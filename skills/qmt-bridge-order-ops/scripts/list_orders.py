#!/usr/bin/env python3
"""查询当日委托列表（只读）。

用法:
    python skills/qmt-bridge-order-ops/scripts/list_orders.py
    python skills/qmt-bridge-order-ops/scripts/list_orders.py --cancelable-only
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
from stock_names import collect_stock_codes, fetch_stock_names  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 当日委托查询（只读）")
    add_client_args(parser)
    parser.add_argument(
        "--cancelable-only",
        action="store_true",
        help="仅返回可撤委托",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    client, account_id = make_client(args)
    orders = as_list(
        unwrap_data(
            call_api(
                client.query_orders,
                account_id=account_id,
                cancelable_only=args.cancelable_only,
            )
        )
    )

    codes = collect_stock_codes(orders)
    name_map = fetch_stock_names(client, codes)

    if args.json:
        print(
            json.dumps(
                {
                    "orders": orders,
                    "account_id": account_id,
                    "stock_names": name_map,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    title = "可撤委托" if args.cancelable_only else "当日委托"
    print(f"=== QMT Bridge {title} ===")
    if account_id:
        print(f"account_id: {account_id}")
    print_orders_table(orders, title=title, name_map=name_map)
    return 0


if __name__ == "__main__":
    sys.exit(main())
