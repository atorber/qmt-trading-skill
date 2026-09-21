"""当日交易操作评价：结合委托/成交、盈亏拆解与执行质量。"""

from __future__ import annotations

from dataclasses import dataclass, field

from orders_util import slippage_bps
from pnl_util import DailyPnlBreakdown
from review_thresholds import thr, thresholds_snapshot
from trading_fmt import order_side, pick
from trading_philosophy import (
    IntradayRange,
    PhilosophyCheckResult,
    SLIPPAGE_SEVERE_BP,
    SLIPPAGE_WARN_BP,
    TurnoverDay,
    apply_trading_philosophy,
    buy_position_in_range,
    classify_buy_timing,
    classify_sector,
    intraday_from_tick,
)


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
    buy_avg: float | None = None
    range_position: float | None = None
    intraday: IntradayRange | None = None
    no_trade_pnl: float | None = None
    op_alpha_pnl: float | None = None


@dataclass
class DailyOperationEval:
    total_daily_pnl: float | None = None
    total_asset: float | None = None
    cash: float | None = None
    order_count: int = 0
    cancelled_count: int = 0
    trade_count: int = 0
    no_trade_total_pnl: float | None = None
    op_alpha_total_pnl: float | None = None
    overall_score: float = 0.0
    overall_grade: str = ""
    summary_line: str = ""
    positives: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    execution_notes: list[str] = field(default_factory=list)
    discipline_tips: list[str] = field(default_factory=list)
    philosophy: PhilosophyCheckResult | None = None
    stocks: list[StockOpEval] = field(default_factory=list)
    eval_mode: str = "evidence"  # evidence | rules
    rule_tags: list[dict] = field(default_factory=list)


# 两市成交额：上证指数 + 深证市场（综指优先，深成指兜底）
_TURNOVER_SH_INDEX = "000001.SH"
_TURNOVER_SZ_INDEX = "399106.SZ"
_TURNOVER_SZ_FALLBACK = "399001.SZ"


def _tick_amount_yuan(tick: dict | None) -> float | None:
    if not isinstance(tick, dict):
        return None
    raw = tick.get("amount")
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _lookup_tick(tick_map: dict, code: str) -> dict | None:
    t = tick_map.get(code) or tick_map.get(code.upper()) or tick_map.get(code.lower())
    return t if isinstance(t, dict) else None


def market_turnover_yi_from_tick_map(tick_map: dict) -> float | None:
    """从指数 tick 的 amount（元）汇总两市成交额（亿元）：上证 + 深证。"""
    if not isinstance(tick_map, dict):
        return None
    sh_yuan = _tick_amount_yuan(_lookup_tick(tick_map, _TURNOVER_SH_INDEX))
    sz_yuan = _tick_amount_yuan(_lookup_tick(tick_map, _TURNOVER_SZ_INDEX))
    if sz_yuan is None:
        sz_yuan = _tick_amount_yuan(_lookup_tick(tick_map, _TURNOVER_SZ_FALLBACK))
    if sh_yuan is None or sz_yuan is None:
        return None
    return round((sh_yuan + sz_yuan) / 1e8, 2)


def fetch_market_turnover_history(
    client,
    days: int = 3,
) -> list[TurnoverDay]:
    """拉取近 N 个交易日两市成交额序列（亿元）。

    通过 get_full_tick 当日成交额 + 本地日缓存构建序列，复盘热路径不读历史 K 线。
    """
    from market_turnover_util import fetch_turnover_history

    return fetch_turnover_history(client, days)


def fetch_market_turnover_yi(client) -> float | None:
    """拉取当日两市成交额（亿元）。优先 indices，缺深市时补 full_tick。"""
    try:
        raw_idx = client.get_major_indices()
        if isinstance(raw_idx, dict):
            yi = market_turnover_yi_from_tick_map(raw_idx.get("data") or {})
            if yi is not None:
                return yi
    except Exception:
        pass
    try:
        snap = client.get_market_snapshot(
            [_TURNOVER_SH_INDEX, _TURNOVER_SZ_INDEX, _TURNOVER_SZ_FALLBACK]
        )
        return market_turnover_yi_from_tick_map(snap if isinstance(snap, dict) else {})
    except Exception:
        return None


def fetch_eval_market_context(
    client,
    stock_codes: list[str],
    turnover_days: int = 3,
) -> tuple[float | None, list[TurnoverDay], dict[str, float | None], float | None]:
    """拉取评价用上下文：当日成交额、近 N 日序列、近 3 日涨幅、指数均涨跌。"""
    from kline_util import cumulative_returns_pct, parse_daily_bars, records_to_list

    turnover_yi: float | None = None
    index_avg: float | None = None
    try:
        raw_idx = client.get_major_indices()
        if isinstance(raw_idx, dict):
            tick_map = raw_idx.get("data") or {}
            turnover_yi = market_turnover_yi_from_tick_map(tick_map)
            codes = raw_idx.get("indices") or []
            pcts: list[float] = []
            for code in codes:
                t = _lookup_tick(tick_map, code) or {}
                last = float(t.get("lastPrice") or t.get("lastClose") or 0)
                prev = float(t.get("lastClose") or t.get("preClose") or 0)
                if prev:
                    pcts.append((last - prev) / prev * 100)
            if pcts:
                index_avg = round(sum(pcts) / len(pcts), 2)
    except Exception:
        pass
    if turnover_yi is None:
        turnover_yi = fetch_market_turnover_yi(client)

    turnover_history = fetch_market_turnover_history(client, days=turnover_days)

    cum3: dict[str, float | None] = {}
    for code in stock_codes:
        if not code:
            continue
        try:
            raw = client.get_history_ex(
                stocks=[code],
                period="1d",
                count=6,
                dividend_type="front",
            )
            data = raw.get("data", raw) if isinstance(raw, dict) else {}
            recs = []
            if isinstance(data, dict):
                recs = data.get(code) or data.get(code.upper()) or []
            bars = parse_daily_bars(records_to_list(recs))
            cum = cumulative_returns_pct(bars, (3,))
            cum3[code] = cum.get(3)
        except Exception:
            cum3[code] = None
    return turnover_yi, turnover_history, cum3, index_avg


def _pct_chg(b: DailyPnlBreakdown) -> float | None:
    if b.last_price is None or b.pre_close is None or b.pre_close == 0:
        return None
    return round((b.last_price / b.pre_close - 1) * 100, 2)


def _no_trade_pnl(b: DailyPnlBreakdown) -> float | None:
    """假设当日不进行任何买卖，仅持有昨仓到收盘的盈亏。"""
    if b.last_price is None or b.pre_close is None:
        return None
    return round(b.yesterday_volume * (b.last_price - b.pre_close), 2)


def _classify_operation(
    b: DailyPnlBreakdown,
    pct: float | None,
    day: IntradayRange | None = None,
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
        label, note, _ = classify_buy_timing(
            t.buy_avg, day, pct_chg=pct
        )
        return label, note

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
        if bps is not None and abs(bps) >= SLIPPAGE_WARN_BP:
            sym = name_map.get(code, code)
            bad_slips.append(f"{sym} {side} {bps:+.1f}bp")
            if abs(bps) >= SLIPPAGE_SEVERE_BP:
                bad_slips[-1] += " [严重]"

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
    market_turnover_yi: float | None = None,
    turnover_history: list[TurnoverDay] | None = None,
    cumulative_3d_pct: dict[str, float | None] | None = None,
    index_avg_pct: float | None = None,
    tick_map: dict[str, dict] | None = None,
    eval_mode: str = "evidence",
) -> DailyOperationEval:
    """生成当日操作评价。

    eval_mode:
      - evidence（默认）：事实 + rule_tags + 算法参考分；模板叙事留给 Agent 专家评审
      - rules：保留旧版「做得好的/需改进/纪律提示」模板句
    """
    mode = (eval_mode or "evidence").strip().lower()
    if mode not in ("evidence", "rules"):
        mode = "evidence"

    result = DailyOperationEval(
        order_count=len(orders),
        cancelled_count=cancelled_count,
        trade_count=len(trades),
        eval_mode=mode,
    )

    if isinstance(asset, dict):
        result.total_asset = _to_float(
            pick(asset, "total_asset", "m_dTotalAsset")
        )
        result.cash = _to_float(pick(asset, "cash", "m_dCash"))

    total_pnl = 0.0
    baseline_pnl = 0.0
    has_pnl = False
    has_baseline = False
    for b in breakdowns:
        if b.daily_pnl is not None:
            total_pnl += b.daily_pnl
            has_pnl = True
        baseline = _no_trade_pnl(b)
        if baseline is not None:
            baseline_pnl += baseline
            has_baseline = True
    if has_pnl:
        result.total_daily_pnl = round(total_pnl, 2)
    if has_baseline:
        result.no_trade_total_pnl = round(baseline_pnl, 2)
    if has_pnl and has_baseline:
        result.op_alpha_total_pnl = round(total_pnl - baseline_pnl, 2)

    ticks = tick_map or {}
    for b in breakdowns:
        code = b.stock_code
        pct = _pct_chg(b)
        tick = ticks.get(code) or ticks.get(code.upper()) or {}
        day = intraday_from_tick(tick if isinstance(tick, dict) else None)
        label, watch = _classify_operation(b, pct, day)
        no_trade = _no_trade_pnl(b)
        alpha = (
            round((b.daily_pnl or 0.0) - no_trade, 2)
            if (b.daily_pnl is not None and no_trade is not None)
            else None
        )
        buy_avg = b.trade_summary.buy_avg
        range_pos = (
            buy_position_in_range(buy_avg, day) if buy_avg is not None else None
        )
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
                buy_avg=buy_avg,
                range_position=range_pos,
                intraday=day,
                no_trade_pnl=no_trade,
                op_alpha_pnl=alpha,
            )
        )

    result.stocks.sort(
        key=lambda s: (s.daily_pnl is None, -(s.daily_pnl or 0)),
    )

    alpha_pos = thr("op_alpha_positive_hint")
    alpha_neg = thr("op_alpha_improve_hint")
    pnl_large = thr("pnl_positive_large")
    pnl_mid = thr("pnl_positive_mid")

    if mode == "rules":
        for s in result.stocks:
            traded = s.buy_volume > 0 or s.sell_volume > 0
            if traded and s.op_alpha_pnl is not None and s.op_alpha_pnl > alpha_pos:
                result.positives.append(
                    f"{_sym(s)}：操作相对不操作多赚 {_fmt_pnl(s.op_alpha_pnl)}（{s.operation_label}）"
                )
            elif s.daily_pnl is not None and s.daily_pnl > pnl_large and s.sell_volume > s.buy_volume:
                result.positives.append(
                    f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}（卖{s.sell_volume}/买{s.buy_volume}）"
                )
            elif s.daily_pnl is not None and s.daily_pnl > pnl_mid and s.operation_label in (
                "顺势加仓",
                "低吸加仓",
            ):
                result.positives.append(
                    f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}，{s.operation_label}"
                )

        for s in result.stocks:
            traded = s.buy_volume > 0 or s.sell_volume > 0
            if not traded:
                if s.daily_pnl is not None and s.daily_pnl > pnl_large and (s.pct_chg or 0) >= 3:
                    result.positives.append(
                        f"{_sym(s)}：{_fmt_pnl(s.daily_pnl)}（{s.pct_chg:+.2f}%），持股浮盈未调仓"
                    )
                continue
            if s.op_alpha_pnl is not None and s.op_alpha_pnl < alpha_neg:
                result.improvements.append(
                    f"{_sym(s)}：操作相对不操作少赚/多亏 {_fmt_pnl(s.op_alpha_pnl)}，{s.operation_label} — {s.watch_note}"
                )
            elif s.daily_pnl is not None and s.daily_pnl < alpha_neg:
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
    score_large = thr("score_alpha_large")
    if result.op_alpha_total_pnl is not None:
        if result.op_alpha_total_pnl >= score_large:
            score += thr("score_alpha_large_bonus")
        elif result.op_alpha_total_pnl > 0:
            score += thr("score_alpha_pos_bonus")
        elif result.op_alpha_total_pnl <= -score_large:
            score += thr("score_alpha_large_penalty")
        else:
            score += thr("score_alpha_neg_penalty")
    elif result.total_daily_pnl is not None:
        if result.total_daily_pnl > 0:
            score += 1.0
        else:
            score -= 1.5

    neg_ops = sum(
        1
        for s in result.stocks
        if s.op_alpha_pnl is not None
        and s.op_alpha_pnl < 0
        and (s.buy_volume > 0 or s.sell_volume > 0)
    )
    if neg_ops >= 2:
        score -= 0.5
    if mode == "rules" and len(result.positives) >= 2:
        score += 0.5
    if any("滑点偏大" in n for n in result.execution_notes):
        score -= 0.5
    if cancelled_count >= 3:
        score -= 0.3

    buy_avg_by_code = {
        s.stock_code: s.buy_avg for s in result.stocks if s.buy_avg is not None
    }
    intraday_by_code = {
        s.stock_code: s.intraday
        for s in result.stocks
        if s.intraday is not None
    }
    result.philosophy = apply_trading_philosophy(
        stocks=result.stocks,
        name_map=name_map,
        total_asset=result.total_asset,
        cash=result.cash,
        order_count=result.order_count,
        cancelled_count=cancelled_count,
        market_turnover_yi=market_turnover_yi,
        turnover_history=turnover_history,
        cumulative_3d_pct=cumulative_3d_pct,
        index_avg_pct=index_avg_pct,
        execution_notes=result.execution_notes,
        buy_avg_by_code=buy_avg_by_code,
        intraday_by_code=intraday_by_code,
    )
    phil = result.philosophy
    if phil.violations:
        score -= min(1.5, 0.35 * len(phil.violations))
    if phil.aligned:
        score += min(0.8, 0.2 * len(phil.aligned))
    if phil.volume_zone and phil.volume_zone.label == "谨慎区" and any(
        s.buy_volume > s.sell_volume for s in result.stocks
    ):
        score -= 0.4

    score = max(1.0, min(10.0, round(score, 1)))
    result.overall_score = score
    result.overall_grade = _grade(score)

    if result.op_alpha_total_pnl is not None:
        if result.op_alpha_total_pnl >= 0:
            result.summary_line = (
                f"相对不操作基线，操作后多赚约 {_fmt_pnl(result.op_alpha_total_pnl)}，"
                f"主动交易以{'止盈减仓' if any('止盈' in s.operation_label for s in result.stocks) else '调仓'}为主"
            )
        else:
            result.summary_line = (
                f"相对不操作基线，操作后少赚/多亏约 {_fmt_pnl(result.op_alpha_total_pnl)}，"
                "宜复盘买卖节奏与仓位纪律"
            )
    elif result.total_daily_pnl is not None and result.total_daily_pnl >= 0:
        result.summary_line = (
            f"盈利日约 {_fmt_pnl(result.total_daily_pnl)}，"
            f"主动交易以{'止盈减仓' if any('止盈' in s.operation_label for s in result.stocks) else '调仓'}为主"
        )
    else:
        result.summary_line = "当日合计亏损，宜复盘买卖节奏与仓位纪律"

    result.rule_tags = build_rule_tags(result, cumulative_3d_pct or {})
    if mode == "rules":
        result.discipline_tips = _discipline_tips(result, phil)
    return result


def build_rule_tags(
    ev: DailyOperationEval,
    cumulative_3d_pct: dict[str, float | None] | None = None,
) -> list[dict]:
    """将规则命中降级为可解释标签（非最终评语）。"""
    tags: list[dict] = []
    cum3 = cumulative_3d_pct or {}
    phil = ev.philosophy

    if phil and phil.volume_zone:
        tags.append(
            {
                "tag": "volume_zone",
                "label": phil.volume_zone.label,
                "detail": phil.volume_zone.guidance,
            }
        )
    if phil and phil.market_heat_label:
        tags.append(
            {
                "tag": "market_heat",
                "label": phil.market_heat_label,
                "detail": phil.market_heat_summary or "",
            }
        )

    for s in ev.stocks:
        code = s.stock_code
        traded = s.buy_volume > 0 or s.sell_volume > 0
        sector = classify_sector(code, s.stock_name)
        base = {
            "stock_code": code,
            "stock_name": s.stock_name,
            "sector": sector,
            "operation_label": s.operation_label,
        }
        if s.operation_label == "追涨加仓":
            tags.append({**base, "tag": "chase_buy_candidate", "detail": s.watch_note})
        if s.operation_label == "低吸加仓":
            tags.append({**base, "tag": "dip_buy_candidate", "detail": s.watch_note})
        if s.operation_label == "逆势加仓":
            tags.append({**base, "tag": "counter_trend_buy", "detail": s.watch_note})
        if s.operation_label == "大涨止盈":
            tags.append({**base, "tag": "take_profit_sell", "detail": s.watch_note})
        if (
            s.pct_chg is not None
            and s.pct_chg >= thr("take_profit_1d_pct")
            and s.sell_volume == 0
            and s.buy_volume == 0
        ):
            tags.append(
                {
                    **base,
                    "tag": "take_profit_gap_1d",
                    "detail": f"单日 {s.pct_chg:+.1f}% 未卖出",
                }
            )
        c3 = cum3.get(code)
        if (
            c3 is not None
            and c3 >= thr("take_profit_3d_pct")
            and s.sell_volume == 0
            and s.buy_volume == 0
        ):
            tags.append(
                {
                    **base,
                    "tag": "take_profit_gap_3d",
                    "detail": f"近3日累计约 +{c3:.1f}% 未分步止盈",
                }
            )
        if traded and s.op_alpha_pnl is not None and s.op_alpha_pnl < thr("op_alpha_improve_hint"):
            tags.append(
                {
                    **base,
                    "tag": "op_alpha_negative",
                    "detail": f"操作增量 {_fmt_pnl(s.op_alpha_pnl)}",
                    "op_alpha_pnl": s.op_alpha_pnl,
                }
            )
        if traded and s.op_alpha_pnl is not None and s.op_alpha_pnl > thr("op_alpha_positive_hint"):
            tags.append(
                {
                    **base,
                    "tag": "op_alpha_positive",
                    "detail": f"操作增量 {_fmt_pnl(s.op_alpha_pnl)}",
                    "op_alpha_pnl": s.op_alpha_pnl,
                }
            )
        if s.range_position is not None:
            tags.append(
                {
                    **base,
                    "tag": "buy_range_position",
                    "detail": f"买入均价振幅位置 {s.range_position:.2f}",
                    "range_position": s.range_position,
                }
            )

    if phil:
        for v in phil.violations:
            tags.append({"tag": "rule_violation", "detail": v})
        for a in phil.aligned:
            tags.append({"tag": "rule_aligned", "detail": a})

    for note in ev.execution_notes:
        if "滑点" in note:
            tags.append({"tag": "slippage_warn", "detail": note})
        if "撤" in note:
            tags.append({"tag": "cancel_busy", "detail": note})

    holding_n = len(ev.stocks)
    traded_n = sum(1 for s in ev.stocks if s.buy_volume > 0 or s.sell_volume > 0)
    if holding_n > int(thr("max_holdings_focus")):
        tags.append(
            {
                "tag": "holdings_scattered",
                "detail": f"持仓 {holding_n} 只",
            }
        )
    if traded_n > int(thr("max_active_traded_today")):
        tags.append(
            {
                "tag": "trade_scattered",
                "detail": f"当日成交标的 {traded_n} 只",
            }
        )
    return tags


def build_evidence_pack(
    *,
    trade_date: str,
    account_id: str | None,
    health,
    account_status,
    asset: dict | None,
    orders: list[dict],
    trades: list[dict],
    name_map: dict[str, str],
    filled: int,
    cancelled: int,
    op_eval: DailyOperationEval,
    combined: bool = False,
) -> dict:
    """稳定契约：供 Agent 三角色专家评审（禁止编造数字，须引用本包）。"""
    phil = op_eval.philosophy
    cash_pct = None
    if op_eval.cash is not None and op_eval.total_asset and op_eval.total_asset > 0:
        cash_pct = round(op_eval.cash / op_eval.total_asset * 100, 2)

    return {
        "schema_version": 1,
        "meta": {
            "trade_date": trade_date,
            "account_id": account_id,
            "combined": combined,
            "health": health,
            "account_status": account_status,
            "eval_mode": op_eval.eval_mode,
        },
        "execution": {
            "order_count": len(orders),
            "filled_count": filled,
            "cancelled_count": cancelled,
            "trade_count": len(trades),
            "orders": orders,
            "trades": trades,
            "execution_notes": op_eval.execution_notes,
        },
        "pnl": {
            "total_daily_pnl": op_eval.total_daily_pnl,
            "no_trade_total_pnl": op_eval.no_trade_total_pnl,
            "op_alpha_total_pnl": op_eval.op_alpha_total_pnl,
            "total_asset": op_eval.total_asset,
            "cash": op_eval.cash,
            "cash_pct": cash_pct,
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
                    "buy_avg": s.buy_avg,
                    "range_position": s.range_position,
                    "no_trade_pnl": s.no_trade_pnl,
                    "op_alpha_pnl": s.op_alpha_pnl,
                    "sector": classify_sector(s.stock_code, s.stock_name),
                }
                for s in op_eval.stocks
            ],
        },
        "market": {
            "market_turnover_yi": phil.market_turnover_yi if phil else None,
            "volume_zone": phil.volume_zone.label if phil and phil.volume_zone else None,
            "volume_note": phil.volume_note if phil else "",
            "market_heat_label": phil.market_heat_label if phil else "",
            "market_heat_summary": phil.market_heat_summary if phil else "",
            "sector_summary": phil.sector_summary if phil else "",
            "turnover_history": [
                {
                    "trade_date": d.trade_date,
                    "turnover_yi": d.turnover_yi,
                    "zone_label": d.zone_label,
                }
                for d in (phil.turnover_history if phil else [])
            ],
        },
        "rule_tags": op_eval.rule_tags,
        "score_hints": {
            "algorithmic_only": True,
            "overall_score": op_eval.overall_score,
            "overall_grade": op_eval.overall_grade,
            "summary_line": op_eval.summary_line,
            "note": "展示以专家综合裁决为准；本分为规则参考分",
        },
        "thresholds": thresholds_snapshot(),
        "stock_names": name_map,
        "disclaimer": "统计归纳与规则标签，非投资建议；专家评语须引用本证据包字段，禁止编造数字。",
    }


def _discipline_tips(
    ev: DailyOperationEval,
    phil: PhilosophyCheckResult | None = None,
) -> list[str]:
    tips: list[str] = []
    if phil and phil.market_heat_summary:
        tips.append(f"量能：{phil.market_heat_summary}")
    elif phil and phil.volume_note:
        tips.append(f"量能：{phil.volume_note}")
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


def _philosophy_to_dict(p: PhilosophyCheckResult | None) -> dict | None:
    if p is None:
        return None
    return {
        "market_turnover_yi": p.market_turnover_yi,
        "market_heat_label": p.market_heat_label,
        "market_heat_summary": p.market_heat_summary,
        "turnover_history": [
            {
                "trade_date": d.trade_date,
                "turnover_yi": d.turnover_yi,
                "zone_label": d.zone_label,
            }
            for d in p.turnover_history
        ],
        "volume_zone": p.volume_zone.label if p.volume_zone else None,
        "volume_note": p.volume_note,
        "sector_summary": p.sector_summary,
        "aligned": p.aligned,
        "violations": p.violations,
        "discipline": p.discipline,
    }


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
        "【当日客观复盘】（事实 + 规则标签；专家评语见 Agent 三角色规程）"
        if ev.eval_mode == "evidence"
        else "【当日操作评价】（统计归纳，非投资建议；对照交易观）",
        "=" * 60,
    ]
    if ev.eval_mode == "evidence":
        lines.append(
            f"算法参考分 {ev.overall_score}/10（{ev.overall_grade}，algorithmic_only） · {ev.summary_line}"
        )
    else:
        lines.append(f"总评 {ev.overall_score}/10（{ev.overall_grade}） · {ev.summary_line}")
    if ev.total_daily_pnl is not None:
        lines.append(f"当日盈亏合计（估算）：{_fmt_pnl(ev.total_daily_pnl)}")
    if (
        ev.no_trade_total_pnl is not None
        and ev.total_daily_pnl is not None
        and ev.op_alpha_total_pnl is not None
    ):
        lines.append(
            "基线对比（不操作）："
            f"不操作约 {_fmt_pnl(ev.no_trade_total_pnl)}；"
            f"操作后约 {_fmt_pnl(ev.total_daily_pnl)}；"
            f"操作增量 {_fmt_pnl(ev.op_alpha_total_pnl)}"
        )
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.philosophy:
        p = ev.philosophy
        lines.append("\n▸ 市场与板块（客观）")
        if p.sector_summary:
            lines.append(f"  · {p.sector_summary}")
        if p.volume_zone:
            lines.append(f"  · 量能分区：{p.volume_zone.label} — {p.volume_zone.guidance}")
        elif p.volume_note:
            lines.append(f"  · {p.volume_note}")
        if p.market_heat_summary:
            label = f"【{p.market_heat_label}】" if p.market_heat_label else ""
            lines.append(f"  · 近3日市场热度{label}：{p.market_heat_summary}")
        if ev.eval_mode == "rules":
            for a in p.aligned:
                lines.append(f"  · ✓ {a}")

    if ev.eval_mode == "evidence" and ev.rule_tags:
        lines.append("\n▸ 规则标签（供专家解释，非定罪）")
        for t in ev.rule_tags[:40]:
            tag = t.get("tag", "")
            detail = t.get("detail", "")
            code = t.get("stock_code", "")
            prefix = f"{code} " if code else ""
            lines.append(f"  · [{tag}] {prefix}{detail}".rstrip())
        if len(ev.rule_tags) > 40:
            lines.append(f"  · …共 {len(ev.rule_tags)} 条，完整见 evidence.json")

    if ev.eval_mode == "rules":
        if ev.positives:
            lines.append("\n▸ 做得好的")
            for p in ev.positives:
                lines.append(f"  · {p}")

        if ev.philosophy and ev.philosophy.violations:
            lines.append("\n▸ 戒律检查（需改进）")
            for v in ev.philosophy.violations:
                lines.append(f"  · {v}")

        if ev.improvements:
            lines.append("\n▸ 需改进")
            for p in ev.improvements:
                lines.append(f"  · {p}")

    if ev.execution_notes:
        lines.append("\n▸ 执行质量")
        for p in ev.execution_notes:
            lines.append(f"  · {p}")

    if ev.eval_mode == "rules" and ev.philosophy and ev.philosophy.discipline:
        lines.append("\n▸ 纪律提示（交易观）")
        for d in ev.philosophy.discipline:
            lines.append(f"  · {d}")

    if ev.stocks:
        lines.append("\n▸ 分标的操作")
        for s in ev.stocks:
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            pct_s = f"{s.pct_chg:+.2f}%" if s.pct_chg is not None else "—"
            lines.append(
                f"  · {_sym(s)}：{pnl_s}（{pct_s}）| {s.operation_label} | "
                f"买{s.buy_volume}/卖{s.sell_volume} | 仓 {s.yesterday_volume}→{s.current_volume}"
            )

    if ev.eval_mode == "rules" and ev.discipline_tips:
        lines.append("\n▸ 明日纪律提示")
        for t in ev.discipline_tips:
            lines.append(f"  · {t}")
    elif ev.eval_mode == "evidence":
        lines.append(
            "\n▸ 下一步：按 references/expert-review-protocol.md "
            "用投顾/基金经理/交易员三角色基于 evidence.json 写专家复盘"
        )
    lines.append("")
    return "\n".join(lines)


def operation_eval_to_dict(ev: DailyOperationEval) -> dict:
    return {
        "eval_mode": ev.eval_mode,
        "overall_score": ev.overall_score,
        "overall_grade": ev.overall_grade,
        "summary_line": ev.summary_line,
        "score_hints": {
            "algorithmic_only": True,
            "overall_score": ev.overall_score,
            "overall_grade": ev.overall_grade,
        },
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
        "rule_tags": ev.rule_tags,
        "philosophy": _philosophy_to_dict(ev.philosophy),
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
                "buy_avg": s.buy_avg,
                "range_position": s.range_position,
                "no_trade_pnl": s.no_trade_pnl,
                "op_alpha_pnl": s.op_alpha_pnl,
            }
            for s in ev.stocks
        ],
        "no_trade_total_pnl": ev.no_trade_total_pnl,
        "op_alpha_total_pnl": ev.op_alpha_total_pnl,
    }
