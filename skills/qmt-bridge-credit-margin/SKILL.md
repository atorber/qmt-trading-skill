---
name: qmt-bridge-credit-margin
description: >-
  通过 QMT Bridge 查询融资融券账户：担保品、可用保证金、信用相关交易端点。
  在用户提到两融、融资融券、保证金、信用账户时使用。按需启用；写操作须确认。
---

# QMT Trading Skill · 两融信用

> **实现状态**：✅ `credit_snapshot.py`、`credit_order.py` 可用（需两融账户）

## 目标

**信用账户**专用查询与规程，与现货 trading skill 隔离，避免误操作。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/credit_snapshot.py` | 信用资产/负债摘要；持仓按「总=融资+担保品」拆分（对齐 QMT 内置 `get_unclosed_compacts` + `position`） |
| `scripts/credit_order.py` | 信用下单：融资买入 / 融券卖出 / 买券还券 / 卖券还款；默认预览，`--execute --confirm` 才实盘 |

## 主要 API

| 前缀 | 说明 |
|------|------|
| `/api/credit/*` | 融资融券相关（见 `docs/rest-api.md`） |
| `/api/trading/*` | 部分信用下单可能共用，须区分账户类型 |

## 规程

1. 确认服务端已开通信用、账户 ID 正确
2. 只读快照优先
3. 开仓/平仓类写操作：**单独确认**，不与其他 skill 混用

## 信用下单

```bash
# 预览（默认，不提交）
python skills/qmt-bridge-credit-margin/scripts/credit_order.py 000001.SZ --finance-buy --volume 100

# 实盘：限价融资买入（须用户明确确认后再加 --execute --confirm）
python skills/qmt-bridge-credit-margin/scripts/credit_order.py 000001.SZ \
  --finance-buy --volume 100 --limit 10.50 --execute --confirm

# 卖券还款
python skills/qmt-bridge-credit-margin/scripts/credit_order.py 000001.SZ --sell-repay --volume 100 --execute --confirm
```

| 参数 | order_type | 含义 |
|------|-----------|------|
| `--finance-buy` | 27 | 融资买入 |
| `--short-sell` | 28 | 融券卖出 |
| `--buy-repay` | 29 | 买券还券 |
| `--sell-repay` | 31 | 卖券还款 |

担保品普通买卖请用 trading skill 的 `place_order.py`（`/api/trading/order` + 信用账户）。

## 安全

- 杠杆风险；默认实盘
- 无信用账户则跳过本 skill

## 信用持仓拆分

QMT 内置脚本逻辑（`compact_type=48` 为融资买入）在 Bridge 中等价为：

| QMT 内置 | Bridge / Skill |
|----------|----------------|
| `get_unclosed_compacts(account, 'CREDIT')` | `query_stk_compacts` → `/api/credit/debt` |
| `get_trade_detail_data(..., 'position')` | `query_credit_positions` → `/api/credit/positions` |
| 担保品 = 总持仓 − 融资量 | `/api/credit/positions/breakdown` 或 `credit_positions_util` |

```bash
python skills/qmt-bridge-credit-margin/scripts/credit_snapshot.py --port 8080 --api-key KEY
# JSON 含 breakdown: [{stock_code, total_volume, margin_volume, collateral_volume, ...}]
```

账户默认取 `.env` 中 `QMT_BRIDGE_CREDIT_ACCOUNT_ID`（不受 `QMT_BRIDGE_DEFAULT_ACCOUNT` 影响）；也可显式传 `--account-id`。

## 参考

- `docs/rest-api.md` · `src/qmt_bridge/server/routers/credit.py`
