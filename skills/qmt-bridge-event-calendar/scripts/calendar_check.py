#!/usr/bin/env python3
"""交易日与交易时段检查（只读）。

用法:
    python skills/qmt-bridge-event-calendar/scripts/calendar_check.py
    python skills/qmt-bridge-event-calendar/scripts/calendar_check.py --market SH --date 20260519
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

from common import add_client_args, call_api, load_env_files, make_client  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="交易日历检查（只读）")
    add_client_args(parser)
    parser.add_argument("--market", default="SH", help="市场 SH/SZ（默认 SH）")
    parser.add_argument(
        "--date",
        default="",
        help="日期 YYYYMMDD，默认今天",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    d = args.date or date.today().strftime("%Y%m%d")
    client, _ = make_client(args, require_api_key=False)

    is_td = call_api(client.is_trading_date, args.market, d)
    prev_d = call_api(client.get_prev_trading_date, args.market, d)
    next_d = call_api(client.get_next_trading_date, args.market, d)
    period = call_api(client.get_trading_period, "600000.SH")

    payload = {
        "market": args.market,
        "date": d,
        "is_trading_date": is_td,
        "prev_trading_date": prev_d,
        "next_trading_date": next_d,
        "trading_period_sample": period,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0

    print("=== QMT Bridge 交易日历 ===")
    print(f"市场={args.market}  日期={d}")
    print(f"是否交易日: {is_td}")
    print(f"上一交易日: {prev_d}")
    print(f"下一交易日: {next_d}")
    print(f"交易时段(示例 600000.SH): {period}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
