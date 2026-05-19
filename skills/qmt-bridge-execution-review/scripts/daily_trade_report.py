#!/usr/bin/env python3
"""当日交易复盘：委托、成交与按标的汇总（只读）。

用法:
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --port 8080 --api-key KEY
    python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
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
from orders_util import as_list, print_orders_table, summarize_by_stock  # noqa: E402
from stock_names import collect_stock_codes, fetch_stock_names, label_stock  # noqa: E402
from trading_fmt import format_order_time, pick  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 当日交易复盘（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-trades", action="store_true", help="跳过成交列表")
    parser.add_argument("--no-summary", action="store_true", help="跳过按标的汇总")
    args = parser.parse_args()

    client, account_id = make_client(args)

    health = call_api(client.health_check)
    acct = unwrap_data(call_api(client.get_account_status, account_id=account_id))
    orders = as_list(
        unwrap_data(call_api(client.query_orders, account_id=account_id))
    )
    trades: list[dict] = []
    if not args.no_trades:
        trades = as_list(
            unwrap_data(call_api(client.query_trades, account_id=account_id))
        )

    filled = sum(
        1 for o in orders
        if int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0) > 0
    )
    cancelled = sum(
        1 for o in orders
        if int(pick(o, "order_status", "m_nOrderStatus", default=0) or 0) == 54
    )

    codes = collect_stock_codes(orders, trades)
    name_map = fetch_stock_names(client, codes)

    if args.json:
        payload = {
            "date": date.today().isoformat(),
            "health": health,
            "account_status": acct,
            "account_id": account_id,
            "stock_names": name_map,
            "orders": orders,
            "trades": trades,
            "stats": {
                "order_count": len(orders),
                "filled_count": filled,
                "cancelled_count": cancelled,
                "trade_count": len(trades),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 当日交易复盘 ===")
    print(f"日期: {date.today().isoformat()}")
    print(f"health: {health.get('status', health)}")
    print(f"account_status: {acct}")
    if account_id:
        print(f"account_id: {account_id}")
    print(
        f"统计: 委托 {len(orders)} 笔 | 有成交 {filled} | 已撤 {cancelled} | "
        f"成交记录 {len(trades)} 条"
    )

    print_orders_table(orders, title="当日委托", name_map=name_map)

    if not args.no_trades and trades:
        print(f"--- 当日成交 ({len(trades)}) ---")
        for t in sorted(
            trades,
            key=lambda x: pick(
                x, "traded_time", "m_nTradedTime", "trade_time", default=0
            ),
        ):
            code = pick(t, "stock_code", "m_strStockCode", default="?")
            sym = label_stock(code, name_map)
            vol = int(
                pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0)
                or 0
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
