#!/usr/bin/env python3
"""自选标的与大盘指数行情快照（只读）。

用法:
    python skills/qmt-bridge-market-watch/scripts/watchlist_snapshot.py --codes 000001.SZ,600519.SH
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
)
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def _parse_codes(raw: str) -> list[str]:
    return [c.strip() for c in raw.split(",") if c.strip()]


def _pct_from_tick(tick: dict) -> float:
    last = float(tick.get("lastPrice") or tick.get("lastClose") or 0)
    prev = float(tick.get("lastClose") or tick.get("preClose") or 0)
    return round(((last - prev) / prev * 100) if prev else 0.0, 2)


def _tick_row(code: str, tick: dict) -> dict:
    last = float(tick.get("lastPrice") or tick.get("lastClose") or 0)
    return {
        "code": code,
        "last": last,
        "pct_chg": _pct_from_tick(tick),
        "amount": tick.get("amount") or tick.get("turnover"),
        "volume": tick.get("volume"),
    }


def _parse_indices(resp: dict) -> list[dict]:
    """解析 /api/market/indices 返回的 {indices, data}。"""
    if not isinstance(resp, dict):
        return []
    codes = resp.get("indices") or []
    tick_map = resp.get("data") or {}
    if not isinstance(tick_map, dict):
        tick_map = {}
    rows: list[dict] = []
    for code in codes:
        t = tick_map.get(code) or tick_map.get(str(code).upper()) or {}
        if not isinstance(t, dict):
            t = {}
        rows.append(_tick_row(str(code), t))
    return rows


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="自选与指数行情快照（只读）")
    add_client_args(parser)
    parser.add_argument(
        "--codes",
        default="",
        help="股票代码，逗号分隔；与 --indices-only 二选一",
    )
    parser.add_argument(
        "--indices-only",
        action="store_true",
        help="仅输出主要指数，不拉自选 codes",
    )
    parser.add_argument("--no-indices", action="store_true", help="跳过大指数")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    if not args.indices_only and not args.codes.strip():
        print("错误: 请指定 --codes 或 --indices-only", file=sys.stderr)
        return 2

    codes = _parse_codes(args.codes) if not args.indices_only else []
    client, _account_id = make_client(args, require_api_key=False)

    indices_rows: list[dict] = []
    if not args.no_indices:
        try:
            indices_rows = _parse_indices(call_api(client.get_major_indices))
        except SystemExit:
            indices_rows = []

    rows: list[dict] = []
    if codes:
        raw = call_api(client.get_full_tick, codes)
        tick_map = raw.get("data", raw) if isinstance(raw, dict) else {}
        if not isinstance(tick_map, dict):
            tick_map = {}
        for code in codes:
            t = tick_map.get(code) or tick_map.get(code.upper()) or {}
            if isinstance(t, dict) and t:
                rows.append(_tick_row(code, t))
            else:
                rows.append({
                    "code": code,
                    "last": 0,
                    "pct_chg": 0,
                    "amount": None,
                    "volume": None,
                })

    all_codes = [r["code"] for r in rows] + [r["code"] for r in indices_rows]
    name_map = fetch_stock_names(client, all_codes)
    for r in rows + indices_rows:
        code = r["code"]
        r["stock_name"] = name_map.get(code) or name_map.get(code.upper()) or ""

    if args.json:
        print(
            json.dumps(
                {
                    "date": date.today().isoformat(),
                    "stock_names": name_map,
                    "indices": indices_rows,
                    "watchlist": rows,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print("=== QMT Bridge 自选快照 ===")
    print(f"日期: {date.today().isoformat()}")

    if indices_rows:
        print(f"--- 主要指数 ({len(indices_rows)}) ---")
        for r in indices_rows:
            sym = label_stock(r["code"], name_map)
            print(
                f"  {sym}  last={fmt_num(r['last'])}  "
                f"pct={r['pct_chg']:+.2f}%"
            )

    print(f"--- 自选 ({len(rows)}) ---")
    for r in rows:
        sym = label_stock(r["code"], name_map)
        print(
            f"  {sym}  last={fmt_num(r['last'])}  "
            f"pct={r['pct_chg']:+.2f}%  amount={r.get('amount')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
