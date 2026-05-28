#!/usr/bin/env python3
"""补齐并校验近N日指数日K缓存（复盘前置）。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, make_client  # noqa: E402
SH = "000001.SH"
SZ = "399106.SZ"
SZ_FALLBACK = "399001.SZ"


def _date_key(row: dict) -> str:
    for k in ("date", "time", "index", "datetime"):
        raw = row.get(k)
        if raw is None:
            continue
        s = str(raw).strip()
        if s.isdigit() and len(s) >= 13:
            try:
                return datetime.fromtimestamp(int(s[:13]) / 1000).strftime("%Y%m%d")
            except (ValueError, OSError):
                continue
        if s.isdigit() and len(s) >= 8:
            return s[:8]
    return ""


def _amount_map(records: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        dt = _date_key(r)
        amt = r.get("amount")
        if not dt or amt is None:
            continue
        try:
            v = float(amt)
        except (TypeError, ValueError):
            continue
        if v > 0:
            out[dt] = v
    return out


def _load_records(client, code: str, count: int) -> list[dict]:
    def _to_records(data) -> list[dict]:
        if data is None:
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            # 兼容 {col: list} 结构
            cols = {k: v for k, v in data.items() if isinstance(v, list)}
            if cols:
                n = max((len(v) for v in cols.values()), default=0)
                rows: list[dict] = []
                for i in range(n):
                    row = {}
                    for k, v in cols.items():
                        if i < len(v):
                            row[k] = v[i]
                    rows.append(row)
                return rows
            return []
        try:
            import pandas as pd

            if isinstance(data, pd.DataFrame):
                if data.empty:
                    return []
                return data.reset_index().to_dict(orient="records")
        except ImportError:
            pass
        return []

    stocks = [code]
    for fn in (
        lambda: client.get_local_data(stocks=stocks, period="1d", count=count),
        lambda: client.get_history_ex(stocks=stocks, period="1d", count=count),
    ):
        try:
            raw = fn()
            data = raw.get("data", raw) if isinstance(raw, dict) else raw
            if not isinstance(data, dict):
                continue
            recs = data.get(code)
            if recs is None:
                recs = data.get(code.upper())
            rows = _to_records(recs)
            if rows:
                return rows
        except Exception:
            continue
    return []


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="补齐并校验近N日指数日K（复盘前置）"
    )
    add_client_args(parser)
    parser.add_argument("--days", type=int, default=3, help="近几日校验，默认3")
    parser.add_argument(
        "--lookback", type=int, default=45, help="下载回看天数，默认45"
    )
    parser.add_argument("--json", action="store_true", help="输出JSON")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)
    days = max(1, int(args.days))
    count = max(days + 15, 30)

    end = date.today().strftime("%Y%m%d")
    start = (date.today() - timedelta(days=max(7, args.lookback))).strftime("%Y%m%d")
    dl = client.download_batch([SH, SZ], period="1d", start_time=start, end_time=end)

    sh_rows = _load_records(client, SH, count)
    sz_rows = _load_records(client, SZ, count)
    if not sz_rows:
        sz_rows = _load_records(client, SZ_FALLBACK, count)
        sz_used = SZ_FALLBACK
    else:
        sz_used = SZ

    sh_map = _amount_map(sh_rows)
    sz_map = _amount_map(sz_rows)

    sh_dates = sorted(sh_map)
    target = sh_dates[-days:] if len(sh_dates) >= days else sh_dates

    missing_sh = [d for d in target if d not in sh_map]
    missing_sz = [d for d in target if d not in sz_map]
    ok = bool(target) and not missing_sh and not missing_sz and len(target) >= days

    payload = {
        "ok": ok,
        "days": days,
        "target_dates": target,
        "sh_code": SH,
        "sz_code_used": sz_used,
        "missing_sh_dates": missing_sh,
        "missing_sz_dates": missing_sz,
        "download_result": dl,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, default=str))
    else:
        print("=== 近N日指数日K补齐 ===")
        print(f"下载区间: {start} ~ {end}")
        print(f"目标交易日: {', '.join(target) if target else '(无)'}")
        print(f"深市使用: {sz_used}")
        if ok:
            print(f"结果: OK（近{days}日沪深日K amount均可用）")
        else:
            print(f"结果: NOT OK（近{days}日仍有缺失）")
            if missing_sh:
                print(f"  - 上证缺失: {', '.join(missing_sh)}")
            if missing_sz:
                print(f"  - 深市缺失: {', '.join(missing_sz)}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
