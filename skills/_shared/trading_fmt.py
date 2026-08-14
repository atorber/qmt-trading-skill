"""交易字段显示：方向、状态、时间、市场代码。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# 普通 + 信用委托类型（对齐 xtquant.xtconstant）
ORDER_TYPE_LABEL: dict[int, str] = {
    23: "买入",
    24: "卖出",
    27: "融资买入",
    28: "融券卖出",
    29: "买券还券",
    30: "直接还券",
    31: "卖券还款",
    32: "直接还款",
    40: "专项融资买入",
    41: "专项融券卖出",
    42: "专项买券还券",
    43: "专项直接还券",
    44: "专项卖券还款",
    45: "专项直接还款",
}

# 计入当日买入/卖出成交量与金额的委托类型
BUY_ORDER_TYPES: frozenset[int] = frozenset({23, 27, 29, 40, 42})
SELL_ORDER_TYPES: frozenset[int] = frozenset({24, 28, 31, 41, 44})

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


def _to_order_type_int(order_type: Any) -> int | None:
    try:
        return int(order_type)
    except (TypeError, ValueError):
        return None


def is_buy_order_type(order_type: Any) -> bool:
    """是否为买入类委托（含融资买入、买券还券等）。"""
    code = _to_order_type_int(order_type)
    return code in BUY_ORDER_TYPES if code is not None else False


def is_sell_order_type(order_type: Any) -> bool:
    """是否为卖出类委托（含融券卖出、卖券还款等）。"""
    code = _to_order_type_int(order_type)
    return code in SELL_ORDER_TYPES if code is not None else False


def order_type_label(order_type: Any) -> str:
    """委托类型展示名（如「融资买入」）。"""
    code = _to_order_type_int(order_type)
    if code is None:
        return "?"
    return ORDER_TYPE_LABEL.get(code, f"类型{code}")


def order_side(order_type: Any) -> str:
    """买卖方向归类：买入 / 卖出 / 类型名（还款类等）。"""
    if is_buy_order_type(order_type):
        return "买入"
    if is_sell_order_type(order_type):
        return "卖出"
    return order_type_label(order_type)


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
