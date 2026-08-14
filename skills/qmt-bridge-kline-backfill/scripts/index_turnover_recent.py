#!/usr/bin/env python3
"""上证+深证指数近 N 日成交额（亿元）：get_full_tick + 本地日缓存，不拉全市场 K 线。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, make_client  # noqa: E402
from market_turnover_util import (  # noqa: E402
    SH_INDEX,
    SZ_FALLBACK,
    SZ_INDEX,
    build_turnover_history,
    fetch_turnover_amount_maps,
    get_recent_trading_dates,
)
from trading_philosophy import format_turnover_history_line  # noqa: E402


def _fmt_date(dt: str) -> str:
    if len(dt) == 8 and dt.isdigit():
        return f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}"
    return dt


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="上证+深证指数近N日成交额（tick+缓存，安全路径）"
    )
    add_client_args(parser)
    parser.add_argument("--days", type=int, default=3, help="近几个交易日，默认3")
    parser.add_argument(
        "--try-history",
        action="store_true",
        help="可选：尝试 get_market_data 补缺失历史（慎用）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)
    days = max(1, int(args.days))
    target = get_recent_trading_dates(client, days)
    sh_map, sz_map, sz_used = fetch_turnover_amount_maps(
        client, try_history=args.try_history
    )

    if not target:
        common = sorted(set(sh_map) & set(sz_map))
        target = common[-days:]

    rows: list[dict] = []
    for dt in target:
        sh = sh_map.get(dt, 0)
        sz = sz_map.get(dt, 0)
        rows.append(
            {
                "trade_date": dt,
                "sh_index": SH_INDEX,
                "sz_index": sz_used if sz > 0 else SZ_INDEX,
                "sh_yi": round(sh / 1e8, 2) if sh > 0 else None,
                "sz_yi": round(sz / 1e8, 2) if sz > 0 else None,
                "total_yi": round((sh + sz) / 1e8, 2) if sh > 0 and sz > 0 else None,
            }
        )

    history = build_turnover_history(sh_map, sz_map, target)
    complete = len(history) >= days and all(r["total_yi"] for r in rows)

    payload = {
        "ok": complete,
        "days": days,
        "sh_code": SH_INDEX,
        "sz_code_used": sz_used,
        "sz_fallback": SZ_FALLBACK,
        "target_dates": target,
        "rows": rows,
        "summary": format_turnover_history_line(history),
        "method": "full_tick+cache"
        + ("+optional_market_data" if args.try_history else ""),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("=== 上证 + 深证 近N日成交额（亿元）===")
        print(f"上证: {SH_INDEX}  深市: {sz_used}（tick 缺 amount 时回退 {SZ_FALLBACK}）")
        print(f"方式: {payload['method']}")
        print()
        print(f"{'交易日':<12} {'上证(亿)':>12} {'深证(亿)':>12} {'两市合计(亿)':>14}")
        print("-" * 52)
        for r in rows:
            sh_s = f"{r['sh_yi']:,.2f}" if r["sh_yi"] is not None else "—"
            sz_s = f"{r['sz_yi']:,.2f}" if r["sz_yi"] is not None else "—"
            tot_s = f"{r['total_yi']:,.2f}" if r["total_yi"] is not None else "—"
            print(f"{_fmt_date(r['trade_date']):<12} {sh_s:>12} {sz_s:>12} {tot_s:>14}")
        print()
        if payload["summary"]:
            print(payload["summary"])
        else:
            print(
                f"近{days}日数据不足：历史依赖 reports/market_turnover_daily.json 逐日累积；"
                "当日由 tick 自动写入。"
            )
            missing = [r["trade_date"] for r in rows if r["total_yi"] is None]
            if missing:
                print(f"缺失交易日: {', '.join(_fmt_date(d) for d in missing)}")

    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
