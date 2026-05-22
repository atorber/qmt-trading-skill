---
name: qmt-bridge-etf
description: >-
  通过 QMT Bridge 查询 ETF 列表、申赎清单与相关行情，辅助 ETF 投资与套利观察。
  在用户提到 ETF、申赎、指数基金、ETF 套利时使用。只读。
---

# QMT Trading Skill · ETF

> **实现状态**：✅ `etf_snapshot.py` 可用

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/etf_snapshot.py` | ETF 列表 + 指定 ETF info + tick |

## 主要 API

| 方法 | 路径 |
|------|------|
| GET | `/api/etf/list` |
| GET | `/api/etf/info` |
| GET | `/api/market/full_tick` |
| POST | `/api/download/etf_info` |

## 规程

- 只读观察；申赎/交易走 [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md)
- 套利需用户自行定义阈值

## 参考

- `docs/rest-api.md`
