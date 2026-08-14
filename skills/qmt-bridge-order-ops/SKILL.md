---
name: qmt-bridge-order-ops
description: >-
  通过 QMT Bridge 管理当日委托：查询可撤单、单笔/批量撤单、委托详情。
  在用户提到撤单、取消委托、查挂单、可撤订单、错单处理时使用。写操作须用户确认。
---

# QMT Trading Skill · 委托运维

> **实现状态**：✅ `list_orders.py`、`cancel_orders.py` 可用

## 目标

盘中**不新增敞口**的委托管理：查单、撤单；与 [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) 分工（后者负责下单/清仓）。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/list_orders.py` | 当日委托列表；`--cancelable-only` 仅可撤 |
| `scripts/cancel_orders.py` | `--sysid` 或 `--cancelable-only`；`--execute --confirm` 撤单 |

```bash
python skills/qmt-bridge-order-ops/scripts/list_orders.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-order-ops/scripts/cancel_orders.py --sysid 411494 --stock 688676.SH --execute --confirm
```

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trading/orders` | 委托列表 |
| GET | `/api/trading/order/{order_id}` | 指定委托 |
| GET | `/api/trading/order_detail` | 委托详情 |
| POST | `/api/trading/cancel` | 撤单 |
| POST | `/api/trading/batch_cancel` | 批量撤单 |
| POST | `/api/trading/cancel_by_sysid` | 按合同编号撤单 |

## 规程（规划）

1. 默认 `list_orders.py` 只读展示
2. 撤单前列出：`stock_code`、方向、价格、剩余量、`order_sysid`
3. **必须用户确认**后 `cancel_orders.py --execute --confirm`
4. 撤单后建议再查 `orders` 核对状态

## 安全

- 撤单影响实盘；禁止未经确认批量撤全部
- 401 → API Key；勿泄露 Key

## 参考

- [qmt-bridge-trading](../qmt-bridge-trading/SKILL.md) · `docs/rest-api.md`
