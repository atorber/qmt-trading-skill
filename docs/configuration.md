# 配置参考（Skill 客户端）

Skill 脚本读取环境变量连接 **已启动的 QMT Bridge**。优先级：**命令行 `--host/--port/--api-key` > 环境变量 > `.env` > 默认值**。

服务端监听、交易开关、miniQMT 路径等见 [qmt-bridge 配置参考](https://github.com/atorber/qmt-bridge/blob/main/docs/configuration.md)。

## 连接 Bridge

| 环境变量 | 脚本参数 | 默认 | 说明 |
|---------|---------|------|------|
| `QMT_BRIDGE_HOST` | `--host` | `127.0.0.1` | **客户端目标**。用 `127.0.0.1` 或 Windows 局域网 IP，不要用 `0.0.0.0` |
| `QMT_BRIDGE_PORT` | `--port` | `8000`（客户端库默认） | 须与 Bridge 实际监听端口一致（其 `.env` 可能不是 8000） |
| `QMT_BRIDGE_API_KEY` | `--api-key` | 空 | 须与 Bridge 侧一致；交易/持仓类必填 |
| `QMT_BRIDGE_STOCK_ACCOUNT_ID` | `--account-id` | 空 | 普通户 |
| `QMT_BRIDGE_CREDIT_ACCOUNT_ID` | | 空 | 信用户 |
| `QMT_BRIDGE_DEFAULT_ACCOUNT` | | `stock` | 默认账户：`stock` \| `credit` |

## 复盘调度与飞书

| 环境变量 | 说明 |
|---------|------|
| `DAILY_EVAL_SCHEDULE_TIME` | 定时复盘时刻，默认 `15:10` |
| `DAILY_EVAL_SCHEDULE_INTERVAL_SEC` | 轮询间隔 |
| `DAILY_EVAL_SCHEDULE_COMBINED` | 是否双账户合并报告 |
| `FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN` | 飞书 Wiki 父节点 |
| `LARK_CLI_AS` | lark-cli 身份，如 `user` |
| `FEISHU_*_DOC_ID` / `FEISHU_*_TOKEN` | 见 `skills/qmt-bridge-feishu-doc` |

## `.env` 示例（本仓库）

```bash
QMT_BRIDGE_HOST=127.0.0.1
QMT_BRIDGE_PORT=8080
QMT_BRIDGE_API_KEY=your-secret-key
QMT_BRIDGE_DEFAULT_ACCOUNT=stock
```

认证方式与 Bridge 相同：HTTP 头 `X-API-Key`。
