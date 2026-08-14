"""批量解析股票中文名称。"""

from __future__ import annotations

from typing import Any


def collect_stock_codes(*groups: list[dict]) -> list[str]:
    """从委托/成交记录中收集不重复股票代码。"""
    from trading_fmt import pick

    seen: set[str] = set()
    codes: list[str] = []
    for items in groups:
        for item in items:
            code = pick(item, "stock_code", "m_strStockCode", default="")
            if code and code not in seen:
                seen.add(code)
                codes.append(str(code))
    return codes


def fetch_stock_names(client, codes: list[str]) -> dict[str, str]:
    """调用 /api/utility/batch_stock_name；失败时返回空映射。"""
    if not codes:
        return {}
    import urllib.error

    try:
        raw = client.get_batch_stock_name(codes)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) if v else "" for k, v in raw.items()}


def label_stock(code: str, name_map: dict[str, str] | None) -> str:
    """格式化为「代码 名称」；无名称时仅代码。"""
    if not name_map:
        return code
    name = (name_map.get(code) or name_map.get(code.upper()) or "").strip()
    return f"{code} {name}" if name else code
