"""信用账户持仓拆分：融资买入 vs 担保品（对齐 QMT 内置脚本逻辑）。"""

from __future__ import annotations

from typing import Any

# QMT / xtquant：48=融资合约（m_eCompactType / compact_type）
COMPACT_TYPE_FIN_BUY = 48


def _position_code(record: dict[str, Any]) -> str:
    return str(
        record.get("stock_code")
        or record.get("instrument_id")
        or record.get("m_strInstrumentID")
        or ""
    ).strip()


def _compact_type(record: dict[str, Any]) -> int | None:
    raw = record.get("compact_type")
    if raw is None:
        raw = record.get("m_eCompactType")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _compact_volume(record: dict[str, Any]) -> int:
    for key in ("real_compact_vol", "m_nRealCompactVol", "business_vol", "m_nBusinessVol"):
        raw = record.get(key)
        if raw is None:
            continue
        try:
            vol = int(raw)
        except (TypeError, ValueError):
            continue
        if vol > 0:
            return vol
    return 0


def _position_volume(record: dict[str, Any]) -> int:
    raw = record.get("volume")
    if raw is None:
        raw = record.get("m_nVolume")
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def margin_volume_by_code(compacts: list[dict[str, Any]]) -> dict[str, int]:
    """汇总未还融资合约数量（仅 compact_type=48）。"""
    out: dict[str, int] = {}
    for item in compacts:
        if not isinstance(item, dict):
            continue
        if _compact_type(item) != COMPACT_TYPE_FIN_BUY:
            continue
        code = _position_code(item)
        if not code:
            continue
        out[code] = out.get(code, 0) + _compact_volume(item)
    return out


def build_credit_position_breakdown(
    compacts: list[dict[str, Any]],
    positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """总持仓 = 融资买入 + 担保品买入（与参考 handlebar 逻辑一致）。"""
    margin_map = margin_volume_by_code(compacts)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pos in positions:
        if not isinstance(pos, dict):
            continue
        code = _position_code(pos)
        if not code:
            continue
        total = _position_volume(pos)
        margin = margin_map.get(code, 0)
        collateral = max(total - margin, 0)
        rows.append(
            {
                "stock_code": code,
                "total_volume": total,
                "margin_volume": margin,
                "collateral_volume": collateral,
                "can_use_volume": int(
                    pos.get("can_use_volume") or pos.get("m_nCanUseVolume") or 0
                ),
                "market_value": pos.get("market_value") or pos.get("m_dMarketValue"),
            }
        )
        seen.add(code)

    for code, margin in margin_map.items():
        if code in seen:
            continue
        rows.append(
            {
                "stock_code": code,
                "total_volume": margin,
                "margin_volume": margin,
                "collateral_volume": 0,
                "can_use_volume": 0,
                "market_value": None,
            }
        )

    return rows
