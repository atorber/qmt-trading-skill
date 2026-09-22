---
name: qmt-bridge-setup
description: >-
  安装、配置并启动 QMT Bridge（qmt-server / PM2），检查健康状态，并同步本仓客户端 .env。
  在用户提到安装 Bridge、启动 qmt-server、PM2 守护、Bridge 连不上、健康检查、
  配置 miniQMT 路径或 API Key 时使用。不涉及下单。
---

# QMT Trading Skill · Bridge 安装与启动

> **实现状态**：✅ 规程可用；`bridge_health.py` 做连通性检查

## 目标

在 **Windows（与 QMT 同机）** 安装并启动 [qmt-bridge](https://github.com/atorber/qmt-bridge)，使本仓及其他 Agent Skills 能通过 HTTP 调用行情与交易接口。

## 总规程（必须遵守）

1. **先健康检查**：运行 `bridge_health.py` 或请求 `GET /api/meta/health`
2. **服务已可达** → 向用户报告主机/端口与健康结果，**禁止**重复 `pip install`、禁止重启 / 再启 `qmt-server` / PM2（除非用户明确要求重启）
3. **服务不可达** → 再按下方「安装 → 启动 → 验证 → 同步本仓 `.env`」执行；安装前探测本地是否已有 Bridge 仓库，有则跳过 clone

## 提示词示例

| 场景 | 提示词 |
|------|--------|
| 推荐（先检测） | `检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动。已在跑则不要重复安装或重启。` |
| 首次安装 | `帮我安装并启动 QMT Bridge` |
| 日常启动 | `启动 qmt-server` · `用 PM2 拉起 Bridge` |
| 排障 | `Bridge 连不上，帮我做健康检查` · `检查 qmt-server 是否在跑` |
| 配置客户端连接 | `帮我配置 Skills 连接 QMT Bridge：主机 127.0.0.1，端口 8080，写入 skills 根 .env 后做健康检查（API Key 勿打进聊天）` |
| 配置 Bridge 服务端 | `配置 Bridge 的端口、API Key 和 miniQMT 路径` |

## 前提条件

- **Windows** + **Python 3.10+**
- 已安装 **QMT 客户端**，券商已开通 miniQMT；启动前勾选 **「独立交易」** 登录并保持运行
- 长期守护需 **Node.js** + 全局 `pm2`（`npm install -g pm2`）
- 本机或局域网防火墙放行 Bridge 端口（常用 `8080` / `.env` 中实际端口）

## Bridge 源码位置（按优先级）

1. 本仓 submodule：`vendor/qmt-bridge`（开发对照）
2. 并列目录：`../qmt-bridge`
3. 单独克隆：`git clone https://github.com/atorber/qmt-bridge.git`

Agent 先探测本地是否已有仓库，再决定 clone / 跳过。

## 规程：安装

在 **Bridge 仓库根目录**（非本 Skill 仓）：

```powershell
cd <qmt-bridge 根目录>
pip install -e ".[full]"
copy .env.example .env
```

仅客户端（在主力机跑 Skill、不启服务）可：`pip install qmt-bridge-pro`（导入名仍是 `qmt_bridge`）。

编辑 Bridge 侧 `.env`（服务端）：

| 变量 | 说明 |
|------|------|
| `QMT_BRIDGE_HOST` | 服务监听，局域网访问用 `0.0.0.0` |
| `QMT_BRIDGE_PORT` | 监听端口（与本仓客户端一致） |
| `QMT_BRIDGE_API_KEY` | 交易端点密钥 |
| `QMT_BRIDGE_TRADING_ENABLED` | 启用交易时设 `true` |
| `QMT_BRIDGE_MINI_QMT_PATH` | 如 `C:\国金QMT交易端\userdata_mini` |
| `QMT_BRIDGE_STOCK_ACCOUNT_ID` / `CREDIT_ACCOUNT_ID` | 普通户 / 信用户 |
| `QMT_BRIDGE_DEFAULT_ACCOUNT` | `stock` 或 `credit` |

## 规程：启动

1. 确认 QMT 已以「独立交易」登录
2. **前台**（调试）：

```powershell
qmt-server --port 8080 --trading --api-key your-secret-key `
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" `
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
```

或依赖 `.env` 后直接：`qmt-server` / `scripts\start.bat`

3. **PM2 守护**（推荐长期运行）：

```bat
REM 可选：set PM2_PYTHON=C:\path\to\venv\Scripts\python.exe
scripts\pm2-start.bat
pm2 status
pm2 logs qmt-server
```

停止：`scripts\pm2-stop.bat`。开机自启（管理员）：`pm2 startup` → `pm2 save`。

## 规程：验证

**任何安装 / 启动操作之前与之后都应跑一次。**

```powershell
# 浏览器或 curl
# http://127.0.0.1:<端口>/docs
curl http://127.0.0.1:8080/api/meta/health

# 本仓脚本（读本仓 .env）
python skills/qmt-bridge-setup/scripts/bridge_health.py
python skills/qmt-bridge-setup/scripts/bridge_health.py --host 127.0.0.1 --port 8080
```

- 启动**前**已成功 → 停止后续安装/启动步骤
- 启动**后**成功 → 再同步本仓客户端 `.env`（若尚未配置）

健康检查通过后再跑交易/复盘类 Skill。

## 规程：同步客户端 `.env`

配置写在 **Skills 安装根**（与 `_shared` 同级），不是某个单独的 `qmt-bridge-*` 目录内。

| 场景 | `.env` 位置 |
|------|-------------|
| 社区 / Agent 安装 | `<skills-root>/.env`（可先复制同级的 `.env.example`） |
| git 克隆本仓库 | 仓库根 `.env`（复制仓库根或 `skills/.env.example`） |

```powershell
# 在 skills 根（Agent 安装）或仓库根（开发克隆）
copy .env.example .env
```

| 变量 | 要求 |
|------|------|
| `QMT_BRIDGE_HOST` | `127.0.0.1` 或 Windows 局域网 IP，**禁止** `0.0.0.0` |
| `QMT_BRIDGE_PORT` | 与 Bridge 实际监听端口相同 |
| `QMT_BRIDGE_API_KEY` | 与 Bridge 相同（**勿**把真实值打进聊天） |
| 账户 ID | 与 Bridge 侧一致（复盘双账户时配齐普通户+信用户） |

Agent 用 Skill 帮用户配置时：

1. 解析 skills 根（`_shared` 的父目录），**打印**将写入的 `.env` 绝对路径
2. 无文件则从 `.env.example` 复制；有则只更新连接相关键
3. 引导用户本地填写 API Key / 账号；写完后跑 `bridge_health.py` 并报告实际 host/port

更完整的说明见仓库 README「配置客户端连接」。

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/bridge_health.py` | 调用 `GET /api/meta/health`，打印连通结果（只读，无需 API Key） |

## 安全

- 不代填真实资金账号/密钥到聊天记录；引导用户本地改 `.env`
- 不自动开启交易开关；用户明确要求交易时才设 `QMT_BRIDGE_TRADING_ENABLED` / `--trading`
- 本 Skill **不下单**；写操作走 [trading](../qmt-bridge-trading/SKILL.md) 等并需确认

## 常见问题

| 现象 | 处理 |
|------|------|
| 连接失败 / URLError | Bridge 未启、端口不对、HOST 写成了 `0.0.0.0` |
| 交易接口 401 | API Key 不一致或未配置 |
| BSON / get_local_data 崩溃 | **重启 QMT 客户端**（见 Bridge CLAUDE.md） |
| PM2 找不到 | `npm install -g pm2`；用 `PM2_PYTHON` 指向 venv |

## 参考

- Bridge 文档：[快速开始](https://atorber.github.io/qmt-bridge/getting-started/) · [配置](https://atorber.github.io/qmt-bridge/configuration/)
- 仓库：[atorber/qmt-bridge](https://github.com/atorber/qmt-bridge)
