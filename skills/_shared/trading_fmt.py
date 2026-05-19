"""交易字段显示：方向、状态、时间、市场代码。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

ORDER_TYPE_LABEL = {
    23: "买入",
    24: "卖出",
}

# QMT / xtquant 常见委托状态（未知码原样显示）
ORDER_STATUS_LABEL = {
    48: "未报",
    49: "待报",
    50: "已报",
    51: "已报待撤",
    52: "部成待撤",
    53: "部撤",
    54: "已撤",
    55: "部成",
    56: "已成",
    57: "废单",
    58: "已报待改",
}


def order_side(order_type: Any) -> str:
    try:
        return ORDER_TYPE_LABEL.get(int(order_type), f"类型{order_type}")
    except (TypeError, ValueError):
        return "?"


def order_status_label(status: Any) -> str:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return str(status)
    name = ORDER_STATUS_LABEL.get(code)
    return f"{name}({code})" if name else str(code)


def market_from_stock(stock_code: str) -> str:
    """从 600519.SH 提取交易所后缀 SH/SZ 等。"""
    if "." in stock_code:
        return stock_code.rsplit(".", 1)[-1].upper()
    return ""


def format_order_time(value: Any) -> str:
    if value is None:
        return "-"
    try:
        ts = int(value)
        if ts > 1_000_000_000_000:
            ts //= 1000
        if ts > 1_000_000_000:
            return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except (TypeError, ValueError, OSError):
        pass
    return str(value)


def pick(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default
