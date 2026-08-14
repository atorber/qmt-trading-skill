---
name: qmt-bridge-realtime-monitor
description: >-
  指导通过 QMT Bridge WebSocket 订阅实时行情、L2、公式推送与交易回报并对账。
  在用户提到 WebSocket 订阅、盘中推送、成交回报、实时盯盘时使用。规程为主。
---

# QMT Trading Skill · 实时监控

> **实现状态**：✅ `ws_subscribe.py` + WebSocket 规程

## 目标

规范 **WebSocket** 使用方式，避免 Agent 随意长连或泄露 Key。

## WebSocket 端点

| 路径 | 用途 | 认证 |
|------|------|------|
| `/ws/realtime` | 实时行情 | 无 |
| `/ws/whole_quote` | 全市场 | 无 |
| `/ws/l2_thousand` | L2 千档 | 无 |
| `/ws/formula` | 公式推送 | 无 |
| `/ws/download_progress` | 下载进度 | 无 |
| `/ws/trade` | 交易回报 | `?api_key=` |

详见 `docs/websocket.md`。

## 规程（规划）

1. 订阅前 `health` + 明确订阅代码列表
2. 交易回报：`/ws/trade` 与 `GET /api/trading/orders` 定期对账
3. 突破提醒：在客户端聚合 tick，**不**把全量 L2 dump 给 LLM
4. 断线重连：指数退避；记录最后 seq/时间
5. 停止订阅：明确 `unsubscribe` 或关闭连接

## 规划脚本（可选）

| 脚本 | 作用 |
|------|------|
| `scripts/ws_subscribe.py` | CLI 示例：订阅 codes 并打印摘要 N 秒 |

## 安全

- `/ws/trade` 的 api_key 勿写入日志
- 监控不等于自动下单

## 参考

- [qmt-bridge-technical-signal](../qmt-bridge-technical-signal/SKILL.md)
- [qmt-bridge-order-ops](../qmt-bridge-order-ops/SKILL.md)
