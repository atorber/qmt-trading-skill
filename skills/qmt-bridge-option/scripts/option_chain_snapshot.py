#!/usr/bin/env python3
"""期权链摘要（只读）。

用法:
    python skills/qmt-bridge-option/scripts/option_chain_snapshot.py --undl 510050.SH
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import urllib.error

from common import add_client_args, call_api, load_env_files, make_client, unwrap_data  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def _count_leaves(obj, depth: int = 0) -> int:
    if depth > 8:
        return 0
    if isinstance(obj, dict):
        return sum(_count_leaves(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        return len(obj) if all(isinstance(x, str) for x in obj) else sum(
            _count_leaves(x, depth + 1) for x in obj
        )
    return 1


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="期权链摘要（只读）")
    add_client_args(parser)
    parser.add_argument("--undl", required=True, help="标的代码，如 510050.SH")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client, _ = make_client(args, require_api_key=False)
    sym = label_stock(args.undl, fetch_stock_names(client, [args.undl]))
    try:
        chain = unwrap_data(
            call_api(client.get_option_chain, args.undl, raise_on_error=False)
        )
    except urllib.error.HTTPError as exc:
        print(
            f"期权链不可用 (HTTP {exc.code})，标的 {sym}。"
            "请确认代码为期权标的（如 510050.SH）且 QMT 已登录。",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(chain, ensure_ascii=False, default=str))
        return 0

    print(f"=== 期权链 {sym} ===")
    if isinstance(chain, dict):
        print(f"  顶层键: {list(chain.keys())[:15]}")
        print(f"  节点规模(估计): {_count_leaves(chain)}")
    else:
        print(f"  数据类型: {type(chain).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
