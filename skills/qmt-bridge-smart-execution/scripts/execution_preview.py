#!/usr/bin/env python3
"""下单前执行预览：资金、可卖、涨跌停距离（不提交委托）。

用法:
    python skills/qmt-bridge-smart-execution/scripts/execution_preview.py \\
        000001.SZ --buy --volume 100
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


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="下单执行预览（不提交）")
    add_client_args(parser)
    parser.add_argument("stock_code", help="股票代码")
    direction = parser.add_mutually_exclusive_group(required=True)
    direction.add_argument("--buy", action="store_true")
    direction.add_argument("--sell", action="store_true")
    parser.add_argument("--volume", type=int, required=True)
    parser.add_argument("--price-type", type=int, default=5)
    parser.add_argument("--price", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.volume <= 0:
        print("错误: --volume 须为正整数", file=sys.stderr)
        return 2

    side = "买入" if args.buy else "卖出"
    order_type = ORDER_BUY if args.buy else ORDER_SELL
    client, account_id = make_client(args)
    name_map = fetch_stock_names(client, [args.stock_code])
    sym = label_stock(args.stock_code, name_map)

    tick_raw = call_api(client.get_full_tick, [args.stock_code])
    tick_map = tick_raw.get("data", tick_raw) if isinstance(tick_raw, dict) else {}
    tick = tick_map.get(args.stock_code) or tick_map.get(args.stock_code.upper()) or {}

    last = float(tick.get("lastPrice") or tick.get("lastClose") or 0)
    up = float(tick.get("upperLimit") or tick.get("UpStopPrice") or 0)
    down = float(tick.get("lowerLimit") or tick.get("DownStopPrice") or 0)

    est_price = args.price if args.price_type == 11 and args.price > 0 else last
    est_amount = est_price * args.volume

    warnings: list[str] = []
    checks: dict = {}

    asset = unwrap_data(call_api(client.query_asset, account_id=account_id))
    cash = float((asset or {}).get("cash") or 0)
    checks["cash"] = cash

    if args.buy:
        if est_amount > cash:
            warnings.append(f"资金不足: 预估 {fmt_num(est_amount)} > 现金 {fmt_num(cash)}")
        if up > 0 and est_price >= up * 0.999:
            warnings.append("委托价接近涨停，可能无法买入")
    else:
        positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
        usable = 0
        if isinstance(positions, list):
            for p in positions:
                if p.get("stock_code") == args.stock_code:
                    usable = int(p.get("can_use_volume") or 0)
                    break
        checks["can_use_volume"] = usable
        if args.volume > usable:
            warnings.append(f"可卖不足: 需要 {args.volume} > 可卖 {usable}")
        if down > 0 and est_price <= down * 1.001:
            warnings.append("委托价接近跌停，可能无法卖出")

    plan = {
        "stock_code": args.stock_code,
        "side": side,
        "order_type": order_type,
        "order_volume": args.volume,
        "price_type": args.price_type,
        "price": args.price,
        "est_price": est_price,
        "est_amount": est_amount,
        "last": last,
        "upper_limit": up,
        "lower_limit": down,
        "warnings": warnings,
        "checks": checks,
    }

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    print("=== 执行预览（未下单）===")
    pt_label = "限价" if args.price_type == 11 else "市价/最新价"
    print(
        f"  {side} {sym} x{args.volume}  "
        f"price_type={args.price_type}({pt_label})"
    )
    print(f"  现价={fmt_num(last)}  预估金额={fmt_num(est_amount)}")
    if up or down:
        print(f"  涨停={fmt_num(up)}  跌停={fmt_num(down)}")
    if warnings:
        print("--- 风险提示 ---")
        for w in warnings:
            print(f"  * {w}")
    else:
        print("--- 风险提示 ---")
        print("  (无)")
    print("\n确认后请使用: skills/qmt-bridge-trading/scripts/place_order.py --execute --confirm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
