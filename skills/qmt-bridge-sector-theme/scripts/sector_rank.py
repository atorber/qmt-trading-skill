#!/usr/bin/env python3
"""板块成分股按涨跌幅排序（只读）。

用法:
    python skills/qmt-bridge-sector-theme/scripts/sector_rank.py --list-sectors
    python skills/qmt-bridge-sector-theme/scripts/sector_rank.py --sector 沪深A股 --top 20
"""

from __future__ import annotations

import argparse
import json
import random
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

# 实测可用的板块名示例（以 --list-sectors 为准）
EXAMPLE_SECTORS = (
    "沪深A股",
    "上证A股",
    "深证A股",
    "创业板",
    "科创板",
)


def _pct_from_tick(tick: dict) -> float:
    last = float(tick.get("lastPrice") or tick.get("lastClose") or 0)
    prev = float(tick.get("lastClose") or tick.get("preClose") or 0)
    return ((last - prev) / prev * 100) if prev else 0.0


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="板块成分强弱排序（只读）")
    add_client_args(parser)
    parser.add_argument("--sector", default="", help="板块名称，如 沪深A股")
    parser.add_argument(
        "--list-sectors",
        action="store_true",
        help="列出可用板块名称",
    )
    parser.add_argument("--top", type=int, default=15, help="输出前 N 名（默认 15）")
    parser.add_argument(
        "--max-scan",
        type=int,
        default=800,
        help="最多拉 tick 的成分股数量（默认 800，大板块请调小 top 或本值）",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="成分超过 max-scan 时随机抽样（默认取前 max-scan 只）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)

    if args.list_sectors:
        sectors = call_api(client.get_sector_list)
        if not isinstance(sectors, list):
            sectors = list(sectors) if sectors else []
        if args.json:
            print(json.dumps({"sectors": sectors}, ensure_ascii=False))
            return 0
        print(f"=== 可用板块 ({len(sectors)} 个) ===")
        for name in sectors[:80]:
            print(f"  {name}")
        if len(sectors) > 80:
            print(f"  ... 共 {len(sectors)} 个，完整列表请加 --json")
        print("\n示例（实测常用）:", ", ".join(EXAMPLE_SECTORS))
        return 0

    if not args.sector:
        print(
            "错误: 请指定 --sector <板块名>，或 --list-sectors 查看列表",
            file=sys.stderr,
        )
        return 2

    stocks = unwrap_data(call_api(client.get_sector_stocks, args.sector))
    if not isinstance(stocks, list):
        stocks = list(stocks) if stocks else []
    codes = [str(c).strip() for c in stocks if c]
    if not codes:
        print(
            f"板块无成分或名称无效: {args.sector}\n"
            f"提示: 运行 --list-sectors 查看有效名称（如「中证500」可能无效）",
            file=sys.stderr,
        )
        return 1

    total_members = len(codes)
    if total_members > args.max_scan:
        if args.sample:
            codes = random.sample(codes, args.max_scan)
            scan_note = f"随机抽样 {args.max_scan}/{total_members} 只"
        else:
            codes = codes[: args.max_scan]
            scan_note = f"仅扫描前 {args.max_scan}/{total_members} 只"
        print(f"提示: {scan_note}", file=sys.stderr)

    batch_size = 80
    ranked: list[dict] = []
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        raw = call_api(client.get_full_tick, batch)
        tick_map = raw.get("data", raw) if isinstance(raw, dict) else {}
        if not isinstance(tick_map, dict):
            continue
        for code in batch:
            t = tick_map.get(code) or {}
            if not isinstance(t, dict):
                continue
            ranked.append({
                "code": code,
                "last": float(t.get("lastPrice") or 0),
                "pct_chg": round(_pct_from_tick(t), 2),
            })

    ranked.sort(key=lambda x: x["pct_chg"], reverse=True)
    top = ranked[: args.top]
    bottom = ranked[-args.top :] if len(ranked) > args.top else []

    display_codes = list({r["code"] for r in top + bottom})
    name_map = fetch_stock_names(client, display_codes)
    for r in top + bottom:
        code = r["code"]
        r["stock_name"] = name_map.get(code) or name_map.get(code.upper()) or ""

    if args.json:
        print(
            json.dumps(
                {
                    "sector": args.sector,
                    "member_count": total_members,
                    "scanned": len(ranked),
                    "stock_names": name_map,
                    "top": top,
                    "bottom": list(reversed(bottom)),
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(
        f"=== 板块成分排序: {args.sector} "
        f"(成分 {total_members}，本次扫描 {len(ranked)}) ==="
    )
    print(f"--- 涨幅前 {args.top} ---")
    for r in top:
        sym = label_stock(r["code"], name_map)
        print(f"  {sym}  {r['pct_chg']:+.2f}%  last={fmt_num(r['last'])}")
    if len(ranked) > args.top:
        print(f"--- 跌幅前 {args.top} ---")
        for r in reversed(bottom):
            sym = label_stock(r["code"], name_map)
            print(f"  {sym}  {r['pct_chg']:+.2f}%  last={fmt_num(r['last'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
