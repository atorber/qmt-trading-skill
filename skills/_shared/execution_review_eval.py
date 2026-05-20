"""当日交易操作评价：结合委托/成交、盈亏拆解与执行质量。"""

from __future__ import annotations

from dataclasses import dataclass, field

from orders_util import slippage_bps
from pnl_util import DailyPnlBreakdown, TradeDaySummary
from trading_fmt import order_side, pick


@dataclass
class StockOpEval:
    stock_code: str
    stock_name: str
    daily_pnl: float | None = None
    pct_chg: float | None = None
    buy_volume: int = 0
    sell_volume: int = 0
    yesterday_volume: int = 0
    current_volume: int = 0
    operation_label: str = ""
    watch_note: str = ""


@dataclass
class DailyOperationEval:
    total_daily_pnl: float | None = None
    total_asset: float | None = None
    cash: float | None = None
    order_count: int = 0
    cancelled_count: int = 0
    trade_count: int = 0
    overall_score: float = 0.0
    overall_grade: str = ""
    summary_line: str = ""
    positives: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    execution_notes: list[str] = field(default_factory=list)
    discipline_tips: list[str] = field(default_factory=list)
    stocks: list[StockOpEval] = field(default_factory=list)


def _pct_chg(b: DailyPnlBreakdown) -> float | None:
    if b.last_price is None or b.pre_close is None or b.pre_close == 0:
        return None
    return round((b.last_price / b.pre_close - 1) * 100, 2)


def _classify_operation(
    b: DailyPnlBreakdown,
    pct: float | None,
) -> tuple[str, str]:
    t = b.trade_summary
    if not t.has_trades:
        return "持股未交易", "无主动调仓"

    if t.sell_volume > 0 and t.buy_volume == 0:
        if pct is not None and pct >= 3:
            return "大涨止盈", "逢高减仓兑现"
        if pct is not None and pct <= -1:
            return "弱势减仓", "下跌中卖出"
        return "减仓", "卖出为主"

    if t.buy_volume > 0 and t.sell_volume == 0:
        if pct is not None and pct <= -2:
            return "逆势加仓", "下跌中买入，注意止损纪律"
        if pct is not None and pct >= 2:
            return "顺势加仓", "上涨中加仓，忌追高"
        return "加仓", "买入为主"

    return "买卖调仓", "同日有买有卖"


def _analyze_orders(orders: list[dict], name_map: dict[str, str]) -> list[str]:
    notes: list[str] = []
    bad_slips: list[str] = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        if traded <= 0:
            continue
        price = float(pick(o, "price", "m_dPrice", default=0) or 0)
        tprice = float(pick(o, "traded_price", "m_dTradedPrice", default=0) or 0)
        side = order_side(pick(o, "order_type", "m_nOrderType"))
        code = pick(o, "stock_code", "m_strStockCode", default="")
        bps = slippage_bps(price, tprice, side)
        if bps is not None and abs(bps) >= 10:
            sym = name_map.get(code, code)
            bad_slips.append(f"{sym} {side} {bps:+.1f}bp")

    if bad_slips:
        notes.append("滑点偏大：" + "；".join(bad_slips))
    return notes


def build_operation_evaluation(
    *,
    orders: list[dict],
    trades: list[dict],
    breakdowns: list[DailyPnlBreakdown],
    asset: dict | None,
    name_map: dict[str, str],
    cancelled_count: int,
) -> DailyOperationEval:
    """生成当日操作评价（统计归纳，非投资建议）。"""
    result = DailyOperationEval(
        order_count=len(orders),
        cancelled_count=cancelled_count,
        trade_count=len(trades),
    )

    if isinstance(asset, dict):
        result.total_asset = _to_float(
            pick(asset, "total_asset", "m_dTotalAsset")
        )
        result.cash = _to_float(pick(asset, "cash", "m_dCash"))

    total_pnl = 0.0
    has_pnl = False
    for b in breakdowns:
        if b.daily_pnl is not None:
            total_pnl += b.daily_pnl
            has_pnl = True
    if has_pnl:
        result.total_daily_pnl = round(total_pnl, 2)

    for b in breakdowns:
        code = b.stock_code
        pct = _pct_chg(b)
        label, watch = _classify_operation(b, pct)
        result.stocks.append(
            StockOpEval(
                stock_code=code,
                stock_name=name_map.get(code, ""),
                daily_pnl=b.daily_pnl,
                pct_chg=pct,
                buy_volume=b.trade_summary.buy_volume,
                sell_volume=b.trade_summary.sell_volume,
                yesterday_volume=b.yesterday_volume,
                current_volume=b.current_volume,
                operation_label=label,
                watch_note=watch,
            )
        )

    result.stocks.sort(
        key=lambda s: (s.daily_pnl is None, -(s.daily_pnl or 0)),
    )

    # 做得好的
    for s in result.stocks:
        if s.daily_pnl is not None and s.daily_pnl > 5000 and s.sell_volume > s.buy_volume:
            result.positives.append(
                f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}（卖{s.sell_volume}/买{s.buy_volume}）"
            )
        elif s.daily_pnl is not None and s.daily_pnl > 3000 and s.operation_label == "顺势加仓":
            result.positives.append(
                f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}"
            )

    # 需改进（仅对有主动交易的标的）
    for s in result.stocks:
        traded = s.buy_volume > 0 or s.sell_volume > 0
        if not traded:
            if s.daily_pnl is not None and s.daily_pnl > 5000 and (s.pct_chg or 0) >= 3:
                result.positives.append(
                    f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}（{s.pct_chg:+.2f}%），持股浮盈未调仓"
                )
            continue
        if s.daily_pnl is not None and s.daily_pnl < -2000:
            result.improvements.append(
                f"{_sym(s)}：当日{_fmt_pnl(s.daily_pnl)}，{s.operation_label} — {s.watch_note}"
            )
        elif s.operation_label == "逆势加仓" and s.buy_volume >= 200:
            result.improvements.append(
                f"{_sym(s)}：逆势加仓 {s.buy_volume} 股（昨{s.yesterday_volume}→今{s.current_volume}），{s.watch_note}"
            )

    if cancelled_count > 0:
        result.execution_notes.append(
            f"委托 {cancelled_count} 笔已撤，建议减少频繁改价撤单"
        )
    result.execution_notes.extend(_analyze_orders(orders, name_map))

    if result.cash is not None and result.total_asset and result.total_asset > 0:
        cash_pct = result.cash / result.total_asset * 100
        if cash_pct < 2:
            result.execution_notes.append(
                f"可用现金占比仅 {cash_pct:.1f}%，调仓弹性偏低"
            )

    score = 7.0
    if result.total_daily_pnl is not None:
        if result.total_daily_pnl > 0:
            score += 1.0
        else:
            score -= 1.5
    neg_ops = sum(1 for s in result.stocks if s.daily_pnl is not None and s.daily_pnl < 0 and s.buy_volume > 0)
    if neg_ops >= 2:
        score -= 0.5
    if len(result.positives) >= 2:
        score += 0.5
    if any("滑点偏大" in n for n in result.execution_notes):
        score -= 0.5
    if cancelled_count >= 3:
        score -= 0.3
    score = max(1.0, min(10.0, round(score, 1)))
    result.overall_score = score
    result.overall_grade = _grade(score)

    if result.total_daily_pnl is not None and result.total_daily_pnl >= 0:
        result.summary_line = (
            f"盈利日约 {_fmt_pnl(result.total_daily_pnl)}，"
            f"主动交易以{'止盈减仓' if any('止盈' in s.operation_label for s in result.stocks) else '调仓'}为主"
        )
    else:
        result.summary_line = "当日合计亏损，宜复盘买卖节奏与仓位纪律"

    result.discipline_tips = _discipline_tips(result)
    return result


def _discipline_tips(ev: DailyOperationEval) -> list[str]:
    tips: list[str] = []
    for s in ev.stocks:
        if s.operation_label == "逆势加仓":
            tips.append(f"{_sym(s)}：停止盲目摊薄，放量企稳再加仓")
        elif s.operation_label == "大涨止盈" and s.current_volume > 0:
            tips.append(f"{_sym(s)}：余仓移动止盈，勿因卖飞追高买回")
        elif s.operation_label == "顺势加仓":
            tips.append(f"{_sym(s)}：加仓单以今日买入均价为防守参考")
    if ev.cash is not None and ev.total_asset and ev.cash / ev.total_asset < 0.05:
        tips.append("账户：下次止盈可多留现金，保留调仓弹性")
    if not tips:
        tips.append("维持纪律：盘中以昨高/昨低为界，尾盘异常放量留意次日惯性")
    return tips


def _grade(score: float) -> str:
    if score >= 8:
        return "较好"
    if score >= 6:
        return "中等"
    return "待改进"


def _sym(s: StockOpEval) -> str:
    return f"{s.stock_code} {s.stock_name}".strip()


def _fmt_pnl(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f} 元"


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_operation_evaluation(ev: DailyOperationEval) -> str:
    lines = [
        "",
        "=" * 60,
        "【当日操作评价】（统计归纳，非投资建议）",
        "=" * 60,
        f"总评 {ev.overall_score}/10（{ev.overall_grade}） · {ev.summary_line}",
    ]
    if ev.total_daily_pnl is not None:
        lines.append(f"当日盈亏合计（估算）：{_fmt_pnl(ev.total_daily_pnl)}")
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.positives:
        lines.append("\n▸ 做得好的")
        for p in ev.positives:
            lines.append(f"  · {p}")

    if ev.improvements:
        lines.append("\n▸ 需改进")
        for p in ev.improvements:
            lines.append(f"  · {p}")

    if ev.execution_notes:
        lines.append("\n▸ 执行质量")
        for p in ev.execution_notes:
            lines.append(f"  · {p}")

    if ev.stocks:
        lines.append("\n▸ 分标的操作")
        for s in ev.stocks:
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            pct_s = f"{s.pct_chg:+.2f}%" if s.pct_chg is not None else "—"
            lines.append(
                f"  · {_sym(s)}：{pnl_s}（{pct_s}）| {s.operation_label} | "
                f"买{s.buy_volume}/卖{s.sell_volume} | 仓 {s.yesterday_volume}→{s.current_volume}"
            )

    if ev.discipline_tips:
        lines.append("\n▸ 明日纪律提示")
        for t in ev.discipline_tips:
            lines.append(f"  · {t}")
    lines.append("")
    return "\n".join(lines)


def operation_eval_to_dict(ev: DailyOperationEval) -> dict:
    return {
        "overall_score": ev.overall_score,
        "overall_grade": ev.overall_grade,
        "summary_line": ev.summary_line,
        "total_daily_pnl": ev.total_daily_pnl,
        "total_asset": ev.total_asset,
        "cash": ev.cash,
        "order_count": ev.order_count,
        "cancelled_count": ev.cancelled_count,
        "trade_count": ev.trade_count,
        "positives": ev.positives,
        "improvements": ev.improvements,
        "execution_notes": ev.execution_notes,
        "discipline_tips": ev.discipline_tips,
        "stocks": [
            {
                "stock_code": s.stock_code,
                "stock_name": s.stock_name,
                "daily_pnl": s.daily_pnl,
                "pct_chg": s.pct_chg,
                "buy_volume": s.buy_volume,
                "sell_volume": s.sell_volume,
                "yesterday_volume": s.yesterday_volume,
                "current_volume": s.current_volume,
                "operation_label": s.operation_label,
                "watch_note": s.watch_note,
            }
            for s in ev.stocks
        ],
    }
