"""orders_util 买卖汇总测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from orders_util import build_stock_trade_summary


def test_stock_summary_credit_sell_types():
    """卖券还款/融资买入应归入卖出/买入，而非展示名键。"""
    orders = [
        {
            "stock_code": "300476.SZ",
            "order_type": 31,  # 卖券还款
            "traded_volume": 400,
        },
        {
            "stock_code": "600584.SH",
            "order_type": 27,  # 融资买入
            "traded_volume": 400,
        },
        {
            "stock_code": "600584.SH",
            "order_type": 31,  # 卖券还款
            "traded_volume": 400,
        },
    ]
    summary = build_stock_trade_summary(orders, [])
    assert summary["300476.SZ"] == {"买入": 0, "卖出": 400}
    assert summary["600584.SH"] == {"买入": 400, "卖出": 400}
