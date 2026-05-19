---
name: qmt-bridge-option
description: >-
  通过 QMT Bridge 查询期权链、合约详情与列表，辅助期权策略与对冲分析。
  在用户提到期权、期权链、认沽认购、对冲时使用。只读。
---

# QMT Bridge 期权 Skill

> **实现状态**：✅ `option_chain_snapshot.py` 可用

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/option_chain_snapshot.py` | 标的 → 期权链摘要 |

## 主要 API

| 方法 | 路径 |
|------|------|
| GET | `/api/option/chain` |
| GET | `/api/option/detail` |
| GET | `/api/option/list` |
| GET | `/api/option/his_option_list` |

## 规程

- 只读；开仓/平仓若 API 支持须单独确认
- 希腊值/定价若 API 未提供，不在 Skill 内推算

## 参考

- `docs/rest-api.md`
