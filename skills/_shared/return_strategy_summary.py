"""基于累计涨幅与量价概率报告，生成下一交易日操作策略与观察点（统计归纳，非投资建议）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from kline_util import ReturnAnalysis


@dataclass
class StockDayStrategy:
    stock_code: str
    stock_name: str
    trend_label: str
    stance: str
    bias: str
    watch_points: list[str] = field(default_factory=list)
    strategy_lines: list[str] = field(default_factory=list)


@dataclass
class PortfolioDayStrategy:
    overview: str
    portfolio_watch: list[str] = field(default_factory=list)
    stocks: list[StockDayStrategy] = field(default_factory=list)


def _pct(analysis: ReturnAnalysis, n: int) -> float | None:
    return analysis.cumulative_pct.get(n)


def _last_day_return(analysis: ReturnAnalysis) -> float | None:
    if analysis.recent_10:
        return analysis.recent_10[-1].get("return_pct")
    return _pct(analysis, 1)


def _trend_label(analysis: ReturnAnalysis) -> str:
    d1 = _pct(analysis, 1)
    d5 = _pct(analysis, 5)
    d30 = _pct(analysis, 30)
    if d30 is None:
        return "数据不足"
    if d30 >= 25 and (d5 or 0) >= 0:
        return "中期强势"
    if d30 >= 10 and (d1 or 0) < -3:
        return "强势回调"
    if d30 <= 5 and (d5 or 0) <= 0:
        return "中期偏弱"
    if abs(d1 or 0) < 1.5 and abs(d5 or 0) < 3:
        return "震荡整理"
    return "趋势分化"


def _stat_bias(analysis: ReturnAnalysis) -> str:
    """统计意义上的次日倾向（非预测）。"""
    scores: list[tuple[str, float]] = []
    d1 = _pct(analysis, 1)
    if d1 is not None:
        if d1 <= -4:
            scores.append(("昨日大跌", -12))
        elif d1 <= -2:
            scores.append(("昨日走弱", -5))
        elif d1 >= 5:
            scores.append(("昨日大涨", 10))
        elif d1 >= 2.5:
            scores.append(("昨日走强", 5))
    if analysis.prob_recent_10_up is not None:
        scores.append(("近10日强势", analysis.prob_recent_10_up - 50))
    if analysis.prob_next_up_pattern is not None:
        scores.append(("形态", analysis.prob_next_up_pattern - 50))
    vp = analysis.volume_prob
    if vp.prob_up_after_up_high_vol is not None and vp.sample_up_high_vol >= 15:
        scores.append(("收涨放量", vp.prob_up_after_up_high_vol - 50))
    if vp.prob_up_after_vol_rising_3d is not None and vp.sample_vol_rising_3d >= 15:
        scores.append(("连增量", vp.prob_up_after_vol_rising_3d - 50))
    if vp.prob_up_volume_state is not None and vp.sample_volume_state >= 3:
        scores.append(("量价态", vp.prob_up_volume_state - 50))

    if not scores:
        return "中性（样本不足）"

    avg = sum(s for _, s in scores) / len(scores)
    if avg >= 8:
        return "统计偏多"
    if avg <= -8:
        return "统计偏空"
    return "统计中性"


def _stance(analysis: ReturnAnalysis, trend: str, bias: str) -> str:
    d1 = _pct(analysis, 1) or 0
    last = _last_day_return(analysis) or d1

    if trend == "强势回调" and last <= -4:
        return "回撤观察：不追涨，等量能企稳"
    if trend == "中期强势" and bias == "统计偏多":
        return "趋势持有观察：回踩承接优于追高"
    if trend == "中期强势" and last >= 4:
        return "短线过热观察：不宜加仓，设好移动止盈"
    if trend == "中期偏弱" or (last <= -4 and bias == "统计偏空"):
        return "防守观察：减仓或止损纪律优先"
    if trend == "震荡整理":
        return "区间震荡：高抛低吸或观望为主"
    if bias == "统计偏空":
        return "谨慎观望：确认止跌放量再考虑博弈"
    if bias == "统计偏多":
        return "偏多观察：突破昨高或放量阳线可跟踪"
    return "中性观望：等待方向选择"


def _build_watch_points(analysis: ReturnAnalysis) -> list[str]:
    pts: list[str] = []
    d1, d5, d10, d30 = _pct(analysis, 1), _pct(analysis, 5), _pct(analysis, 10), _pct(analysis, 30)
    if d1 is not None:
        pts.append(f"昨日收 {d1:+.2f}%（1日）| 5日 {d5:+.2f}% / 30日 {d30:+.2f}%" if d5 is not None and d30 is not None else f"昨日收 {d1:+.2f}%")

    if analysis.last_close is not None:
        pts.append(f"最新收盘 {analysis.last_close:.2f}，关注昨高/昨低突破与跌破")

    if analysis.prob_recent_10_up is not None and analysis.prob_baseline_up is not None:
        diff = analysis.prob_recent_10_up - analysis.prob_baseline_up
        tag = "强于历史" if diff >= 8 else ("弱于历史" if diff <= -8 else "接近历史")
        pts.append(f"近10日收涨 {analysis.prob_recent_10_up:.0f}% vs 基准 {analysis.prob_baseline_up:.0f}%（{tag}）")

    if analysis.pattern_signature:
        p = analysis.prob_next_up_pattern
        ptxt = f"{p:.1f}%" if p is not None else "—"
        pts.append(
            f"形态 [{analysis.pattern_signature}]（{analysis.pattern_effective_len}日）"
            f" → 次日收涨统计 {ptxt} (n={analysis.pattern_sample_count})"
        )

    vp = analysis.volume_prob
    if vp.volume_state_signature:
        vptxt = f"{vp.prob_up_volume_state:.1f}%" if vp.prob_up_volume_state is not None else "—"
        pts.append(f"近3日量价 {vp.volume_state_signature} → 次日收涨统计 {vptxt}")

    if analysis.recent_10:
        last = analysis.recent_10[-1]
        vol_tag = last.get("vol_tag") or ""
        if last.get("direction") == "跌" and vol_tag == "放量":
            pts.append("昨日放量下跌：警惕惯性下探，观察是否缩量止跌")
        elif last.get("direction") == "涨" and vol_tag == "放量":
            pts.append("昨日放量上涨：关注冲高量能是否持续或冲高回落")
        elif last.get("direction") == "涨" and vol_tag == "缩量":
            pts.append("昨日缩量上涨：上攻持续性存疑，突破需补量")

    if vp.prob_up_after_up_high_vol is not None and vp.sample_up_high_vol >= 15:
        pts.append(
            f"历史收涨放量后次日收涨 {vp.prob_up_after_up_high_vol:.1f}% (n={vp.sample_up_high_vol})"
        )
    if vp.up_days_volume_confirmed_pct is not None:
        pts.append(f"近10日收涨日中放量确认占比 {vp.up_days_volume_confirmed_pct:.0f}%")

    return pts


def _strategy_lines(stance: str, bias: str, trend: str) -> list[str]:
    lines = [f"【一日倾向】{bias} · {trend} · {stance}"]
    if "偏多" in bias:
        lines.append("→ 若高开：不盲目追；若平开缩量回踩昨收附近企稳，可小仓试探（纪律止损）")
        lines.append("→ 若低开：看 30 分钟能否收复昨收；收复则弱转强，否则观望")
    elif "偏空" in bias:
        lines.append("→ 若低开：避免抄底接飞刀；反弹至昨收/5日线附近承压可考虑减亏")
        lines.append("→ 若高开：警惕诱多，无量冲高宜减仓而非加仓")
    else:
        lines.append("→ 盘中以昨高、昨低为界：突破放量看多一日，跌破缩量看弱一日")
    return lines


def build_stock_day_strategy(
    analysis: ReturnAnalysis,
    stock_name: str = "",
) -> StockDayStrategy | None:
    if analysis.error:
        return StockDayStrategy(
            stock_code=analysis.stock_code,
            stock_name=stock_name,
            trend_label="—",
            stance="跳过",
            bias="—",
            watch_points=[analysis.error],
            strategy_lines=[],
        )
    trend = _trend_label(analysis)
    bias = _stat_bias(analysis)
    stance = _stance(analysis, trend, bias)
    return StockDayStrategy(
        stock_code=analysis.stock_code,
        stock_name=stock_name,
        trend_label=trend,
        stance=stance,
        bias=bias,
        watch_points=_build_watch_points(analysis),
        strategy_lines=_strategy_lines(stance, bias, trend),
    )


def build_portfolio_day_strategy(
    analyses: list[ReturnAnalysis],
    name_map: dict[str, str],
) -> PortfolioDayStrategy:
    stocks: list[StockDayStrategy] = []
    ranked: list[tuple[float, str, ReturnAnalysis]] = []
    for a in analyses:
        name = name_map.get(a.stock_code, "")
        brief = build_stock_day_strategy(a, name)
        if brief:
            stocks.append(brief)
        d30 = _pct(a, 30)
        if d30 is not None and not a.error:
            ranked.append((d30, name or a.stock_code, a))

    ranked.sort(reverse=True)
    watch: list[str] = []
    if ranked:
        top = ranked[0]
        bot = ranked[-1]
        watch.append(
            f"组合分化：30日最强 {top[1]} ({top[0]:+.1f}%)，最弱 {bot[1]} ({bot[0]:+.1f}%)"
        )
    weak_yday = [
        name_map.get(a.stock_code, a.stock_code)
        for a in analyses
        if (_pct(a, 1) or 0) <= -3 and not a.error
    ]
    strong_yday = [
        name_map.get(a.stock_code, a.stock_code)
        for a in analyses
        if (_pct(a, 1) or 0) >= 3 and not a.error
    ]
    if weak_yday:
        watch.append(f"昨日显著回调：{', '.join(weak_yday)} — 优先跟踪量能与支撑位")
    if strong_yday:
        watch.append(f"昨日强势：{', '.join(strong_yday)} — 关注是否延续或冲高回落")

    watch.append("开盘前：看板块/指数是否共振；持仓与指数背离时降低单日博弈仓位")
    watch.append("盘中：昨高、昨低、5日均线；尾盘异常放量留意次日惯性")

    overview = f"共 {len([a for a in analyses if not a.error])} 只可分析标的"
    if ranked:
        overview += f"；阶段强势集中在 {ranked[0][1]} 一带，短线留意分化与量能"

    return PortfolioDayStrategy(overview=overview, portfolio_watch=watch, stocks=stocks)


def format_day_strategy_text(plan: PortfolioDayStrategy) -> str:
    lines = [
        "",
        "=" * 60,
        "【下一交易日】操作策略与观察点（统计归纳，非投资建议）",
        "=" * 60,
        plan.overview,
        "",
        "▸ 组合观察",
    ]
    for w in plan.portfolio_watch:
        lines.append(f"  · {w}")
    for s in plan.stocks:
        label = f"{s.stock_code} {s.stock_name}".strip()
        lines.extend([
            "",
            f"▸ {label}",
            f"  趋势：{s.trend_label} | 统计倾向：{s.bias}",
            f"  策略：{s.stance}",
            "  观察点：",
        ])
        for p in s.watch_points:
            lines.append(f"    - {p}")
        for sl in s.strategy_lines:
            lines.append(f"  {sl}")
    lines.append("")
    return "\n".join(lines)
