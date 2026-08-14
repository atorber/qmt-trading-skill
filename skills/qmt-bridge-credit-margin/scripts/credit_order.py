#!/usr/bin/env python3
"""信用交易下单：默认仅预览，须 --execute --confirm 才会真实提交。

支持融资买入 / 融券卖出 / 买券还券 / 卖券还款（通过 order_type 常量区分）。
账户默认取 .env 中 QMT_BRIDGE_CREDIT_ACCOUNT_ID。

用法:
    python skills/qmt-bridge-credit-margin/scripts/credit_order.py 000001.SZ --finance-buy --volume 100
    python skills/qmt-bridge-credit-margin/scripts/credit_order.py 600519.SH --sell-repay --volume 100 --limit 1800.0 --execute --confirm
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, load_env_files, make_client  # noqa: E402
from stock_names import fetch_stock_names, label_stock  # noqa: E402
from trading_fmt import ORDER_TYPE_LABEL  # noqa: E402

# 信用委托类型（对齐 xtquant.xtconstant）
CREDIT_FIN_BUY = 27       # 融资买入
CREDIT_SLO_SELL = 28      # 融券卖出
CREDIT_BUY_SECU_REPAY = 29   # 买券还券
CREDIT_SELL_SECU_REPAY = 31  # 卖券还款


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="QMT Bridge 信用交易下单（默认预览）")
    add_client_args(parser)
    parser.add_argument("stock_code", help="股票代码，如 000001.SZ")
    direction = parser.add_mutually_exclusive_group(required=True)
    direction.add_argument(
        "--finance-buy", action="store_true", help="融资买入 (order_type=27)"
    )
    direction.add_argument(
        "--short-sell", action="store_true", help="融券卖出 (order_type=28)"
    )
    direction.add_argument(
        "--buy-repay", action="store_true", help="买券还券 (order_type=29)"
    )
    direction.add_argument(
        "--sell-repay", action="store_true", help="卖券还款 (order_type=31)"
    )
    parser.add_argument("--volume", type=int, required=True, help="委托数量（股）")
    parser.add_argument(
        "--price-type",
        type=int,
        default=5,
        help="报价类型：5=最新价，11=限价（默认 5）",
    )
    parser.add_argument(
        "--limit",
        dest="price",
        type=float,
        default=0.0,
        help="限价价格（自动切换 price_type=11）",
    )
    parser.add_argument("--remark", default="agent-credit", help="委托备注")
    parser.add_argument("--strategy", default="", help="策略名称")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真实提交（默认仅预览）",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="与 --execute 同时使用，确认实盘下单",
    )
    args = parser.parse_args()

    if args.finance_buy:
        order_type = CREDIT_FIN_BUY
    elif args.short_sell:
        order_type = CREDIT_SLO_SELL
    elif args.buy_repay:
        order_type = CREDIT_BUY_SECU_REPAY
    else:
        order_type = CREDIT_SELL_SECU_REPAY
    side = ORDER_TYPE_LABEL.get(order_type, str(order_type))

    # 显式给限价时自动用限价单
    if args.price > 0 and args.price_type == 5:
        args.price_type = 11
    if args.price_type == 11 and args.price <= 0:
        print("错误: 限价单须指定 --limit > 0", file=sys.stderr)
        return 2
    if args.volume <= 0:
        print("错误: --volume 须为正整数", file=sys.stderr)
        return 2

    # 信用下单默认使用信用户，而非全局默认户（可能是普通户）
    if args.account_id is None:
        args.account_id = os.environ.get("QMT_BRIDGE_CREDIT_ACCOUNT_ID") or None
    if not args.account_id:
        print(
            "错误: 未指定信用账户。请配置 QMT_BRIDGE_CREDIT_ACCOUNT_ID 或传 --account-id",
            file=sys.stderr,
        )
        return 2

    plan = {
        "account_id": args.account_id,
        "stock_code": args.stock_code,
        "order_type": order_type,
        "side": side,
        "order_volume": args.volume,
        "price_type": args.price_type,
        "price": args.price,
        "order_remark": args.remark,
        "strategy_name": args.strategy,
    }

    client, account_id = make_client(args)
    sym = label_stock(args.stock_code, fetch_stock_names(client, [args.stock_code]))

    if not args.execute:
        print("【预览】未提交委托。确认后请加 --execute --confirm")
        print(f"  {side} {sym} x{args.volume}  account={account_id}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if not args.confirm:
        print("错误: 实盘下单须同时指定 --execute --confirm", file=sys.stderr)
        return 2

    result = call_api(
        client.credit_order,
        stock_code=args.stock_code,
        order_type=order_type,
        order_volume=args.volume,
        price_type=args.price_type,
        price=args.price,
        strategy_name=args.strategy,
        order_remark=args.remark,
        account_id=account_id,
    )
    order_id = result.get("order_id", result) if isinstance(result, dict) else result
    print(f"已提交 {side} {sym} x{args.volume}  order_id={order_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
