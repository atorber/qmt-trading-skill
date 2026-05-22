"""execution_review_eval 单元测试（无需 Bridge）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared"))

from execution_review_eval import (  # noqa: E402
    build_operation_evaluation,
    market_turnover_yi_from_tick_map,
)
from pnl_util import DailyPnlBreakdown, TradeDaySummary  # noqa: E402


def test_kline_amount_yuan_by_date_from_records():
    from execution_review_eval import _kline_amount_yuan_by_date  # noqa: E402

    recs = [{"index": "20260522", "amount": 1_200_000_000_000}]
    assert _kline_amount_yuan_by_date(recs) == {"20260522": 1_200_000_000_000.0}


def test_market_turnover_yi_from_tick_map():
    tick_map = {
        "000001.SH": {"amount": 1_200_000_000_000},
        "399106.SZ": {"amount": 800_000_000_000},
    }
    assert market_turnover_yi_from_tick_map(tick_map) == 20000.0

    assert market_turnover_yi_from_tick_map({}) is None
    assert market_turnover_yi_from_tick_map({"000001.SH": {"amount": 100}}) is None

    fallback = {
        "000001.SH": {"amount": 1_000_000_000_000},
        "399001.SZ": {"amount": 500_000_000_000},
    }
    assert market_turnover_yi_from_tick_map(fallback) == 15000.0


def test_build_operation_evaluation_with_turnover():
    ev = build_operation_evaluation(
        orders=[],
        trades=[],
        breakdowns=[],
        asset={"total_asset": 1_000_000, "cash": 100_000},
        name_map={},
        cancelled_count=0,
        market_turnover_yi=12500.0,
    )
    assert ev.philosophy is not None
    assert ev.philosophy.market_turnover_yi == 12500.0
    assert ev.philosophy.volume_zone is not None
    assert ev.philosophy.volume_zone.label == "适度参与区"


def test_build_operation_evaluation():
    b1 = DailyPnlBreakdown(
        stock_code="600584.SH",
        current_volume=2000,
        yesterday_volume=3700,
        last_price=66.0,
        pre_close=60.0,
        daily_pnl=20000.0,
        overnight_pnl=20000.0,
        buy_pnl=None,
        sell_pnl=-100.0,
        trade_summary=TradeDaySummary(sell_volume=1700, sell_amount=110000),
        source="trades",
    )
    b2 = DailyPnlBreakdown(
        stock_code="300394.SZ",
        current_volume=900,
        yesterday_volume=500,
        last_price=355.0,
        pre_close=363.0,
        daily_pnl=-5000.0,
        overnight_pnl=None,
        buy_pnl=-2000.0,
        sell_pnl=None,
        trade_summary=TradeDaySummary(buy_volume=400, buy_amount=140000),
        source="trades",
    )
    ev = build_operation_evaluation(
        orders=[],
        trades=[],
        breakdowns=[b1, b2],
        asset={"total_asset": 900000, "cash": 5000},
        name_map={"600584.SH": "长电", "300394.SZ": "天孚"},
        cancelled_count=2,
    )
    assert ev.total_daily_pnl == 15000.0
    assert ev.overall_score >= 5
    assert len(ev.stocks) == 2
    assert any(s.operation_label == "大涨止盈" for s in ev.stocks)
    assert ev.philosophy is not None
    assert ev.philosophy.sector_summary.startswith("持仓板块")
