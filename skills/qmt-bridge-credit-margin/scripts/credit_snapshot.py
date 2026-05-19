#!/usr/bin/env python3
"""两融账户只读快照（需信用账户）。

用法:
    python skills/qmt-bridge-credit-margin/scripts/credit_snapshot.py --port 8080 --api-key KEY
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, fmt_num, load_env_files, make_client, unwrap_data  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def _credit_call(client, method, account_id: str):
    return unwrap_data(
        call_api(method, account_id=account_id, raise_on_error=False)
    )


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="两融账户快照（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client, account_id = make_client(args)

    try:
        detail = _credit_call(client, client.query_credit_detail, account_id)
        positions = _credit_call(client, client.query_credit_positions, account_id)
        debt = _credit_call(client, client.query_stk_compacts, account_id)
    except urllib.error.HTTPError as exc:
        print(
            "两融数据不可用 "
            f"(HTTP {exc.code})。可能未开通信用账户或服务端未启用信用模块。",
            file=sys.stderr,
        )
        if args.json:
            print(json.dumps({"error": exc.code, "hint": "no_credit_account"}, ensure_ascii=False))
        return 0

    if not isinstance(positions, list):
        positions = []

    codes = [
        str(p.get("stock_code") or "").strip()
        for p in positions
        if isinstance(p, dict) and p.get("stock_code")
    ]
    name_map = fetch_stock_names(client, codes) if codes else {}

    if args.json:
        print(
            json.dumps(
                {
                    "detail": detail,
                    "positions": positions,
                    "debt": debt,
                    "stock_names": name_map,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print("=== 两融账户快照 ===")
    if account_id:
        print(f"account_id: {account_id}")
    print(f"资产概要: {detail}")
    print(f"负债概要: {debt}")
    print(f"--- 信用持仓 ({len(positions)}) ---")
    if not positions:
        print("  (无)")
    for p in positions[:30]:
        code = p.get("stock_code", "?")
        sym = label_stock(code, name_map)
        vol = p.get("volume", p.get("current_amount", "?"))
        mv = p.get("market_value")
        line = f"  {sym}  vol={vol}"
        if mv is not None:
            line += f"  mv={fmt_num(mv)}"
        print(line)
    if len(positions) > 30:
        print(f"  ... 共 {len(positions)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
