---
name: qmt-bridge-smart-execution
description: >-
  通过 QMT Bridge 做下单前执行预览：价格类型选择、涨跌停检查、分批建议。
  在用户提到怎么下单、限价还是市价、分批、滑点、执行方案时使用。默认预览，提交须确认。
---

# QMT Trading Skill · 智能执行

> **实现状态**：✅ `execution_preview.py` 可用

## 目标

在调用 [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) 前，生成**可审阅的执行方案**（非自动交易）。

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/execution_preview.py` | 输入标的/方向/数量 → 输出建议 price_type、风险提示 |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/market/full_tick` | 现价、涨跌停 |
| GET | `/api/trading/positions` | 可卖数量 |
| GET | `/api/trading/asset` | 可用资金 |
| POST | `/api/trading/order` | 实际下单（须转 trading skill + 确认） |

## 规程（规划）

1. 拉 tick：距涨停/跌停距离
2. 卖出：校验 `can_use_volume`
3. 买入：校验 `cash` 与预估金额
4. 大单：若超过阈值建议 `batch_order` 分批（阈值可配置）
5. 输出预览；**提交订单必须** `--execute --confirm` 且用户同意

## 常量（与 trading 一致）

- `order_type` 23 买 / 24 卖
- `price_type` 5 最新价 / 11 限价 / 42 最优五档即时成交剩余撤销

## 安全

- 预览默认；禁止静默下单
- 真实资金默认实盘

## 参考

- [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) · [qmt-bridge-portfolio-risk](../qmt-bridge-portfolio-risk/SKILL.md)
