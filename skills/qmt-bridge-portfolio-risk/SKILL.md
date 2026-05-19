---
name: qmt-bridge-portfolio-risk
description: >-
  通过 QMT Bridge 输出组合风险快照：仓位权重、现金占比、单票集中度、可卖数量与 T+1 提示。
  在用户提到仓位风险、集中度、组合敞口、下单前风控检查时使用。只读。
---

# QMT Bridge 组合风险 Skill

> **实现状态**：✅ `portfolio_snapshot.py` 可用

## 目标

**下单前**快速回答：钱够不够、仓是否过重、哪些票今天不能卖。

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/portfolio_snapshot.py` | positions + asset + 批量 tick 算权重与浮盈（可选） |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/positions` | 持仓 |
| GET | `/api/trading/asset` | 资产 |
| GET | `/api/market/full_tick` | 现价（批量） |
| GET | `/api/trading/position/{stock_code}` | 单票核查 |

## 规程（规划）

1. 拉 `asset`：`cash`、`market_value`、`total_asset`
2. 拉 `positions`，计算单票 `market_value / total_asset`
3. **阈值提示**（可在脚本参数配置）：单票权重 >30% 警告；现金占比过低警告
4. `can_use_volume < volume` → 标注 T+1 可卖不足
5. 通过 `batch_stock_name` 显示中文名称
6. 只读，不自动下单

## 安全

- 只读；交易查询需 API Key
- 阈值规则由用户配置，Skill 不做投资建议

## 参考

- [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) · `docs/rest-api.md`
