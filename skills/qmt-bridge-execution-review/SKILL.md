---
name: qmt-bridge-execution-review
description: >-
  通过 QMT Bridge 生成当日交易复盘：客观证据（委托/成交/滑点/不操作基线/规则标签）+
  Agent 层投顾/基金经理/交易员三角色专家评审与综合裁决。
  在用户提到今日成交、交易复盘、今日操作评估、执行质量、三角色复盘、专家复盘、
  不操作少赚多亏时使用。只读。
---

# QMT Trading Skill · 交易复盘

> **实现状态**：✅ 客观脚本 + 证据包；✅ 三角色专家规程（Agent）

## 目标

闭合「计划—执行—复盘」：

1. **客观层（脚本）**：委托/成交/滑点、盈亏拆解、不操作基线、规则标签、算法参考分
2. **主观层（Agent）**：投顾 / 基金经理 / 交易员并行评审 → 综合裁决（见 [expert-review-protocol.md](references/expert-review-protocol.md)）

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_trade_report.py` | 单账户；默认 `--eval-mode=evidence` → `reports/daily_eval_evidence.json`；`--feishu-md` |
| `scripts/combined_trade_report.py` | 全账户综合；证据包 `reports/combined_daily_eval_evidence.json` |

### 产物路径（禁止写死机器绝对路径）

相对路径一律相对 **工作区根**（`workspace_root()`）：

| 布局 | 工作区根 | `reports/` 位置 |
|------|----------|-----------------|
| 本仓库开发 | 仓库根（含 `skills/`） | `<repo>/reports/` |
| Agent 安装 | Skills 安装根（`_shared` 的父目录） | `<skills-root>/reports/` |

- 脚本 stderr 会打印**实际写入的绝对路径**；后续读写请用该路径或相对 `reports/...`，**禁止**把某台机器的 `C:\GitHub\...` 写进规程/提示词
- 可选覆盖：`QMT_TRADING_SKILL_ROOT`（工作区根）或 `QMT_TRADING_SKILL_REPORTS`（reports 目录）

```bash
# 推荐：客观报告 + 证据包
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md

# 双账户
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md

# 旧版模板评语（对比校准）
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --eval-mode=rules --feishu-md
```

| 参数 | 说明 |
|------|------|
| `--eval-mode evidence\|rules` | 默认 `evidence`（事实+标签）；`rules` 旧模板叙事 |
| `--evidence-json [PATH]` | 证据包路径（evidence 模式默认写出） |
| `--feishu-md [PATH]` | 客观 Markdown（含第七节专家占位） |
| `--json` | stdout JSON（含 `operation_evaluation`） |
| `--no-eval` | 跳过评价与证据 |
| `--market-turnover-yi` / `--no-philosophy-fetch` | 同前 |

## 提示词示例

| 场景 | 提示词 |
|------|--------|
| **三角色专家复盘（推荐）** | `用投顾/基金经理/交易员三角色做今日复盘并综合裁决` |
| 客观报告 | `生成今日交易复盘（先出证据包）` |
| 基线对比 | `列一下不操作少赚/多亏的明细` |
| 全账户 | `普通户+信用户综合复盘并做三角色评审` |
| 旧规则对照 | `用 rules 模式跑一版复盘对比算法分` |

## 操作规程（Agent）

1. `health` 确认 Bridge；需要时按 [qmt-bridge-setup](../qmt-bridge-setup/SKILL.md) 检测服务
2. 跑 `daily_trade_report.py` 或 `combined_trade_report.py`（`--feishu-md`）
3. 读取 `reports/*_evidence.json` — **禁止编造数字**
4. 按 [expert-review-protocol.md](references/expert-review-protocol.md) 套用：
   - [personas/advisor.md](references/personas/advisor.md)
   - [personas/fund-manager.md](references/personas/fund-manager.md)
   - [personas/trader.md](references/personas/trader.md)
5. 写入 `reports/feishu_*_expert.md`，合并替换客观 MD 第七节
6. 同步飞书见 [feishu-doc](../qmt-bridge-feishu-doc/SKILL.md) — **允许**基于 evidence 写专家评语；**禁止**手写/篡改一～六客观章节
7. **只输出报告，不下单**

## 报告结构

```text
一～四  客观：概览 / 委托 / 成交 / 标的汇总
五      客观：盈亏与不操作基线
六      规则标签 + 算法参考分（algorithmic_only）
七      专家评审（Agent）
         7.1 投顾  7.2 基金经理  7.3 交易员  7.4 综合裁决
```

展示以 **7.4 专家综合** 为准；第六节算法分仅对照。

## 阈值与交易观

- 规则阈值：[references/thresholds.yaml](references/thresholds.yaml)
- 默认风格假设：[references/trading-philosophy.md](references/trading-philosophy.md)（标签来源，非最终评语）

## 不操作基线

| 概念 | 公式 |
|------|------|
| 不操作基线 | `昨仓股数 × (收盘价 − 昨收)` |
| 操作增量 | 实际盈亏 − 不操作基线 |

回答「少赚/多亏」时优先引用 evidence / `--feishu-md` 中的 `op_alpha_pnl`。

## 安全

- 只读；需交易查询 API Key
- 评述为统计归纳 + 专家视角，**非投资建议**

## 报告示例

见 [docs/examples/daily-eval-report.md](../../docs/examples/daily-eval-report.md)。
