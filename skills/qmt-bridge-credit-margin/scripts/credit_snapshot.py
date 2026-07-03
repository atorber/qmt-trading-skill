#!/usr/bin/env python3
"""两融账户只读快照（需信用账户）。

用法:
    python skills/qmt-bridge-credit-margin/scripts/credit_snapshot.py --port 8080 --api-key KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, fmt_num, load_env_files, make_client, resolve_account_type_for_id, unwrap_data  # noqa: E402
from credit_positions_util import build_credit_position_breakdown  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402


def _credit_call(client, method, account_id: str, account_type: str = ""):
    return unwrap_data(
        call_api(method, account_id=account_id, account_type=account_type, raise_on_error=False)
    )


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="两融账户快照（只读）")
    add_client_args(parser)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # 信用快照默认使用信用户，而非全局默认户（可能是普通户）
    if args.account_id is None:
        args.account_id = os.environ.get("QMT_BRIDGE_CREDIT_ACCOUNT_ID") or None

    client, account_id = make_client(args)
    account_type = resolve_account_type_for_id(
        account_id,
        getattr(args, "account_type", None) or "",
    )

    try:
        detail = _credit_call(
            client, client.query_credit_detail, account_id, account_type=account_type or "CREDIT"
        )
        positions = _credit_call(
            client,
            client.query_credit_positions,
            account_id,
            account_type=account_type or "CREDIT",
        )
        debt = _credit_call(
            client, client.query_stk_compacts, account_id, account_type=account_type or "CREDIT"
        )
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
    if not isinstance(debt, list):
        debt = []

    breakdown = build_credit_position_breakdown(debt, positions)
    codes = [
        str(row.get("stock_code") or "").strip()
        for row in breakdown
        if row.get("stock_code")
    ]
    name_map = fetch_stock_names(client, codes) if codes else {}

    if args.json:
        print(
            json.dumps(
                {
                    "detail": detail,
                    "positions": positions,
                    "debt": debt,
                    "breakdown": breakdown,
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
    if account_type:
        print(f"account_type: {account_type or 'CREDIT'}")
    print(f"资产概要: {detail}")
    print(f"负债合约: {len(debt)} 条")
    print(f"--- 信用持仓拆分 ({len(breakdown)}) ---")
    if not breakdown:
        print("  (无)")
    for row in breakdown[:30]:
        code = row.get("stock_code", "?")
        sym = label_stock(code, name_map)
        total = row.get("total_volume", 0)
        margin = row.get("margin_volume", 0)
        collateral = row.get("collateral_volume", 0)
        mv = row.get("market_value")
        line = (
            f"  {sym}  总={total}  融资={margin}  担保品={collateral}"
        )
        if mv is not None:
            line += f"  mv={fmt_num(mv)}"
        print(line)
    if len(breakdown) > 30:
        print(f"  ... 共 {len(breakdown)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
