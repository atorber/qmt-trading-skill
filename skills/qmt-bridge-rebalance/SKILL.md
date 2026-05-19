---
name: qmt-bridge-rebalance
description: >-
  通过 QMT Bridge 根据目标权重生成组合再平衡买卖清单，预览后批量下单。
  在用户提到调仓、再平衡、目标仓位、权重对齐时使用。提交须用户确认。
---

# QMT Bridge 组合再平衡 Skill

> **实现状态**：✅ `rebalance_plan.py` 可用

## 目标

将**目标权重表**转为买卖差额清单，减少手工算股数错误。

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/rebalance_plan.py` | `--targets` JSON/CSV；输出买卖预览 |
| （提交） | 预览确认后调用 `batch_order`（`--execute --confirm`） |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/positions` | 当前持仓 |
| GET | `/api/trading/asset` | 总资产 |
| GET | `/api/market/full_tick` | 现价估市值 |
| POST | `/api/trading/batch_order` | 批量下单 |

## 规程（规划）

1. 读入目标权重（总和应≈1，允许现金权重）
2. 当前市值 vs 目标 → 差额股数（整手取整规则：A 股 100 股）
3. 输出买卖列表 + 预估成交金额
4. **用户确认**后执行 `batch_order`
5. 执行后建议 [execution-review](../qmt-bridge-execution-review/SKILL.md) 核对

## 安全

- 批量下单影响大；必须双重确认
- 先 [portfolio-risk](../qmt-bridge-portfolio-risk/SKILL.md) 可选

## 参考

- [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) · `docs/rest-api.md`
