"""信用持仓拆分单元测试。"""

from qmt_bridge.credit_positions import build_credit_position_breakdown, margin_volume_by_code


def test_margin_volume_from_compacts():
    compacts = [
        {"compact_type": 48, "instrument_id": "600000.SH", "real_compact_vol": 100},
        {"compact_type": 48, "instrument_id": "600000.SH", "real_compact_vol": 50},
        {"compact_type": 49, "instrument_id": "000001.SZ", "real_compact_vol": 200},
    ]
    assert margin_volume_by_code(compacts) == {"600000.SH": 150}


def test_build_credit_position_breakdown():
    compacts = [
        {"compact_type": 48, "instrument_id": "301308.SZ", "real_compact_vol": 100},
    ]
    positions = [
        {"stock_code": "301308.SZ", "volume": 300, "market_value": 180000},
    ]
    rows = build_credit_position_breakdown(compacts, positions)
    assert len(rows) == 1
    assert rows[0]["total_volume"] == 300
    assert rows[0]["margin_volume"] == 100
    assert rows[0]["collateral_volume"] == 200
