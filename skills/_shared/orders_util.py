"""委托/成交列表解析与展示。"""

from __future__ import annotations

from typing import Any

from trading_fmt import format_order_time, order_side, order_status_label, pick


def as_list(resp: Any) -> list[dict]:
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        return [resp]
    return []


def slippage_bps(order_price: float, traded_price: float, side: str) -> float | None:
    """滑点（基点）：买入为正表示买贵了，卖出为正表示卖便宜了。"""
    if not order_price or not traded_price:
        return None
    diff = (traded_price - order_price) / order_price * 10000
    if side == "卖出":
        diff = -diff
    return round(diff, 1)


def print_orders_table(
    orders: list[dict],
    *,
    title: str = "委托",
    name_map: dict[str, str] | None = None,
) -> None:
    from stock_names import label_stock

    print(f"--- {title} ({len(orders)}) ---")
    if not orders:
        print("  (无)")
        return
    for o in sorted(orders, key=lambda x: pick(x, "order_time", "m_nOrderTime", default=0)):
        code = pick(o, "stock_code", "m_strStockCode", default="?")
        sym = label_stock(code, name_map)
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        vol = int(pick(o, "order_volume", "m_nOrderVolume", default=0) or 0)
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        price = float(pick(o, "price", "m_dPrice", default=0) or 0)
        tprice = float(pick(o, "traded_price", "m_dTradedPrice", default=0) or 0)
        status = order_status_label(pick(o, "order_status", "m_nOrderStatus"))
        t = format_order_time(pick(o, "order_time", "m_nOrderTime"))
        sysid = pick(o, "order_sysid", "m_strOrderSysID", default="")
        slip = ""
        if traded > 0 and price > 0 and tprice > 0:
            bps = slippage_bps(price, tprice, side)
            if bps is not None:
                slip = f"  slip={bps:+.1f}bp"
        print(
            f"  {t}  {sym}  {side}  {vol}@{price:.2f}  "
            f"成交{traded}@{tprice:.2f}  {status}  sysid={sysid}{slip}"
        )


def summarize_by_stock(
    orders: list[dict],
    trades: list[dict],
    *,
    name_map: dict[str, str] | None = None,
) -> None:
    from stock_names import label_stock
    """按标的汇总当日买卖量。"""
    summary: dict[str, dict[str, int]] = {}
    for o in orders:
        code = pick(o, "stock_code", "m_strStockCode", default="")
        if not code:
            continue
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        if code not in summary:
            summary[code] = {"买入": 0, "卖出": 0}
        if traded > 0:
            summary[code][side] = summary[code].get(side, 0) + traded
    if trades:
        for t in trades:
            code = pick(t, "stock_code", "m_strStockCode", default="")
            if not code or code in summary:
                continue
            summary[code] = {"买入": 0, "卖出": 0}

    if not summary:
        return
    print("--- 按标的成交汇总 ---")
    for code in sorted(summary):
        b = summary[code].get("买入", 0)
        s = summary[code].get("卖出", 0)
        sym = label_stock(code, name_map)
        print(f"  {sym}  买入={b}  卖出={s}  净={b - s}")
