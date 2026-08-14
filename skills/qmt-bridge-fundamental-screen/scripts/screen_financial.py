#!/usr/bin/env python3
"""基本面数据筛选：缺数可自动下载，拉取最新一期并按字段过滤。

下载-only 请用 qmt-bridge-financial-download/scripts/download_financial_data.py

用法:
    python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py \\
        --codes 000001.SZ,600519.SH --table Pershareindex
    python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py \\
        --codes 600519.SH --table Pershareindex --field du_return_on_equity --min 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, make_client  # noqa: E402
from financial_util import (  # noqa: E402
    KNOWN_TABLES,
    codes_without_table,
    download_financial,
    fetch_financial,
    latest_record,
)
from positions_util import fetch_position_codes  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402

# 常用筛选字段别名（不区分大小写）
FIELD_ALIASES = {
    "roe": "du_return_on_equity",
    "净资产收益率": "du_return_on_equity",
    "eps": "s_fa_eps_basic",
    "bps": "s_fa_bps",
}


def _normalize_field(field: str) -> str:
    if not field:
        return field
    key = field.strip()
    return FIELD_ALIASES.get(key.lower(), key)


def _get_field(record: dict, field: str) -> Any:
    norm = _normalize_field(field)
    for key, val in record.items():
        if key.lower() == norm.lower():
            return val
    return record.get(norm)


def _passes_filter(val: Any, min_val: float | None, max_val: float | None) -> bool:
    try:
        num = float(val)
    except (TypeError, ValueError):
        return min_val is None and max_val is None
    if min_val is not None and num < min_val:
        return False
    if max_val is not None and num > max_val:
        return False
    return True


def _build_rows(
    data: dict,
    codes: list[str],
    table: str,
    field: str,
    min_val: float | None,
    max_val: float | None,
) -> list[dict]:
    rows: list[dict] = []
    norm_field = _normalize_field(field)
    for code in codes:
        stock_tables = data.get(code) or data.get(code.upper()) or {}
        recs = stock_tables.get(table) if isinstance(stock_tables, dict) else []
        latest = latest_record(recs if isinstance(recs, list) else [])
        if not latest:
            rows.append({"code": code, "status": "no_data"})
            continue
        entry: dict = {"code": code, "status": "ok", "report": latest}
        if norm_field:
            val = _get_field(latest, norm_field)
            entry["field"] = norm_field
            entry["value"] = val
            if not _passes_filter(val, min_val, max_val):
                entry["status"] = "filtered_out"
        rows.append(entry)

    if norm_field and (min_val is not None or max_val is not None):
        rows = [r for r in rows if r.get("status") != "filtered_out"]
    return rows


def _print_rows(
    rows: list[dict],
    name_map: dict[str, str],
    table: str,
    field: str,
) -> None:
    norm_field = _normalize_field(field)
    print(f"=== 基本面筛选 [{table}] ===")
    if norm_field and (field != norm_field):
        print(f"  字段: {field} → {norm_field}")

    ok = sum(1 for r in rows if r.get("status") == "ok")
    no_data = sum(1 for r in rows if r.get("status") == "no_data")

    for r in rows:
        code = r["code"]
        sym = label_stock(code, name_map)
        if r.get("status") == "no_data":
            print(
                f"  {sym}  (无数据，可先运行 financial-download Skill 或 --download)"
            )
            continue
        latest = r.get("report") or {}
        tag = latest.get("m_timetag") or latest.get("report_date", "")
        if norm_field:
            val = r.get("value", _get_field(latest, norm_field))
            print(f"  {sym}  {norm_field}={val}  报告期={tag}")
        else:
            prefer = [
                "du_return_on_equity",
                "s_fa_eps_basic",
                "s_fa_bps",
                "inc_revenue_rate",
                "du_profit_rate",
            ]
            parts: list[str] = []
            for k in prefer:
                if k in latest and latest[k] is not None:
                    parts.append(f"{k}={latest[k]}")
            if len(parts) < 4:
                for k in sorted(latest.keys()):
                    if k in prefer or latest[k] is None:
                        continue
                    parts.append(f"{k}={latest[k]}")
                    if len(parts) >= 6:
                        break
            print(f"  {sym}  报告期={tag}  " + ", ".join(parts))

    print(f"共 {len(rows)} 条（有数据 {ok}，无数据 {no_data}）")


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="基本面筛选：缺数可自动下载（大批量请先 financial-download Skill）",
    )
    add_client_args(parser)
    parser.add_argument("--codes", default="", help="股票代码，逗号分隔")
    parser.add_argument(
        "--from-positions",
        action="store_true",
        help="使用当前持仓代码（须 API Key 与交易账户）",
    )
    parser.add_argument(
        "--table",
        default="Pershareindex",
        help=f"财务表名，如 {', '.join(KNOWN_TABLES[:4])}",
    )
    parser.add_argument(
        "--field",
        default="",
        help="筛选字段（支持别名 roe→du_return_on_equity）",
    )
    parser.add_argument("--min", type=float, dest="min_val", help="字段最小值（含）")
    parser.add_argument("--max", type=float, dest="max_val", help="字段最大值（含）")
    parser.add_argument(
        "--download",
        action="store_true",
        help="查询前先下载指定表（刷新缓存）",
    )
    parser.add_argument(
        "--if-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="缺数时自动下载后重试（默认开启）",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=5.0,
        help="下载后等待秒数再查询（默认 5）",
    )
    parser.add_argument("--start-time", default="", help="下载开始时间 YYYYMMDD")
    parser.add_argument("--end-time", default="", help="下载结束时间 YYYYMMDD")
    parser.add_argument(
        "--download-all-tables",
        action="store_true",
        help="下载全部财务表（较慢）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if args.from_positions:
        client, account_id = make_client(args, require_api_key=True)
        codes = fetch_position_codes(client, account_id)
        if not codes:
            print("错误: 当前无持仓，无法 --from-positions", file=sys.stderr)
            return 1
    else:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        if not codes:
            print(
                "错误: 请指定 --codes 或 --from-positions",
                file=sys.stderr,
            )
            return 2
        client, _ = make_client(args, require_api_key=False)
    name_map = fetch_stock_names(client, codes)
    download_log: list[dict] = []

    def do_download(target_codes: list[str], reason: str) -> None:
        if not target_codes:
            return
        sym_list = ", ".join(label_stock(c, name_map) for c in target_codes)
        print(f"--- 下载财务数据 ({reason}) ---")
        print(f"  标的: {sym_list}")
        print(f"  表: {args.table if not args.download_all_tables else '全部'}")
        result = download_financial(
            client,
            target_codes,
            args.table,
            start_time=args.start_time,
            end_time=args.end_time,
            all_tables=args.download_all_tables,
        )
        download_log.append({"reason": reason, "codes": target_codes, "result": result})
        print(f"  结果: {result.get('status', result)}")
        if args.wait > 0:
            print(f"  等待 {args.wait:.0f}s 后查询...")
            time.sleep(args.wait)

    if args.download:
        do_download(codes, "用户指定 --download")

    data = fetch_financial(client, codes, args.table)

    if args.if_missing:
        missing = codes_without_table(data, codes, args.table)
        if missing and not args.download:
            do_download(missing, "本地无缓存")
        data = fetch_financial(client, codes, args.table)

    if not data:
        print("未获取到任何财务数据。", file=sys.stderr)
        return 1

    rows = _build_rows(data, codes, args.table, args.field, args.min_val, args.max_val)
    for r in rows:
        code = r["code"]
        r["stock_name"] = name_map.get(code) or name_map.get(code.upper()) or ""

    if args.json:
        print(
            json.dumps(
                {
                    "table": args.table,
                    "field": _normalize_field(args.field),
                    "stock_names": name_map,
                    "download": download_log,
                    "rows": rows,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    if download_log:
        print("")
    _print_rows(rows, name_map, args.table, args.field)
    return 0


if __name__ == "__main__":
    sys.exit(main())
