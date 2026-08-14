"""信用/两融委托类型与盈亏计算测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from pnl_util import compute_daily_pnl, summarize_trades_by_code, TradeDaySummary
from trading_fmt import is_buy_order_type, order_side, order_type_label


def test_credit_fin_buy_order_type():
    assert order_type_label(27) == "融资买入"
    assert order_side(27) == "买入"
    assert is_buy_order_type(27)


def test_summarize_credit_fin_buy_trades():
    trades = [
        {
            "stock_code": "301308.SZ",
            "order_type": 27,
            "traded_volume": 100,
            "traded_price": 614.09,
            "traded_amount": 61409.0,
        },
        {
            "stock_code": "301308.SZ",
            "order_type": 27,
            "traded_volume": 100,
            "traded_price": 609.50,
            "traded_amount": 60950.0,
        },
    ]
    summary = summarize_trades_by_code(trades)["301308.SZ"]
    assert summary.buy_volume == 200
    assert summary.sell_volume == 0
    assert summary.buy_amount == 122359.0


def test_compute_daily_pnl_new_credit_position_not_market_value():
    """未识别融资买入时会把当日盈亏误算为市值；修复后应为买卖价差。"""
    trade = TradeDaySummary(buy_volume=300, buy_amount=182659.0)
    position = {
        "stock_code": "301308.SZ",
        "volume": 300,
        "yesterday_volume": 0,
    }
    tick = {"lastPrice": 599.22, "lastClose": 667.77}
    row = compute_daily_pnl(
        "301308.SZ",
        position=position,
        trade=trade,
        tick=tick,
        allow_tick=True,
    )
    assert row.daily_pnl is not None
    assert row.daily_pnl < 0
    assert row.daily_pnl != round(300 * 599.22, 2)
