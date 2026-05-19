#!/usr/bin/env python3
"""ETF 列表或单券申赎信息快照（只读）。

用法:
    python skills/qmt-bridge-etf/scripts/etf_snapshot.py --list --limit 20
    python skills/qmt-bridge-etf/scripts/etf_snapshot.py --code 510300.SH
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
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="ETF 快照（只读）")
    add_client_args(parser)
    parser.add_argument("--list", action="store_true", help="列出 ETF 代码")
    parser.add_argument("--limit", type=int, default=20, help="列表最多显示条数")
    parser.add_argument("--code", default="", help="单只 ETF 详情")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)

    if not args.code and not args.list:
        args.list = True

    if args.code:
        info = call_api(client.get_etf_info, args.code)
        sym = label_stock(args.code, fetch_stock_names(client, [args.code]))
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2, default=str))
            return 0
        print(f"=== ETF {sym} ===")
        name = info.get("name", "")
        nav = info.get("nav", info.get("iopv"))
        comp = info.get("component_count", len(info.get("components") or []))
        print(f"  名称={name}  NAV/IOPV={nav}  成分数={comp}")
        return 0

    stocks = call_api(client.get_etf_list)
    if not isinstance(stocks, list):
        stocks = []
    show = stocks[: args.limit]
    show_codes = [str(s).strip() for s in show if s]
    name_map = fetch_stock_names(client, show_codes)
    if args.json:
        print(
            json.dumps(
                {"total": len(stocks), "sample": show, "stock_names": name_map},
                ensure_ascii=False,
            )
        )
        return 0
    print(f"=== ETF 列表 (共 {len(stocks)} 只，显示前 {len(show)}) ===")
    for s in show:
        print(f"  {label_stock(str(s), name_map)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
