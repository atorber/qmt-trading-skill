---
name: qmt-bridge-hk-connect
description: >-
  通过 QMT Bridge 查询港股通标的、连接方向与经纪商字典，辅助港股通投资筛选。
  在用户提到港股通、沪港通、深港通、港股标的时使用。只读。
---

# QMT Trading Skill · 港股通

> **实现状态**：✅ `hk_universe.py` 可用

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/hk_universe.py` | 港股通列表 + 可选筛选 |

## 主要 API

| 方法 | 路径 |
|------|------|
| GET | `/api/hk/stock_list` |
| GET | `/api/hk/connect_stocks` |
| GET | `/api/hk/broker_dict` |

## 规程

- 只读；交易若走港股通账户须确认账户与 trading 配置
- 行情可能需单独权限，失败时提示用户

## 参考

- `docs/rest-api.md`
