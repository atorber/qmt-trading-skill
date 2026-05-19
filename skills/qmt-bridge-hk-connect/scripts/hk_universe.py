#!/usr/bin/env python3
"""港股通标的列表摘要（只读）。

用法:
    python skills/qmt-bridge-hk-connect/scripts/hk_universe.py
    python skills/qmt-bridge-hk-connect/scripts/hk_universe.py --connect south --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, load_env_files, make_client  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="港股通标的（只读）")
    add_client_args(parser)
    parser.add_argument(
        "--connect",
        choices=("north", "south", "all"),
        default="all",
        help="north=沪/深股通 south=港股通 all=stock_list",
    )
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)

    if args.connect == "all":
        stocks = call_api(client.get_hk_stock_list)
        label = "港股通标的"
    else:
        stocks = call_api(client.get_hk_connect_stocks, args.connect)
        label = f"connect={args.connect}"

    if not isinstance(stocks, list):
        stocks = []
    sample = stocks[: args.limit]

    if args.json:
        print(json.dumps({"label": label, "total": len(stocks), "sample": sample}, ensure_ascii=False))
        return 0

    print(f"=== {label} (共 {len(stocks)} 只) ===")
    for s in sample:
        print(f"  {s}")
    if len(stocks) > args.limit:
        print(f"  ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
