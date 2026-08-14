#!/usr/bin/env python3
"""组合风险快照：权重、现金、集中度、T+1 可卖（只读）。

用法:
    python skills/qmt-bridge-portfolio-risk/scripts/portfolio_snapshot.py
    python skills/qmt-bridge-portfolio-risk/scripts/portfolio_snapshot.py --warn-weight 0.25
"""

from __future__ import annotations

import argparse
import json
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


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 组合风险快照（只读）")
    add_client_args(parser)
    parser.add_argument(
        "--warn-weight",
        type=float,
        default=0.30,
        help="单票权重超过该比例时警告（默认 0.30）",
    )
    parser.add_argument(
        "--min-cash-ratio",
        type=float,
        default=0.0,
        help="现金占总资产低于该比例时警告（默认 0 不检查）",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    client, account_id = make_client(args)

    asset = unwrap_data(call_api(client.query_asset, account_id=account_id))
    if not isinstance(asset, dict):
        asset = {}

    positions = unwrap_data(call_api(client.query_positions, account_id=account_id))
    if not isinstance(positions, list):
        positions = []

    total_asset = float(asset.get("total_asset") or 0)
    cash = float(asset.get("cash") or 0)
    market_value = float(asset.get("market_value") or 0)

    if total_asset <= 0:
        pos_mv_sum = sum(float(p.get("market_value") or 0) for p in positions)
        total_asset = pos_mv_sum + cash if (pos_mv_sum + cash) > 0 else 1.0

    rows: list[dict] = []

    for p in positions:
        code = p.get("stock_code", "?")
        vol = int(p.get("volume") or 0)
        usable = int(p.get("can_use_volume") or 0)
        mv = float(p.get("market_value") or 0)
        weight = mv / total_asset if total_asset else 0.0
        rows.append({
            "stock_code": code,
            "volume": vol,
            "can_use_volume": usable,
            "market_value": mv,
            "weight": round(weight, 4),
        })

    cash_ratio = cash / total_asset if total_asset else 0.0

    rows.sort(key=lambda r: r["weight"], reverse=True)

    codes = [r["stock_code"] for r in rows if r.get("stock_code")]
    name_map = fetch_stock_names(client, codes)
    for r in rows:
        code = r["stock_code"]
        r["stock_name"] = name_map.get(code) or name_map.get(code.upper()) or ""

    warnings: list[str] = []
    for r in rows:
        code = r["stock_code"]
        sym = label_stock(code, name_map)
        weight = r["weight"]
        vol = r["volume"]
        usable = r["can_use_volume"]
        if weight >= args.warn_weight and vol > 0:
            warnings.append(f"集中度: {sym} 权重 {weight:.1%} >= {args.warn_weight:.0%}")
        if vol > 0 and usable < vol:
            warnings.append(
                f"T+1: {sym} 可卖 {usable} < 持仓 {vol}（差额 {vol - usable} 不可卖）"
            )
    if args.min_cash_ratio > 0 and cash_ratio < args.min_cash_ratio:
        warnings.append(
            f"现金占比 {cash_ratio:.1%} < 阈值 {args.min_cash_ratio:.0%}"
        )

    if args.json:
        print(
            json.dumps(
                {
                    "account_id": account_id,
                    "asset": asset,
                    "stock_names": name_map,
                    "positions": rows,
                    "cash_ratio": round(cash_ratio, 4),
                    "warnings": warnings,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print("=== QMT Bridge 组合风险快照 ===")
    if account_id:
        print(f"account_id: {account_id}")
    print(
        f"总资产={fmt_num(total_asset)}  现金={fmt_num(cash)} ({cash_ratio:.1%})  "
        f"持仓市值={fmt_num(market_value)}"
    )

    print(f"--- 持仓 ({len(rows)}) ---")
    if not rows:
        print("  (无持仓)")
    for r in rows:
        flag = " !" if r["weight"] >= args.warn_weight and r["volume"] > 0 else ""
        t1 = ""
        if r["volume"] > 0 and r["can_use_volume"] < r["volume"]:
            t1 = " [T+1]"
        sym = label_stock(r["stock_code"], name_map)
        print(
            f"  {sym}  权重={r['weight']:.1%}  "
            f"vol={r['volume']}  can_use={r['can_use_volume']}  "
            f"mv={fmt_num(r['market_value'])}{t1}{flag}"
        )

    if warnings:
        print("--- 风险提示 ---")
        for w in warnings:
            print(f"  * {w}")
    else:
        print("--- 风险提示 ---")
        print("  (无)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
