#!/usr/bin/env python3
"""撤销委托：默认预览，须 --execute --confirm 提交。

用法:
    python skills/qmt-bridge-order-ops/scripts/cancel_orders.py --cancelable-only
    python skills/qmt-bridge-order-ops/scripts/cancel_orders.py --sysid 411494 --stock 688676.SH
    python skills/qmt-bridge-order-ops/scripts/cancel_orders.py --cancelable-only --execute --confirm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, load_env_files, make_client, unwrap_data  # noqa: E402
from orders_util import as_list, print_orders_table  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402
from trading_fmt import market_from_stock, order_side, pick  # noqa: E402


def _cancel_targets(
    orders: list[dict],
    *,
    sysid: str,
    stock: str,
    cancelable_only: bool,
) -> list[dict]:
    out: list[dict] = []
    for o in orders:
        code = pick(o, "stock_code", "m_strStockCode", default="")
        oid = pick(o, "order_id", "m_nOrderID", default=0)
        osys = str(pick(o, "order_sysid", "m_strOrderSysID", default="") or "")
        status = int(pick(o, "order_status", "m_nOrderStatus", default=0) or 0)
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        vol = int(pick(o, "order_volume", "m_nOrderVolume", default=0) or 0)

        if sysid and osys != sysid:
            continue
        if stock and code != stock:
            continue
        if cancelable_only:
            # 已撤、已成、废单跳过
            if status in (54, 56, 57):
                continue
            if traded >= vol and vol > 0:
                continue
        if not sysid and not stock and not cancelable_only:
            continue

        out.append(o)
    return out


def _do_cancel(client, order: dict, account_id: str) -> dict:
    oid = int(pick(order, "order_id", "m_nOrderID", default=0) or 0)
    osys = str(pick(order, "order_sysid", "m_strOrderSysID", default="") or "")
    code = pick(order, "stock_code", "m_strStockCode", default="")

    if oid > 0:
        return call_api(client.cancel_order, order_id=oid, account_id=account_id)
    if osys:
        market = market_from_stock(code)
        return call_api(
            client.cancel_order_by_sysid,
            market=market,
            sysid=osys,
            account_id=account_id,
        )
    raise ValueError(f"无法撤单：缺少 order_id 与 order_sysid ({code})")


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 撤单（预览/执行）")
    add_client_args(parser)
    parser.add_argument("--sysid", default="", help="仅撤指定合同编号")
    parser.add_argument("--stock", default="", help="限定股票代码")
    parser.add_argument(
        "--cancelable-only",
        action="store_true",
        help="撤所有可撤委托（与 --sysid 互斥时优先 sysid）",
    )
    parser.add_argument("--execute", action="store_true", help="执行撤单")
    parser.add_argument("--confirm", action="store_true", help="与 --execute 同时确认")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if not args.sysid and not args.cancelable_only:
        print(
            "错误: 请指定 --sysid <合同号> 或 --cancelable-only",
            file=sys.stderr,
        )
        return 2

    client, account_id = make_client(args)
    all_orders = as_list(
        unwrap_data(call_api(client.query_orders, account_id=account_id))
    )
    targets = _cancel_targets(
        all_orders,
        sysid=args.sysid,
        stock=args.stock,
        cancelable_only=args.cancelable_only and not args.sysid,
    )

    plan = [
        {
            "stock_code": pick(o, "stock_code", "m_strStockCode"),
            "side": order_side(pick(o, "order_type", "m_nOrderType")),
            "order_sysid": pick(o, "order_sysid", "m_strOrderSysID"),
            "order_id": pick(o, "order_id", "m_nOrderID"),
        }
        for o in targets
    ]

    cancel_codes = [
        str(pick(o, "stock_code", "m_strStockCode", default="") or "").strip()
        for o in targets
    ]
    cancel_codes = [c for c in cancel_codes if c]
    name_map = fetch_stock_names(client, cancel_codes) if cancel_codes else {}

    if args.json and not args.execute:
        print(
            json.dumps(
                {"plan": plan, "stock_names": name_map},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("=== QMT Bridge 撤单预览 ===")
    if not targets:
        print("  (无匹配委托)")
        return 0
    print_orders_table(targets, title="拟撤销", name_map=name_map)

    if not args.execute:
        print("\n【预览】未撤单。确认后请加 --execute --confirm")
        return 0

    if not args.confirm:
        print("错误: 实盘撤单须同时指定 --execute --confirm", file=sys.stderr)
        return 2

    results = []
    for o in targets:
        code = pick(o, "stock_code", "m_strStockCode", default="?")
        osys = pick(o, "order_sysid", "m_strOrderSysID", default="")
        try:
            res = _do_cancel(client, o, account_id)
            results.append({"stock_code": code, "order_sysid": osys, "status": "ok", "result": res})
            print(f"  已撤: {label_stock(code, name_map)} sysid={osys}")
        except ValueError as exc:
            results.append({"stock_code": code, "order_sysid": osys, "status": "error", "error": str(exc)})
            print(f"  失败: {label_stock(code, name_map)} — {exc}", file=sys.stderr)
        except SystemExit:
            raise
        except Exception as exc:  # pragma: no cover
            results.append({"stock_code": code, "order_sysid": osys, "status": "error", "error": repr(exc)})
            print(f"  失败: {label_stock(code, name_map)} — {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
