---
name: qmt-bridge-execution-review
description: >-
  通过 QMT Bridge 生成当日交易复盘：委托、成交、滑点、按标的汇总，
  并结合当日盈亏输出操作评价（做得好的/需改进/执行质量/明日纪律）。
  在用户提到今日成交、交易复盘、今日操作评估、执行质量时使用。只读。
---

# QMT Bridge 交易复盘 Skill

> **实现状态**：✅ `daily_trade_report.py` 可用（见 [ROADMAP.md](../ROADMAP.md)）

## 目标

闭合「计划—执行—复盘」中的**复盘**环节：

1. 汇总当日委托与成交，评估滑点与撤单
2. 按标的汇总买卖量
3. **当日操作评价**：结合盈亏拆解，归纳止盈/加仓/逆势操作、总评与纪律提示

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_trade_report.py` | orders + trades + 操作评价；`--json` |

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
```

| 参数 | 说明 |
|------|------|
| `--json` | JSON（含 `operation_evaluation`） |
| `--no-trades` | 跳过成交列表 |
| `--no-summary` | 跳过按标的汇总 |
| `--no-eval` | 不输出操作评价 |

## 提示词示例（可复制）

| 场景 | 提示词 |
|------|--------|
| **复盘+评价（推荐）** | `生成今日交易复盘并做当日操作评价` |
| | `今日操作评估：得失、执行质量、明日纪律` |
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

- **分标的**：操作类型（大涨止盈/逆势加仓/顺势加仓等）、当日盈亏、仓位变化
- **总评**：1～10 分 + 做得好的 / 需改进 / 执行质量（滑点、撤单、现金占比）
- 统计归纳，**非投资建议**

## 安全

- 只读；需 `X-API-Key` 的交易查询端点

## 发布到飞书云文档

同步飞书：使用 **[qmt-bridge-feishu-doc](../qmt-bridge-feishu-doc/SKILL.md)** + **lark-doc** / **lark-drive** Skill（`lark-cli docs +update`，勿用 `scripts/` 飞书脚本）。工作流见 `references/workflows/daily-eval-sync.md`。
