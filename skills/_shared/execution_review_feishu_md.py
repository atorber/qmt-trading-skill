"""当日复盘 → 飞书 Markdown 全文导出（客观章节 + 专家占位）。"""

from __future__ import annotations

from execution_review_eval import DailyOperationEval
from feishu_doc import DOC_TYPES, format_title
from orders_util import build_stock_trade_summary, slippage_bps
from stock_names import label_stock
from trading_fmt import format_order_time, order_status_label, order_type_label, pick


def _sym(s) -> str:
    return f"{s.stock_code} {s.stock_name}".strip()


def _fmt_pnl(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f} 元"


def _orders_table_md(orders: list[dict], name_map: dict[str, str]) -> list[str]:
    lines = [f"## 二、当日委托（{len(orders)}）", ""]
    if not orders:
        lines.append("（无）")
        return lines
    lines.append("| 时间 | 标的 | 方向 | 委托 | 成交 | 状态 | 滑点 |")
    lines.append("|------|------|------|------|------|------|------|")
    for o in sorted(orders, key=lambda x: pick(x, "order_time", "m_nOrderTime", default=0)):
        code = pick(o, "stock_code", "m_strStockCode", default="?")
        sym = label_stock(code, name_map)
        side = order_type_label(pick(o, "order_type", "m_nOrderType"))
        vol = int(pick(o, "order_volume", "m_nOrderVolume", default=0) or 0)
        traded = int(pick(o, "traded_volume", "m_nTradedVolume", default=0) or 0)
        price = float(pick(o, "price", "m_dPrice", default=0) or 0)
        tprice = float(pick(o, "traded_price", "m_dTradedPrice", default=0) or 0)
        status = order_status_label(pick(o, "order_status", "m_nOrderStatus"))
        t = format_order_time(pick(o, "order_time", "m_nOrderTime"))
        slip_s = "—"
        if traded > 0 and price > 0 and tprice > 0:
            bps = slippage_bps(price, tprice, side)
            if bps is not None:
                slip_s = f"{bps:+.1f}bp"
        lines.append(
            f"| {t} | {sym} | {side} | {vol}@{price:.2f} | "
            f"{traded}@{tprice:.2f} | {status} | {slip_s} |"
        )
    return lines


def _trades_md(trades: list[dict], name_map: dict[str, str]) -> list[str]:
    lines = [f"## 三、当日成交（{len(trades)}）", ""]
    if not trades:
        lines.append("（无）")
        return lines
    for t in sorted(
        trades,
        key=lambda x: pick(x, "traded_time", "m_nTradedTime", "trade_time", default=0),
    ):
        code = pick(t, "stock_code", "m_strStockCode", default="?")
        sym = label_stock(code, name_map)
        vol = int(pick(t, "traded_volume", "m_nTradedVolume", "trade_volume", default=0) or 0)
        price = float(pick(t, "traded_price", "m_dTradedPrice", "trade_price", default=0) or 0)
        tm = format_order_time(pick(t, "traded_time", "m_nTradedTime", "trade_time"))
        lines.append(f"- {tm} **{sym}** {vol}@{price:.2f}")
    return lines


def _stock_summary_md(
    orders: list[dict],
    trades: list[dict],
    name_map: dict[str, str],
) -> list[str]:
    summary = build_stock_trade_summary(orders, trades)
    lines = ["## 四、按标的成交汇总", ""]
    if not summary:
        lines.append("（无）")
        return lines
    lines.append("| 标的 | 买入 | 卖出 | 净变动 |")
    lines.append("|------|------|------|--------|")
    for code in sorted(summary):
        b = summary[code].get("买入", 0)
        s = summary[code].get("卖出", 0)
        sym = label_stock(code, name_map)
        lines.append(f"| {sym} | {b} | {s} | {b - s} |")
    return lines


def format_objective_pnl_md(ev: DailyOperationEval) -> str:
    """第五节：客观盈亏与不操作基线（不含主观定罪）。"""
    lines = [
        "## 五、盈亏与不操作基线（客观）",
        "",
        "> 事实数据；专家评语见第七节。非投资建议。",
        "",
    ]
    if ev.total_daily_pnl is not None:
        lines.append(f"**当日盈亏合计（估算）**：{_fmt_pnl(ev.total_daily_pnl)}")
    if (
        ev.no_trade_total_pnl is not None
        and ev.total_daily_pnl is not None
        and ev.op_alpha_total_pnl is not None
    ):
        lines.append(
            f"**基线对比**：不操作约 {_fmt_pnl(ev.no_trade_total_pnl)}；"
            f"操作后约 {_fmt_pnl(ev.total_daily_pnl)}；"
            f"操作增量 {_fmt_pnl(ev.op_alpha_total_pnl)}"
        )
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.stocks and any(s.no_trade_pnl is not None for s in ev.stocks):
        lines.extend(
            [
                "",
                "### 不操作少赚/多亏明细",
                "",
                "> 不操作基线 = 昨仓持有到收盘；操作增量 = 实际操作盈亏 − 不操作基线。",
                "",
                "| 标的 | 操作 | 不操作基线 | 实际操作 | 操作增量 |",
                "|------|------|-----------|---------|---------|",
            ]
        )
        ranked = sorted(
            ev.stocks,
            key=lambda s: (
                s.op_alpha_pnl is None,
                s.op_alpha_pnl if s.op_alpha_pnl is not None else 0,
            ),
        )
        for s in ranked:
            if s.no_trade_pnl is None and s.daily_pnl is None:
                continue
            base_s = _fmt_pnl(s.no_trade_pnl) if s.no_trade_pnl is not None else "—"
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            alpha_s = _fmt_pnl(s.op_alpha_pnl) if s.op_alpha_pnl is not None else "—"
            lines.append(
                f"| {_sym(s)} | {s.operation_label} | {base_s} | {pnl_s} | {alpha_s} |"
            )

    if ev.philosophy:
        p = ev.philosophy
        lines.extend(["", "### 市场与板块", ""])
        if p.sector_summary:
            lines.append(f"- {p.sector_summary}")
        if p.volume_zone:
            lines.append(f"- 量能分区：**{p.volume_zone.label}** — {p.volume_zone.guidance}")
        elif p.volume_note:
            lines.append(f"- {p.volume_note}")
        if p.market_heat_summary:
            heat = f"**{p.market_heat_label}** — " if p.market_heat_label else ""
            lines.append(f"- 近3日市场热度：{heat}{p.market_heat_summary}")

    if ev.execution_notes:
        lines.extend(["", "### 执行质量（客观）", ""])
        for p in ev.execution_notes:
            lines.append(f"- {p}")

    if ev.stocks:
        lines.extend(["", "### 分标的操作", ""])
        lines.append("| 标的 | 当日盈亏 | 涨跌 | 操作 | 买/卖 | 仓位变化 |")
        lines.append("|------|----------|------|------|-------|----------|")
        for s in ev.stocks:
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            pct_s = f"{s.pct_chg:+.2f}%" if s.pct_chg is not None else "—"
            lines.append(
                f"| {_sym(s)} | {pnl_s} | {pct_s} | {s.operation_label} | "
                f"买{s.buy_volume}/卖{s.sell_volume} | "
                f"{s.yesterday_volume}→{s.current_volume} |"
            )

    return "\n".join(lines)


def format_rule_tags_md(ev: DailyOperationEval) -> str:
    """第六节：规则标签 + 算法参考分。"""
    lines = [
        "## 六、规则标签与算法参考分",
        "",
        f"**算法参考分** {ev.overall_score}/10（{ev.overall_grade}，`algorithmic_only`）",
        "",
        f"> {ev.summary_line}",
        "",
        "展示以第七节专家综合裁决为准；下列标签供专家解释，**非定罪**。",
        "",
    ]
    if not ev.rule_tags:
        lines.append("（无规则标签）")
        return "\n".join(lines)

    lines.append("| 标签 | 标的 | 说明 |")
    lines.append("|------|------|------|")
    for t in ev.rule_tags:
        tag = t.get("tag", "")
        code = t.get("stock_code", "") or "—"
        name = t.get("stock_name", "")
        sym = f"{code} {name}".strip() if code != "—" else "—"
        detail = (t.get("detail") or "").replace("|", "/")
        lines.append(f"| `{tag}` | {sym} | {detail} |")
    return "\n".join(lines)


def format_expert_placeholder_md() -> str:
    """第七节占位：由 Agent 按 expert-review-protocol 追加/覆盖。"""
    return "\n".join(
        [
            "## 七、专家评审",
            "",
            "> **待 Agent 填写**：读取 `reports/daily_eval_evidence.json`（或 combined 对应文件），",
            "> 按 `skills/qmt-bridge-execution-review/references/expert-review-protocol.md`",
            "> 输出投顾 / 基金经理 / 交易员三角色评审 + 综合裁决。",
            "> **禁止编造** evidence 中不存在的金额与增量；可将完整专家报告写入",
            "> `reports/feishu_daily_eval_expert.md` 后与本节合并再同步飞书。",
            "",
            "### 7.1 投顾视角",
            "",
            "（待填写）",
            "",
            "### 7.2 基金经理视角",
            "",
            "（待填写）",
            "",
            "### 7.3 交易员视角",
            "",
            "（待填写）",
            "",
            "### 7.4 综合裁决",
            "",
            "- **共识**：",
            "- **分歧**：",
            "- **综合结论**：",
            "- **明日纪律**（1～3 条）：",
            "",
        ]
    )


def format_operation_evaluation_md(ev: DailyOperationEval) -> str:
    """兼容入口：evidence 模式用五～七节；rules 模式保留旧版单节评价。"""
    if ev.eval_mode == "evidence":
        return "\n\n".join(
            [
                format_objective_pnl_md(ev),
                format_rule_tags_md(ev),
                format_expert_placeholder_md(),
            ]
        )

    lines = [
        "## 五、当日操作评价",
        "",
        "> 统计归纳，非投资建议；对照交易观（追涨/低吸按买入均价判断）。`--eval-mode=rules`",
        "",
        f"**总评** {ev.overall_score}/10（{ev.overall_grade}） · {ev.summary_line}",
    ]
    if ev.total_daily_pnl is not None:
        lines.append(f"**当日盈亏合计（估算）**：{_fmt_pnl(ev.total_daily_pnl)}")
    if (
        ev.no_trade_total_pnl is not None
        and ev.total_daily_pnl is not None
        and ev.op_alpha_total_pnl is not None
    ):
        lines.append(
            f"**基线对比**：不操作约 {_fmt_pnl(ev.no_trade_total_pnl)}；"
            f"操作后约 {_fmt_pnl(ev.total_daily_pnl)}；"
            f"操作增量 {_fmt_pnl(ev.op_alpha_total_pnl)}"
        )
    lines.append(
        f"委托 {ev.order_count} 笔 · 已撤 {ev.cancelled_count} · 成交 {ev.trade_count} 条"
    )

    if ev.stocks and any(s.no_trade_pnl is not None for s in ev.stocks):
        lines.extend(
            [
                "",
                "### 不操作少赚/多亏明细",
                "",
                "| 标的 | 操作 | 不操作基线 | 实际操作 | 操作增量 |",
                "|------|------|-----------|---------|---------|",
            ]
        )
        ranked = sorted(
            ev.stocks,
            key=lambda s: (
                s.op_alpha_pnl is None,
                s.op_alpha_pnl if s.op_alpha_pnl is not None else 0,
            ),
        )
        for s in ranked:
            if s.no_trade_pnl is None and s.daily_pnl is None:
                continue
            base_s = _fmt_pnl(s.no_trade_pnl) if s.no_trade_pnl is not None else "—"
            pnl_s = _fmt_pnl(s.daily_pnl) if s.daily_pnl is not None else "—"
            alpha_s = _fmt_pnl(s.op_alpha_pnl) if s.op_alpha_pnl is not None else "—"
            lines.append(
                f"| {_sym(s)} | {s.operation_label} | {base_s} | {pnl_s} | {alpha_s} |"
            )

    if ev.philosophy:
        p = ev.philosophy
        lines.extend(["", "### 交易观对照", ""])
        if p.sector_summary:
            lines.append(f"- {p.sector_summary}")
        if p.volume_zone:
            lines.append(f"- 量能分区：**{p.volume_zone.label}** — {p.volume_zone.guidance}")
        for a in p.aligned:
            lines.append(f"- ✓ {a}")

    if ev.positives:
        lines.extend(["", "### 做得好的", ""])
        for p in ev.positives:
            lines.append(f"- {p}")

    if ev.philosophy and ev.philosophy.violations:
        lines.extend(["", "### 戒律检查（需改进）", ""])
        for v in ev.philosophy.violations:
            lines.append(f"- {v}")

    if ev.improvements:
        lines.extend(["", "### 需改进", ""])
        for p in ev.improvements:
            lines.append(f"- {p}")

    if ev.execution_notes:
        lines.extend(["", "### 执行质量", ""])
        for p in ev.execution_notes:
            lines.append(f"- {p}")

    if ev.discipline_tips:
        lines.extend(["", "### 明日纪律提示", ""])
        for t in ev.discipline_tips:
            lines.append(f"- {t}")

    return "\n".join(lines)


def build_daily_eval_feishu_markdown(
    *,
    trade_date: str,
    synced_at: str,
    account_id: str | None,
    health: dict | str,
    account_status,
    orders: list[dict],
    trades: list[dict],
    name_map: dict[str, str],
    filled: int,
    cancelled: int,
    op_eval: DailyOperationEval | None,
    include_trades: bool = True,
    include_summary: bool = True,
    evidence_path: str | None = None,
) -> str:
    """生成飞书复盘 Markdown 全文。"""
    spec = DOC_TYPES["daily-eval"]
    title = format_title(
        spec.title_prefix,
        trade_date=trade_date,
        synced_at=synced_at,
    )
    health_s = health.get("status", health) if isinstance(health, dict) else str(health)

    parts: list[str] = [
        f"# {title}",
        "",
        f"**交易日**：{trade_date}  ",
        f"**同步时间**：{synced_at}  ",
        f"**账户**：{account_id or '默认'} | health: {health_s}",
        "",
        "---",
        "",
        "## 一、统计概览",
        "",
        "| 项目 | 数值 |",
        "|------|------|",
        f"| 委托 | {len(orders)} 笔 |",
        f"| 有成交 | {filled} 笔 |",
        f"| 已撤 | {cancelled} 笔 |",
        f"| 成交记录 | {len(trades)} 条 |",
    ]
    if op_eval and op_eval.total_daily_pnl is not None:
        parts.append(f"| **当日盈亏（估算）** | **{_fmt_pnl(op_eval.total_daily_pnl)}** |")
        parts.append(
            f"| **算法参考分** | **{op_eval.overall_score}/10（{op_eval.overall_grade}）** |"
        )
    if evidence_path:
        parts.append(f"| 证据包 | `{evidence_path}` |")

    parts.extend(["", "---", ""])
    parts.extend(_orders_table_md(orders, name_map))
    parts.append("")

    if include_trades:
        parts.extend(_trades_md(trades, name_map))
        parts.append("")

    if include_summary:
        parts.extend(_stock_summary_md(orders, trades, name_map))
        parts.append("")

    if op_eval is not None:
        parts.append(format_operation_evaluation_md(op_eval))
        parts.append("")

    parts.extend(
        [
            "---",
            "",
            "*客观章节由 `daily_trade_report.py --feishu-md` 生成；"
            "第七节专家评审由 Agent 按 expert-review-protocol 基于 evidence.json 填写。*",
        ]
    )
    return "\n".join(parts)
