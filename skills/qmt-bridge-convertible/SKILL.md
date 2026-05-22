---
name: qmt-bridge-convertible
description: >-
  通过 QMT Bridge 查询可转债列表与条款信息，辅助转债双低、强赎等策略观察。
  在用户提到可转债、转债、强赎、转股时使用。只读。
---

# QMT Trading Skill · 可转债

> **实现状态**：✅ `cb_snapshot.py` 可用

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/cb_snapshot.py` | 转债列表 + 单券 info |

## 主要 API

| 方法 | 路径 |
|------|------|
| GET | `/api/cb/list` |
| GET | `/api/cb/info` |
| POST | `/api/download/cb_data` |

## 规程

- 只读；交易走 trading skill
- 强赎/下修等规则以 info 字段为准，Skill 不预测价格

## 参考

- `docs/rest-api.md`
