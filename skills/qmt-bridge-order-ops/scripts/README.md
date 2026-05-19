# qmt-bridge-order-ops 脚本

| 脚本 | 状态 | 说明 |
|------|------|------|
| `list_orders.py` | ✅ | 委托列表，`--cancelable-only` |
| `cancel_orders.py` | ✅ | `--sysid` 或 `--cancelable-only`；`--execute --confirm` 撤单 |

```bash
just agent-list-orders --port 8080 --api-key KEY
just agent-cancel-orders --cancelable-only --port 8080 --api-key KEY
```
