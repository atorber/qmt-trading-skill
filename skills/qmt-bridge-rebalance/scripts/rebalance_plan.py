#!/usr/bin/env python3
"""目标权重再平衡：生成买卖差额清单（默认预览）。

用法:
    python skills/qmt-bridge-rebalance/scripts/rebalance_plan.py \\
        --targets '{"300394.SZ":0.5,"688008.SH":0.5}'
    python skills/qmt-bridge-rebalance/scripts/rebalance_plan.py \\
        --targets-file weights.json --execute --confirm
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import (  # noqa: E402
    add_client_args,
    call_api,
    fmt_num,
    load_env_files,
    make_client,
    unwrap_data,
)
from stock_names import fetch_stock_names, label_stock  # noqa: E402

ORDER_BUY = 23
ORDER_SELL = 24
LOT = 100


def _round_lot(shares: float) -> int:
    if shares <= 0:
        return 0
    return int(shares // LOT) * LOT


def _load_targets(args) -> dict[str, float]:
    if args.targets_file:
        raw = Path(args.targets_file).read_text(encoding="utf-8")
        targets = json.loads(raw)
    else:
        targets = json.loads(args.targets)
    if not isinstance(targets, dict):
        raise ValueError("targets 须为 JSON 对象 {code: weight}")
    total_w = sum(float(v) for v in targets.values())
    if total_w <= 0:
        raise ValueError("权重之和须 > 0")
    return {k: float(v) / total_w for k, v in targets.items()}


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="组合再平衡计划（预览/执行）")
    add_client_args(parser)
    parser.add_argument("--targets", default="", help='目标权重 JSON，如 {"000001.SZ":0.5}')
    parser.add_argument("--targets-file", default="", help="权重 JSON 文件路径")
    parser.add_argument("--execute", action="store_true", help="提交 batch_order")
    parser.add_argument("--confirm", action="store_true", help="与 --execute 确认实盘")
    parser.add_argument("--price-type", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.targets and not args.targets_file:
        print(
            "错误: 须 --targets 或 --targets-file\n"
            '示例: --targets \'{"300394.SZ":0.5,"688008.SH":0.5}\'',
            file=sys.stderr,
        )
        return 2

    try:
        targets = _load_targets(args)
    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"错误: {exc}\n"
            '示例: --targets \'{"300394.SZ":0.5,"688008.SH":0.5}\'',
            file=sys.stderr,
        )
        return 2

    client, account_id = make_client(args)
    asset = unwrap_data(call_api(client.query_asset, account_id=account_id))
    positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
    if not isinstance(positions, list):
        positions = []

    total_asset = float((asset or {}).get("total_asset") or 0)
    if total_asset <= 0:
        print("错误: 无法取得 total_asset", file=sys.stderr)
        return 1

    pos_map = {p.get("stock_code"): int(p.get("volume") or 0) for p in positions}
    all_codes = sorted(set(targets) | set(pos_map))
    name_map = fetch_stock_names(client, all_codes)
    ticks = call_api(client.get_full_tick, all_codes)
    tick_map = ticks.get("data", ticks) if isinstance(ticks, dict) else {}

    orders: list[dict] = []
    lines: list[dict] = []

    for code in all_codes:
        t = tick_map.get(code) or {}
        price = float(t.get("lastPrice") or t.get("lastClose") or 0)
        if price <= 0:
            lines.append({"code": code, "error": "无现价"})
            continue
        weight = targets.get(code, 0.0)
        target_value = total_asset * weight
        target_shares = _round_lot(target_value / price)
        current = pos_map.get(code, 0)
        diff = target_shares - current
        current_weight = (current * price / total_asset) if total_asset else 0.0
        lines.append({
            "code": code,
            "weight": weight,
            "current_weight": round(current_weight, 4),
            "weight_gap": round(current_weight - weight, 4),
            "current": current,
            "target": target_shares,
            "diff": diff,
            "price": price,
        })
        if diff == 0:
            continue
        if diff > 0:
            orders.append({
                "stock_code": code,
                "order_type": ORDER_BUY,
                "order_volume": diff,
                "price_type": args.price_type,
                "price": 0.0,
                "order_remark": "rebalance",
                "account_id": account_id,
                "strategy_name": "",
            })
        else:
            # 卖出量不超过可卖
            usable = 0
            for p in positions:
                if p.get("stock_code") == code:
                    usable = int(p.get("can_use_volume") or 0)
                    break
            sell_vol = min(-diff, usable)
            if sell_vol <= 0:
                continue
            orders.append({
                "stock_code": code,
                "order_type": ORDER_SELL,
                "order_volume": sell_vol,
                "price_type": args.price_type,
                "price": 0.0,
                "order_remark": "rebalance",
                "account_id": account_id,
                "strategy_name": "",
            })

    if args.json and not args.execute:
        print(json.dumps({"lines": lines, "orders": orders}, ensure_ascii=False, indent=2))
        return 0

    print(f"=== 再平衡计划 (总资产 {fmt_num(total_asset)}) ===")
    for ln in lines:
        if "error" in ln:
            print(f"  {label_stock(ln['code'], name_map)}  {ln['error']}")
            continue
        sym = label_stock(ln["code"], name_map)
        print(
            f"  {sym}  目标权重={ln['weight']:.1%}  "
            f"当前权重={ln['current_weight']:.1%}  偏离={ln['weight_gap']:+.1%}  "
            f"股数 {ln['current']} -> {ln['target']}  差额={ln['diff']:+d}"
        )
    print(f"--- 拟委托 ({len(orders)} 笔) ---")
    for o in orders:
        side = "买" if o["order_type"] == ORDER_BUY else "卖"
        print(f"  {side} {label_stock(o['stock_code'], name_map)} x{o['order_volume']}")

    if not orders:
        return 0
    if not args.execute:
        print("\n【预览】未提交。确认: --execute --confirm")
        return 0
    if not args.confirm:
        print("错误: 须 --execute --confirm", file=sys.stderr)
        return 2

    result = call_api(client.batch_order, orders)
    print(json.dumps(unwrap_data(result), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
