---
name: qmt-bridge-credit-margin
description: >-
  通过 QMT Bridge 查询融资融券账户：担保品、可用保证金、信用相关交易端点。
  在用户提到两融、融资融券、保证金、信用账户时使用。按需启用；写操作须确认。
---

# QMT Bridge 两融信用 Skill

> **实现状态**：✅ `credit_snapshot.py` 可用（需两融账户）

## 目标

**信用账户**专用查询与规程，与现货 trading skill 隔离，避免误操作。

## 规划脚本

| 脚本 | 作用 |
|------|------|
| `scripts/credit_snapshot.py` | 信用资产/负债/担保品摘要（只读） |

## 主要 API

| 前缀 | 说明 |
|------|------|
| `/api/credit/*` | 融资融券相关（见 `docs/rest-api.md`） |
| `/api/trading/*` | 部分信用下单可能共用，须区分账户类型 |

## 规程（规划）

1. 确认服务端已开通信用、账户 ID 正确
2. 只读快照优先
3. 开仓/平仓类写操作：**单独确认**，不与其他 skill 混用

## 安全

- 杠杆风险；默认实盘
- 无信用账户则跳过本 skill

## 参考

- `docs/rest-api.md` · `src/qmt_bridge/server/routers/credit.py`
