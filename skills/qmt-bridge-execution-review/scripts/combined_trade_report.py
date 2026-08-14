#!/usr/bin/env python3
"""全账户综合复盘：合并普通户 + 信用户持仓与成交，不区分账户（只读）。

用法:
    python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py
    python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --port 8080 --api-key KEY
    python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --feishu-md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import (  # noqa: E402
    add_client_args,
    call_api,
    load_env_files,
    make_client,
    resolve_account_type_for_id,
    unwrap_data,
)
from execution_review_eval import (  # noqa: E402
    build_operation_evaluation,
    fetch_eval_market_context,
    fetch_market_turnover_history,
    fetch_market_turnover_yi,
    format_operation_evaluation,
    operation_eval_to_dict,
)
from execution_review_feishu_md import build_daily_eval_feishu_markdown  # noqa: E402
from feishu_doc import DOC_TYPES  # noqa: E402
from orders_util import as_list, print_orders_table, summarize_by_stock  # noqa: E402
from pnl_util import (  # noqa: E402
    TradeDaySummary,
    collect_pnl_stock_codes,
    compute_daily_pnl,
    summarize_trades_by_code,
)
from stock_names import collect_stock_codes, fetch_stock_names, label_stock  # noqa: E402
from trading_fmt import format_order_time, pick  # noqa: E402

_REPO = Path(__file__).resolve().parents[3]

_DAILY_PNL_KEYS = (
    "today_profit_loss",
    "today_close_profit_loss",
    "m_dTodayProfitLoss",
    "m_dTodayCloseProfitLoss",
)

_SUM_POSITION_KEYS = (
    "volume",
    "m_nVolume",
    "can_use_volume",
    "m_nCanUseVolume",
    "market_value",
    "m_dMarketValue",
    "yesterday_volume",
    "m_nYesterdayVolume",
    *_DAILY_PNL_KEYS,
)

_ASSET_SUM_KEYS = (
    "cash",
    "frozen_cash",
    "market_value",
    "total_asset",
    "m_dCash",
    "m_dFrozenCash",
    "m_dMarketValue",
    "m_dTotalAsset",
)


def _broker_daily_pnl(position: dict | None) -> float | None:
    if not position:
        return None
    total = 0.0
    found = False
    for k in _DAILY_PNL_KEYS:
        val = pick(position, k)
        if val is None:
            continue
        try:
            total += float(val)
            found = True
            break
        except (TypeError, ValueError):
            continue
    return total if found else None


def _configured_accounts() -> list[tuple[str, str, str]]:
    """返回 [(label, account_id, account_type), ...]。"""
    accounts: list[tuple[str, str, str]] = []
    stock_id = (os.environ.get("QMT_BRIDGE_STOCK_ACCOUNT_ID") or "").strip()
    credit_id = (os.environ.get("QMT_BRIDGE_CREDIT_ACCOUNT_ID") or "").strip()
    if stock_id:
        accounts.append(("普通户", stock_id, ""))
    if credit_id:
        accounts.append(("信用户", credit_id, "CREDIT"))
    return accounts


def _merge_positions(position_lists: list[list[dict]]) -> list[dict]:
    """按标的合并多账户持仓（数量/市值/当日盈亏字段求和）。"""
    merged: dict[str, dict] = {}
    for positions in position_lists:
        for p in positions:
            if not isinstance(p, dict):
                continue
            code = str(pick(p, "stock_code", "m_strStockCode", default="") or "").strip()
            if not code:
                continue
            if code not in merged:
                merged[code] = dict(p)
                continue
            base = merged[code]
            for key in _SUM_POSITION_KEYS:
                v1 = pick(base, key)
                v2 = pick(p, key)
                if v1 is None and v2 is None:
                    continue
                try:
                    base[key] = float(v1 or 0) + float(v2 or 0)
                except (TypeError, ValueError):
                    pass
    return list(merged.values())


def _merge_assets(assets: list[dict]) -> dict:
    """合并多账户资产摘要。"""
    out: dict[str, float] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        for key in _ASSET_SUM_KEYS:
            val = pick(asset, key)
            if val is None:
                continue
            try:
                out[key] = out.get(key, 0.0) + float(val)
            except (TypeError, ValueError):
                continue
    # 归一化常用字段名
    result = dict(out)
    if "cash" not in result and "m_dCash" in result:
        result["cash"] = result["m_dCash"]
    if "market_value" not in result and "m_dMarketValue" in result:
        result["market_value"] = result["m_dMarketValue"]
    if "total_asset" not in result and "m_dTotalAsset" in result:
        result["total_asset"] = result["m_dTotalAsset"]
    return result


def _fetch_account_bundle(
    client,
    account_id: str,
    account_type: str,
) -> dict:
    account_type = resolve_account_type_for_id(account_id, account_type)
    asset = unwrap_data(
        call_api(
            client.query_asset,
            account_id=account_id,
            account_type=account_type,
        )
    )
    positions = unwrap_data(
        call_api(
            client.query_positions,
            account_id=account_id,
            account_type=account_type,
        )
    )
    orders = unwrap_data(
        call_api(
            client.query_orders,
            account_id=account_id,
            account_type=account_type,
        )
    )
    trades = unwrap_data(
        call_api(
            client.query_trades,
            account_id=account_id,
            account_type=account_type,
        )
    )
    status = unwrap_data(call_api(client.get_account_status, account_id=account_id))
    return {
        "account_id": account_id,
        "account_type": account_type,
        "asset": asset if isinstance(asset, dict) else {},
        "positions": positions if isinstance(positions, list) else [],
        "orders": as_list(orders),
        "trades": as_list(trades),
        "status": status,
    }


def _fetch_combined_pnl_breakdowns(
    client,
    positions: list[dict],
    trades: list[dict],
):
    trade_map = summarize_trades_by_code(trades)
    pos_by_code: dict[str, dict] = {}
    for p in positions:
        if not isinstance(p, dict):
            continue
        code = str(pick(p, "stock_code", "m_strStockCode", default="") or "").strip()
        if code:
            pos_by_code[code] = p

    codes = collect_pnl_stock_codes(positions, trade_map)
    tick_map: dict[str, dict] = {}
    if codes:
        raw = call_api(client.get_full_tick, codes)
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if isinstance(data, dict):
            tick_map = data

    breakdowns = []
    for code in codes:
        pos = pos_by_code.get(code)
        trade = trade_map.get(code, TradeDaySummary())
        tick = tick_map.get(code) or tick_map.get(code.upper()) or {}
        breakdowns.append(
            compute_daily_pnl(
                code,
                position=pos,
                trade=trade,
                tick=tick,
                broker_daily=_broker_daily_pnl(pos),
                allow_tick=True,
            )
        )
    return breakdowns, tick_map


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 全账户综合复盘（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-trades", action="store_true", help="跳过成交列表")
    parser.add_argument("--no-summary", action="store_true", help="跳过按标的汇总")
    parser.add_argument("--no-eval", action="store_true", help="不输出当日操作评价")
    parser.add_argument(
        "--market-turnover-yi",
        type=float,
        default=None,
        metavar="YI",
        help="两市成交额（亿元）；未传时自动拉取",
    )
    parser.add_argument(
        "--no-philosophy-fetch",
        action="store_true",
        help="不拉取指数/近3日涨幅",
    )
    parser.add_argument(
        "--feishu-md",
        nargs="?",
        const="reports/feishu_combined_daily_eval.md",
        metavar="PATH",
        help="导出飞书 Markdown（默认 reports/feishu_combined_daily_eval.md）",
    )
    args = parser.parse_args()

    accounts = _configured_accounts()
    if not accounts:
        print(
            "错误: 未配置账户。请在 .env 设置 QMT_BRIDGE_STOCK_ACCOUNT_ID / "
            "QMT_BRIDGE_CREDIT_ACCOUNT_ID",
            file=sys.stderr,
        )
        return 2

    client, _ = make_client(args)
    health = call_api(client.health_check)

    bundles = []
    for label, account_id, account_type in accounts:
        bundle = _fetch_account_bundle(client, account_id, account_type)
        bundle["label"] = label
        bundles.append(bundle)

    orders: list[dict] = []
    trades: list[dict] = []
    for b in bundles:
        orders.extend(b["orders"])
        trades.extend(b["trades"])
    orders.sort(key=lambda x: pick(x, "order_time", "m_nOrderTime", default=0))
    trades.sort(
        key=lambda x: pick(x, "traded_time", "m_nTradedTime", "trade_time", default=0)
    )

    positions = _merge_positions([b["positions"] for b in bundles])
    asset = _merge_assets([b["asset"] for b in bundles])

    account_label = "综合（" + " + ".join(b["label"] for b in bundles) + "）"
    account_ids = ",".join(b["account_id"] for b in bundles)
    acct_status = {b["account_id"]: b["status"] for b in bundles}

    filled = sum(
        1
        for o in orders
        if int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0) > 0
    )
    cancelled = sum(
        1
        for o in orders
        if int(pick(o, "order_status", "m_nOrderStatus", default=0) or 0) == 54
    )

    codes = collect_stock_codes(orders, trades)
    for p in positions:
        code = pick(p, "stock_code", "m_strStockCode", default="")
        if code and code not in codes:
            codes.append(code)
    name_map = fetch_stock_names(client, codes)

    op_eval = None
    breakdowns = []
    if not args.no_eval:
        breakdowns, tick_map = _fetch_combined_pnl_breakdowns(client, positions, trades)
        eval_codes = [b.stock_code for b in breakdowns if b.stock_code]
        cum3: dict[str, float | None] = {}
        index_avg: float | None = None
        turnover_history = []
        market_turnover_yi = args.market_turnover_yi
        if not args.no_philosophy_fetch:
            fetched_turnover, turnover_history, cum3, index_avg = (
                fetch_eval_market_context(client, eval_codes)
            )
        else:
            fetched_turnover = fetch_market_turnover_yi(client)
            turnover_history = fetch_market_turnover_history(client, days=3)
        if market_turnover_yi is None:
            market_turnover_yi = fetched_turnover
        if market_turnover_yi is not None:
            print(
                f"两市成交额（{'手动' if args.market_turnover_yi is not None else '自动'}）: "
                f"{market_turnover_yi:,.2f} 亿元",
                file=sys.stderr,
            )
        if turnover_history:
            from trading_philosophy import format_turnover_history_line  # noqa: E402

            print(format_turnover_history_line(turnover_history), file=sys.stderr)
        op_eval = build_operation_evaluation(
            orders=orders,
            trades=trades,
            breakdowns=breakdowns,
            asset=asset,
            name_map=name_map,
            cancelled_count=cancelled,
            market_turnover_yi=market_turnover_yi,
            turnover_history=turnover_history,
            cumulative_3d_pct=cum3,
            index_avg_pct=index_avg,
            tick_map=tick_map,
        )

    if args.feishu_md:
        out = Path(args.feishu_md)
        if not out.is_absolute():
            out = _REPO / out
        synced = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade_date = date.today().isoformat()
        md = build_daily_eval_feishu_markdown(
            trade_date=trade_date,
            synced_at=synced,
            account_id=f"{account_label} [{account_ids}]",
            health=health,
            account_status=acct_status,
            orders=orders,
            trades=trades,
            name_map=name_map,
            filled=filled,
            cancelled=cancelled,
            op_eval=op_eval,
            include_trades=not args.no_trades,
            include_summary=not args.no_summary,
        )
        md = md.replace(
            "daily_trade_report.py --feishu-md",
            "combined_trade_report.py --feishu-md",
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"已写入飞书 Markdown: {out}", file=sys.stderr)

    if args.json:
        payload = {
            "date": date.today().isoformat(),
            "scope": "combined",
            "accounts": [
                {
                    "label": b["label"],
                    "account_id": b["account_id"],
                    "account_type": b["account_type"] or "STOCK",
                }
                for b in bundles
            ],
            "health": health,
            "account_status": acct_status,
            "asset": asset,
            "positions": positions,
            "stock_names": name_map,
            "orders": orders,
            "trades": trades,
            "stats": {
                "order_count": len(orders),
                "filled_count": filled,
                "cancelled_count": cancelled,
                "trade_count": len(trades),
                "position_count": len(positions),
            },
            "operation_evaluation": None
            if op_eval is None
            else operation_eval_to_dict(op_eval),
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 全账户综合复盘 ===")
    print(f"日期: {date.today().isoformat()}")
    print(f"范围: {account_label}")
    print(f"账户: {account_ids}")
    print(f"health: {health.get('status', health)}")
    print(f"account_status: {acct_status}")
    if asset:
        print(
            f"合并资产: cash={asset.get('cash', 0):,.2f}  "
            f"market_value={asset.get('market_value', 0):,.2f}  "
            f"total_asset={asset.get('total_asset', 0):,.2f}"
        )
    print(f"合并持仓: {len(positions)} 只")
    print(
        f"统计: 委托 {len(orders)} 笔 | 有成交 {filled} | 已撤 {cancelled} | "
        f"成交记录 {len(trades)} 条"
    )

    print_orders_table(orders, title="当日委托（全账户）", name_map=name_map)

    if not args.no_trades and trades:
        print(f"--- 当日成交（全账户，{len(trades)}） ---")
        for t in trades:
            code = pick(t, "stock_code", "m_strStockCode", default="?")
            sym = label_stock(code, name_map)
            vol = int(
                pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0) or 0
            )
            price = float(
                pick(t, "traded_price", "m_dTradedPrice", "trade_price", default=0) or 0
            )
            tm = format_order_time(
                pick(t, "traded_time", "m_nTradedTime", "trade_time")
            )
            print(f"  {tm}  {sym}  {vol}@{price:.2f}")

    if not args.no_summary:
        summarize_by_stock(orders, trades, name_map=name_map)

    if op_eval is not None:
        print(format_operation_evaluation(op_eval))

    return 0


if __name__ == "__main__":
    sys.exit(main())
