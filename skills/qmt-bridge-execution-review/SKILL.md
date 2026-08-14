---
name: qmt-bridge-execution-review
description: >-
  通过 QMT Bridge 生成当日交易复盘：委托、成交、滑点、按标的汇总，
  并结合当日盈亏输出操作评价（对照**交易观**：量能分区、板块聚焦、分步止盈/低吸不追涨、戒律检查）。
  支持**不操作基线对比**（昨仓持有到收盘 vs 实际操作，输出操作增量/少赚多亏明细）。
  在用户提到今日成交、交易复盘、今日操作评估、执行质量、交易观、不操作少赚多亏时使用。只读。
---

# QMT Trading Skill · 交易复盘

> **实现状态**：✅ `daily_trade_report.py` 可用（见 [ROADMAP.md](../ROADMAP.md)）

## 目标

闭合「计划—执行—复盘」中的**复盘**环节：

1. 汇总当日委托与成交，评估滑点与撤单
2. 按标的汇总买卖量
3. **当日操作评价**：结合盈亏拆解与 [交易观标准](references/trading-philosophy.md)，归纳止盈/加仓/逆势、量能与戒律检查
4. **不操作基线对比**：估算「昨仓不动」盈亏，与实际操作对比得出**操作增量**（总评核心依据）

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_trade_report.py` | 单账户：orders + trades + 操作评价；`--json`；`--feishu-md` → `reports/feishu_daily_eval.md` |
| `scripts/combined_trade_report.py` | **全账户综合（推荐）**：合并普通户+信用户持仓与成交，不区分账户；`--feishu-md` → `reports/feishu_combined_daily_eval.md` |

```bash
# 单账户
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md

# 全账户综合（普通户 + 信用户，.env 配置双账户时）
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --json --api-key KEY
```

| 参数 | 说明 |
|------|------|
| `--json` | JSON（含 `operation_evaluation`，每标的有 `no_trade_pnl` / `op_alpha_pnl`） |
| `--feishu-md [PATH]` | 导出飞书 Markdown 全文（单账户默认 `reports/feishu_daily_eval.md`；综合默认 `reports/feishu_combined_daily_eval.md`） |
| `--no-trades` | 跳过成交列表 |
| `--no-summary` | 跳过按标的汇总 |
| `--no-eval` | 不输出操作评价 |
| `--market-turnover-yi` | 两市成交额（亿元）；未传时自动从 Bridge 指数 tick 拉取 |
| `--no-philosophy-fetch` | 不拉近3日涨幅；仍会自动拉两市成交额与指数涨跌 |

## 提示词示例（可复制）

| 场景 | 提示词 |
|------|--------|
| **复盘+评价（推荐）** | `生成今日交易复盘并做当日操作评价` |
| | `今日操作评估：得失、执行质量、明日纪律` |
| **全账户综合** | `普通户+信用户综合复盘` |
| **基线对比** | `列一下不操作少赚/多亏的明细` |
| 执行质量 | `汇总今天委托和成交，看看滑点和撤单` |
| 对照盈亏 | `结合当日盈亏评价今天买卖是否合理` |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/orders` | 当日委托 |
| GET | `/api/trading/trades` | 当日成交 |
| GET | `/api/trading/positions` | 持仓（评价用） |
| GET | `/api/trading/asset` | 资金（评价用） |
| GET | `/api/market/full_tick` | 现价/昨收（盈亏估算） |

## 操作规程

1. `health` + `account_status` 确认服务与交易通道
2. 拉 `orders`、`trades`、`positions`、`asset`
3. 输出委托表、成交列表、按标的汇总
4. 计算当日盈亏拆解，生成 **【当日操作评价】**（`--no-eval` 可关）
5. **只输出报告，不下单**

## 操作评价说明

评价依据见 **[references/trading-philosophy.md](references/trading-philosophy.md)**，实现见 `_shared/trading_philosophy.py` + `execution_review_eval.py`，飞书 Markdown 见 `execution_review_feishu_md.py`。

- **分标的**：操作类型（大涨止盈/逆势加仓/顺势加仓等）、当日盈亏、仓位变化
- **不操作基线对比**（`--feishu-md` 第五节含明细表）：
  - **不操作基线** = `昨仓股数 × (收盘价 − 昨收)`（假设当日零买卖）
  - **操作增量** = 实际操作盈亏 − 不操作基线（负值 = 少赚/多亏；正值 = 操作优于躺平）
  - 终端与 JSON：`no_trade_total_pnl`、`op_alpha_total_pnl`；分标的 `no_trade_pnl`、`op_alpha_pnl`
  - **总评 1～10 分**以操作增量为主（±5000 元档加减分）；基线不可得时退化为当日盈亏
  - 「需改进」中对主动交易且增量 &lt; -2000 元标为「操作相对不操作少赚/多亏」
- **交易观对照**：四板块分布、量能分区、符合顺势/止盈的亮点
- **戒律检查**：追涨、谨慎区重仓买、近3日/单日大涨未止盈、滑点与持仓过散等
- **总评**：1～10 分 + 做得好的 / 需改进 / 执行质量 / 纪律提示
- 统计归纳，**非投资建议**

### 不操作基线对比（解读要点）

| 现象 | 含义 |
|------|------|
| 当日亏损大、操作增量为正 | 操作反而**少亏**（如日内高抛低吸对冲下跌） |
| 当日盈利、操作增量为负 | 操作**少赚**（如过早卖出或追涨加仓拖累） |
| 新建仓标的 | 不操作基线多为 0，增量≈当日盈亏 |
| 持股未动 | 增量恒为 0 |

Agent 回答「少赚/多亏明细」时：**优先** `--json` 或 `--feishu-md` 产物中的 `op_alpha_pnl` 字段，**禁止**手算或臆造。

### 量能参数

复盘脚本支持传入当日两市成交额（亿元）：

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY --market-turnover-yi 12500
```

两市成交额默认自动拉取（上证 `000001.SH` + 深证 `399106.SZ`，缺则用 `399001.SZ` 的 tick `amount` 汇总）；可用 `--market-turnover-yi` 覆盖。**近 3 日市场热度**由 `get_full_tick` + `reports/market_turnover_daily.json` 缓存汇总（实现见 `_shared/market_turnover_util.py`）；历史缺口见 [qmt-bridge-kline-backfill](../qmt-bridge-kline-backfill/SKILL.md)。近 3 日个股涨幅可用 `--no-philosophy-fetch` 关闭（不影响量能序列拉取）。

## 安全

- 只读；需 `X-API-Key` 的交易查询端点

## 报告示例（文档）

脱敏后的完整章节结构见 **[docs/examples/daily-eval-report.md](../../docs/examples/daily-eval-report.md)**（MkDocs「示例 → 每日复盘报告」）。

## 发布到飞书云文档

同步飞书：**必须先** `--feishu-md` 生成 Markdown（单账户 `reports/feishu_daily_eval.md`；**双账户综合** `reports/feishu_combined_daily_eval.md`），再用 **[qmt-bridge-feishu-doc](../qmt-bridge-feishu-doc/SKILL.md)** + **lark-doc** / **lark-wiki** 上传（禁止 Agent 手写正文）。工作流见 `qmt-bridge-feishu-doc/references/workflows/daily-eval-sync.md`。

飞书第五节除交易观对照外，自动包含：

- **基线对比**一行（不操作 / 操作后 / 操作增量合计）
- **不操作少赚/多亏明细**表（全持仓标的，按操作增量排序）
