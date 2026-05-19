"""持仓代码列表（供筛选、再平衡等脚本复用）。"""

from __future__ import annotations

from common import call_api, unwrap_data


def fetch_position_codes(client, account_id: str) -> list[str]:
    """查询当前持仓股票代码（去重、保序）。"""
    positions = unwrap_data(
        call_api(client.query_positions, account_id=account_id)
    )
    if not isinstance(positions, list):
        return []
    seen: set[str] = set()
    codes: list[str] = []
    for p in positions:
        if not isinstance(p, dict):
            continue
        code = str(p.get("stock_code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    return codes
