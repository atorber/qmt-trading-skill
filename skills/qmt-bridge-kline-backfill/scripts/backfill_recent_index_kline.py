#!/usr/bin/env python3
"""校验近 N 日两市成交额是否可用于复盘（不触发历史 K 线下载）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, load_env_files, make_client  # noqa: E402
from market_turnover_util import ensure_recent_turnover  # noqa: E402


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(
        description="校验近N日两市成交额（复盘前置，market_data+缓存）"
    )
    add_client_args(parser)
    parser.add_argument("--days", type=int, default=3, help="近几日校验，默认3")
    parser.add_argument(
        "--try-history",
        action="store_true",
        help="可选：尝试 get_market_data 补历史（可能超时/BSON，默认关闭）",
    )
    parser.add_argument("--json", action="store_true", help="输出JSON")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)
    days = max(1, int(args.days))
    payload = ensure_recent_turnover(client, days, try_history=args.try_history)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, default=str))
    else:
        print("=== 近N日两市成交额校验 ===")
        print(f"方式: {payload.get('method')}")
        print(f"缓存: {payload.get('cache_path')}")
        target = payload.get("target_dates") or []
        print(f"目标交易日: {', '.join(target) if target else '(无)'}")
        print(f"深市使用: {payload.get('sz_code_used')}")
        if payload.get("ok"):
            print(f"结果: OK（近{days}日沪深成交额均可用）")
        else:
            print(f"结果: NOT OK（近{days}日仍有缺失）")
            missing_sh = payload.get("missing_sh_dates") or []
            missing_sz = payload.get("missing_sz_dates") or []
            if missing_sh:
                print(f"  - 上证缺失: {', '.join(missing_sh)}")
            if missing_sz:
                print(f"  - 深市缺失: {', '.join(missing_sz)}")

    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
