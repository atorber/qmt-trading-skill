---
name: qmt-bridge-market-watch
description: >-
  通过 QMT Bridge 对自选标的做行情快照：涨跌幅、现价、指数环境、交易日校验。
  在用户提到看盘、自选监控、盘前检查、行情快照、大盘环境时使用。只读，不下单。
---

# QMT Bridge 自选监控 Skill

> **实现状态**：✅ `watchlist_snapshot.py`

## 目标

盘前/盘中/盘后快速浏览**自选池**与**大盘环境**，输出表格摘要（含中文名称）。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/watchlist_snapshot.py` | `--codes` 自选；`--indices-only` 仅指数 |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/market/full_tick` | 实时快照 |
| GET | `/api/market/indices` | 主要指数 |
| GET | `/api/market/market_data_ex` | K 线（可选） |
| GET | `/api/calendar/is_trading_date` | 交易日 |
| GET | `/api/utility/search` | 代码/名称搜索 |
| GET | `/api/meta/last_trade_date` | 最近交易日 |

## 规程（规划）

1. 校验交易日（可选，见 event-calendar）
2. 拉 `indices` 作为环境背景（或 `--indices-only` 快速看盘）
3. 对 `--codes` 批量 `full_tick`，输出涨跌幅等
4. **只输出观察结果，不推荐买卖**

## 安全

- 只读；行情端点默认无需 Key（若服务端开启数据鉴权则配置 Key）

## 参考

- `docs/rest-api.md` · [qmt-bridge-sector-theme](../qmt-bridge-sector-theme/SKILL.md)
