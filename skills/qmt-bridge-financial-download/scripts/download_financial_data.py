#!/usr/bin/env python3
"""下载财报到 Bridge 服务端缓存（写操作，需用户知情）。

用法:
    python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
        --codes 600584.SH,603986.SH --table Pershareindex
    python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
        --codes 600584.SH --all-tables --verify --wait 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, make_client  # noqa: E402
from financial_util import (  # noqa: E402
    KNOWN_TABLES,
    download_financial,
    verify_cache,
)
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="下载财务数据到服务端缓存（POST，非只读）",
    )
    add_client_args(parser)
    parser.add_argument("--codes", required=True, help="股票代码，逗号分隔")
    parser.add_argument(
        "--table",
        default="Pershareindex",
        help=f"财务表名，默认 Pershareindex；可选 {', '.join(KNOWN_TABLES)}",
    )
    parser.add_argument(
        "--all-tables",
        action="store_true",
        help="下载全部财务表（较慢）",
    )
    parser.add_argument("--start-time", default="", help="开始时间 YYYYMMDD")
    parser.add_argument("--end-time", default="", help="结束时间 YYYYMMDD")
    parser.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="下载后等待秒数再验证（默认 5，与 --verify 联用）",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="下载后查询缓存，确认是否有数据",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    if not codes:
        print("错误: --codes 不能为空", file=sys.stderr)
        return 2

    client, _ = make_client(args, require_api_key=False)
    name_map = fetch_stock_names(client, codes)

    table_label = "全部表" if args.all_tables else args.table
    sym_list = ", ".join(label_stock(c, name_map) for c in codes)
    print("=== 下载财务数据 ===")
    print(f"  标的: {sym_list}")
    print(f"  表: {table_label}")
    if args.start_time or args.end_time:
        print(f"  区间: {args.start_time or '*'} ~ {args.end_time or '*'}")

    result = download_financial(
        client,
        codes,
        args.table,
        start_time=args.start_time,
        end_time=args.end_time,
        all_tables=args.all_tables,
    )
    print(f"  API 结果: {result.get('status', result)}")

    verify_rows: list[dict] = []
    if args.verify:
        if args.wait > 0:
            print(f"  等待 {args.wait:.0f}s 后验证缓存...")
            time.sleep(args.wait)
        verify_rows = verify_cache(client, codes, args.table)
        missing = [r["code"] for r in verify_rows if r.get("status") != "ok"]
        if missing and args.wait > 0:
            retry_wait = min(args.wait, 10.0)
            print(f"  {len(missing)} 只仍无数据，再等 {retry_wait:.0f}s 重试验证...")
            time.sleep(retry_wait)
            verify_rows = verify_cache(client, codes, args.table)

        print("")
        print(f"=== 缓存验证 [{args.table}] ===")
        for row in verify_rows:
            sym = label_stock(row["code"], name_map)
            if row["status"] == "ok":
                print(f"  {sym}  有数据  报告期={row.get('report_period', '')}")
            else:
                print(f"  {sym}  仍无数据（可加大 --wait 或检查 QMT 登录）")

        ok = sum(1 for r in verify_rows if r["status"] == "ok")
        print(f"共 {len(verify_rows)} 只（有缓存 {ok}，无数据 {len(verify_rows) - ok}）")
    elif args.wait > 0:
        print(f"  已等待 {args.wait:.0f}s（未验证，可加 --verify）")
        time.sleep(args.wait)

    if args.json:
        payload = {
            "codes": codes,
            "table": args.table,
            "all_tables": args.all_tables,
            "stock_names": name_map,
            "download_result": result,
            "verify": verify_rows,
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
