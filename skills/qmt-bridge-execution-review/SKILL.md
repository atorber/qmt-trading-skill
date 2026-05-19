---
name: qmt-bridge-execution-review
description: >-
  通过 QMT Bridge 生成当日交易复盘报告：委托、成交、买卖汇总与滑点观察。
  在用户提到今日成交、交易复盘、交割单、当日委托、执行质量时使用。
  只读；不执行下单。
---

# QMT Bridge 交易复盘 Skill

> **实现状态**：✅ `daily_trade_report.py` 可用（见 [ROADMAP.md](../ROADMAP.md)）

## 目标

闭合「计划—执行—复盘」中的**复盘**环节：汇总当日委托与成交，便于评估执行质量与纪律执行。

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/daily_trade_report.py` | 拉取 orders + trades + 可选 positions/asset，输出表格摘要 |

```bash
just agent-daily-report --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json
```

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/orders` | 当日委托 |
| GET | `/api/trading/trades` | 当日成交 |
| GET | `/api/trading/positions` | 收盘持仓（可选） |
| GET | `/api/trading/asset` | 资金（可选） |
| GET | `/api/calendar/is_trading_date` | 是否交易日 |

## 操作规程（规划）

1. `health` + `account_status` 确认服务与交易通道
2. 拉 `orders`、`trades`
3. 按 `stock_code` 汇总：买入/卖出笔数、成交量、均价、委托价 vs 成交价（滑点观察）
4. 标注未成交/已撤（`order_status`、`traded_volume`）
5. 通过 `GET /api/utility/batch_stock_name` 为委托/成交/汇总附带**中文名称**
6. **只输出报告，不下单**

## 安全

- 只读；需 `X-API-Key` 的交易查询端点
- 勿在输出中泄露完整 API Key

## 参考

- 已实现交易 Skill：[qmt-bridge-trading](../qmt-bridge-trading/SKILL.md)
- API 列表：`docs/rest-api.md`
