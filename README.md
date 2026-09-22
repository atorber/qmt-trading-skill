# QMT Trading Skill

> 在 Cursor / Claude Code / **豆包工作** / **WorkBuddy** 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API、`qmt-server`、`QMTClient` 在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。

**在线文档**：[GitHub Pages](https://atorber.github.io/qmt-trading-skill/) · [快速开始](docs/getting-started.md) · [Agent Skills](docs/agent-skills.md) · [skills/README.md](skills/README.md)

## 一键安装

在 **豆包工作** 、 **WorkBuddy** 等 Agent 的对话里直接粘贴下面提示词，Agent 会自动拉取并安装本仓库的 Skills。

```text
帮我安装这个 skill：https://github.com/atorber/qmt-trading-skill

安装布局（必须遵守）：
1. 把 skills/ 下每个 qmt-bridge-* 目录安装为独立 Skill（含 SKILL.md、scripts、references）。
2. 同时把 skills/_shared 复制到与上述 Skill 同一父目录下（与各 qmt-bridge-* 并列）。
   _shared 是共享库、没有 SKILL.md，不要注册成 Skill，但必须复制，否则脚本会 ImportError。
3. 一并复制 skills/VERSION 与 skills/.env.example（便于核对版本与配置连接）。
4. 不要把仓库根目录其它文件误装成 Skill。

安装完成后：读取 VERSION；说明如何用自然语言查持仓、当日盈亏和生成复盘；
并确认 _shared 已与各 Skill 同级存在；提醒用户按 README「配置客户端连接」写好 .env。
```

正确目录示例（父目录名因 Agent 而异，如 `~/.agents/skills`、`~/.workbuddy/skills`、`.cursor/skills`）：

```text
<skills-root>/
├── VERSION                 # 包版本
├── .env                    # 客户端连接配置（可选，见下方「配置客户端连接」）
├── .env.example            # 示例；社区安装时建议一并复制
├── _shared/                # 共享库（必须有，不是 Skill）
├── qmt-bridge-setup/
├── qmt-bridge-trading/
├── qmt-bridge-execution-review/
└── …其它 qmt-bridge-*
```

脚本用 `Path(__file__).parents[2] / "_shared"` 定位共享模块，因此 **`_shared` 必须与各 Skill 目录同级**。仅安装 `qmt-bridge-*`、漏拷 `_shared` 时，从技能目录跑脚本会失败。

### 通用 CLI（可选）

任意支持 [Agent Skills](https://skills.sh/) 的环境也可用：

```bash
npx skills add atorber/qmt-trading-skill -g -y
```

CLI 按仓库结构安装时一般会带上同仓文件；若本地只有分散的 Skill 目录，请按上面布局补齐 `_shared`。

安装 Skills 后，下一步是检测 / 按需启动 Bridge（见下方「使用」第 2 步），不要默认重复安装或重启已在跑的服务。

## 版本

| 项 | 位置 | 当前 |
|----|------|------|
| Skills 包版本 | [`skills/VERSION`](skills/VERSION) | **1.1.2** |
| Python 包版本 | [`pyproject.toml`](pyproject.toml) `project.version` | 与上同步 |
| 变更说明 | [`skills/CHANGELOG.md`](skills/CHANGELOG.md) | 按版本记录 |

发版约定：改 Skill 行为或新增 Skill 时递增 `skills/VERSION` 与 `pyproject.toml`，并在 `CHANGELOG.md` 写一行；Git tag 建议 `v1.1.0`。Agent 更新后应能读到新的 `VERSION` 内容。

## 更新 Skills（已安装用户）

仓库有新版本时，**已安装**本 Skill 包的 Agent 需主动拉取覆盖，不会自动升级。

### 对话一键更新（豆包工作 / WorkBuddy / Cursor 等）

```text
帮我把 qmt-trading-skill 更新到最新版：https://github.com/atorber/qmt-trading-skill

覆盖安装时保持布局：
1. 更新全部 qmt-bridge-* Skill 目录；
2. 同步更新同级的 _shared（共享库，不注册为 Skill，但必须存在）；
3. 更新 VERSION，读出并告诉我版本号。
```

若 Agent 使用 `npx skills`，也可说：`用 npx skills update 更新 atorber/qmt-trading-skill，并核对 VERSION`。

### 通用 CLI

```bash
# 检查是否有更新
npx skills check

# 更新全部已装 Skill（全局安装用 -g）
npx skills update -g -y

# 或强制重装本仓库（覆盖）
npx skills add atorber/qmt-trading-skill -g -y
```

### 开发克隆（git）

```powershell
cd qmt-trading-skill
git pull --recurse-submodules
git submodule update --init --recursive
# 核对版本
Get-Content skills\VERSION
```

更新后**新开一轮对话**再触发 Skill，避免旧会话缓存旧规程。若本地改过某 Skill 文件，覆盖前请自行备份。

## 仓库职责

| 仓库 | 内容 | 文档 |
|------|------|------|
| [atorber/qmt-bridge](https://github.com/atorber/qmt-bridge) | `qmt-server`、REST/WebSocket、`QMTClient`、PyPI 包 **`qmt-bridge-pro`**；长期守护用 PM2 | [atorber.github.io/qmt-bridge](https://atorber.github.io/qmt-bridge/) |
| **本仓库** [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | `skills/`、复盘调度、Skill 文档 | [atorber.github.io/qmt-trading-skill](https://atorber.github.io/qmt-trading-skill/) |

典型用法：在 Windows（与 QMT 同机）启动 Bridge → 在 Agent / 本仓跑 Skills。配置分两边：

- **Bridge（服务端）**：监听地址（可为 `0.0.0.0`）、交易开关、miniQMT 路径、API Key → 见 [qmt-bridge 配置](https://github.com/atorber/qmt-bridge/blob/main/docs/configuration.md)
- **Skills（客户端）**：只配连接目标 → 见下方「配置客户端连接」

运行时客户端：`pip install qmt-bridge-pro`（导入名仍是 `qmt_bridge`）。克隆本仓请带 submodule：`git clone --recurse-submodules ...`；开发对照源码可用 `pip install -e ./vendor/qmt-bridge`。

## 配置客户端连接

各 Skill 脚本通过 HTTP 访问已启动的 Bridge，**不会自动发现端口**。连接参数统一由 [`skills/_shared/common.py`](skills/_shared/common.py) 解析。

**优先级（高 → 低）：** 命令行 `--host` / `--port` / `--api-key` → 进程环境变量 → **`.env` 文件** → 默认值（`127.0.0.1` / `8000`）。

### `.env` 放哪里

| 安装方式 | `.env` 路径 |
|----------|-------------|
| 社区 / 对话安装进 Agent | **`<skills-root>/.env`**（与 `_shared`、`qmt-bridge-*` **同级**） |
| git 克隆本仓库开发 | **仓库根** `.env`（可复制根目录 [`.env.example`](.env.example)） |

社区安装时，也可一并复制 [`skills/.env.example`](skills/.env.example) 到 skills 根再改名为 `.env`。脚本还会尝试读取当前工作目录下的 `.env`，但**推荐始终写在 skills 根**，避免换对话目录后失效。

### 主要变量

| 变量 | 说明 |
|------|------|
| `QMT_BRIDGE_HOST` | 客户端目标，用 `127.0.0.1` 或 Windows 局域网 IP，**禁止** `0.0.0.0` |
| `QMT_BRIDGE_PORT` | 须与 Bridge **实际监听端口**一致（常见 `8080`；未配置时脚本默认 `8000`） |
| `QMT_BRIDGE_API_KEY` | 须与 Bridge 侧相同；交易 / 持仓类必填 |
| `QMT_BRIDGE_STOCK_ACCOUNT_ID` / `CREDIT_ACCOUNT_ID` | 普通户 / 信用户（可选） |
| `QMT_BRIDGE_DEFAULT_ACCOUNT` | `stock` 或 `credit`（可选） |

完整列表见 [docs/configuration.md](docs/configuration.md)。

### 方式一：手动改配置

1. 找到 skills 根（或仓库根），复制示例：

```powershell
# Agent 社区安装（在 skills 根执行）
copy .env.example .env

# 或本仓库开发克隆（在仓库根执行）
copy .env.example .env
```

2. 编辑 `.env`，至少设置 `HOST` / `PORT` / `API_KEY`，与 Bridge 一致。
3. 验证：

```powershell
python <skills-root>/qmt-bridge-setup/scripts/bridge_health.py
# 或显式指定
python .../bridge_health.py --host 127.0.0.1 --port 8080
```

也可不建文件，仅在本机设置系统环境变量，或每次命令行传 `--host` / `--port` / `--api-key`。

### 方式二：用 Skill 配置（推荐）

在对话中直接说（会走 [qmt-bridge-setup](skills/qmt-bridge-setup/SKILL.md)）：

```text
帮我配置 Skills 连接 QMT Bridge：主机 127.0.0.1，端口 8080，并写入 skills 根目录的 .env（不要把 API Key 打在聊天里，引导我本地填写）。写完后做一次健康检查。
```

或分步：

```text
检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动。已在跑则不要重复安装或重启。
然后把本机 Skills 的客户端 .env 与 Bridge 的端口、API Key 对齐。
```

Agent 规程要点：

1. 定位 **skills 根**（`_shared` 的父目录），打印将要写入的 `.env` 绝对路径
2. 若不存在则从 `.env.example` 复制；存在则只改连接相关键
3. **禁止**把真实 API Key / 资金账号完整打进对话；引导用户本地编辑或粘贴到终端
4. 写完后跑 `bridge_health.py`，在结果里确认实际使用的 host/port

改端口后无需重装 Skills；改完 `.env` 即可。若 Bridge 改了监听端口，客户端 `.env` 必须同步修改。

## 使用

### 1. 安装本仓库全部 Skills

先把本仓 `skills/` 下全部 Agent Skills 装进当前 Agent（跳过 `_shared`）。任选一种方式：

- **对话一键安装**（豆包工作 / WorkBuddy）：见上方「一键安装」提示词
- **CLI**：`npx skills add atorber/qmt-trading-skill -g -y`
- **开发克隆**（需跑脚本时）：

```powershell
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install qmt-bridge-pro
pip install -e ".[dev]"
cp .env.example .env
```

开发对照 Bridge 源码时用 `pip install -e ".\vendor\qmt-bridge"` 代替 PyPI。`.env` 中配置 `QMT_BRIDGE_HOST=127.0.0.1`、`QMT_BRIDGE_PORT`、`QMT_BRIDGE_API_KEY`（与 Bridge 一致）。

### 2. 检测并（按需）安装 / 启动 QMT Bridge

Skills 装好后，在对话中说：

```text
检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动。已在跑则不要重复安装或重启。
```

或 `@skills/qmt-bridge-setup/SKILL.md`。Agent 规程：

1. **先健康检查**（如 `bridge_health.py` / `GET /api/meta/health`）
2. **已可达** → 直接报告状态，**不重复安装、不重启**
3. **不可达** → 再按 setup Skill 安装 / 配置 / 启动（Windows 与 QMT 同机；QMT 需「独立交易」登录）
4. 启动成功后 → 按上方「配置客户端连接」对齐 skills 根（或仓库根）`.env`

连不上时优先核对：Bridge 是否在跑、`.env` 端口是否一致、HOST 是否误写成 `0.0.0.0`。

### 3. 开始使用

对话中直接说自然语言即可（也可 `@skills/.../SKILL.md`）。每个 Skill 一条典型提示词：

| Skill | 提示词 |
|-------|--------|
| [setup](skills/qmt-bridge-setup/SKILL.md) | `检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动` / `帮我配置 Skills 连接 Bridge 并写入 .env` |
| [trading](skills/qmt-bridge-trading/SKILL.md) | `帮我查持仓和可用资金` |
| [execution-review](skills/qmt-bridge-execution-review/SKILL.md) | `用投顾/基金经理/交易员三角色做今日复盘并综合裁决` |
| [feishu-doc](skills/qmt-bridge-feishu-doc/SKILL.md) | `把今日复盘同步到飞书` |
| [portfolio-risk](skills/qmt-bridge-portfolio-risk/SKILL.md) | `组合风险快照，看下持仓集中度` |
| [daily-pnl](skills/qmt-bridge-daily-pnl/SKILL.md) | `今天账户盈亏多少` |
| [order-ops](skills/qmt-bridge-order-ops/SKILL.md) | `查今日委托和可撤单` |
| [kline-backfill](skills/qmt-bridge-kline-backfill/SKILL.md) | `复盘前检查近3日两市成交额` |
| [return-analysis](skills/qmt-bridge-return-analysis/SKILL.md) | `评估持仓涨幅概率并总结明日策略` |
| [market-watch](skills/qmt-bridge-market-watch/SKILL.md) | `自选行情快照` |
| [sector-theme](skills/qmt-bridge-sector-theme/SKILL.md) | `今天行业强弱怎么排` |
| [financial-download](skills/qmt-bridge-financial-download/SKILL.md) | `下载财报到 Bridge 缓存` |
| [fundamental-screen](skills/qmt-bridge-fundamental-screen/SKILL.md) | `按 ROE、EPS 做基本面筛选` |
| [technical-signal](skills/qmt-bridge-technical-signal/SKILL.md) | `用 QMT 公式检查是否金叉` |
| [smart-execution](skills/qmt-bridge-smart-execution/SKILL.md) | `预览这笔买单会不会涨跌停` |
| [rebalance](skills/qmt-bridge-rebalance/SKILL.md) | `按目标权重生成调仓计划` |
| [credit-margin](skills/qmt-bridge-credit-margin/SKILL.md) | `查两融保证金和担保品` |
| [realtime-monitor](skills/qmt-bridge-realtime-monitor/SKILL.md) | `WebSocket 订阅实时行情` |
| [event-calendar](skills/qmt-bridge-event-calendar/SKILL.md) | `今天是不是交易日` |
| [etf](skills/qmt-bridge-etf/SKILL.md) | `查 ETF 列表和申赎清单` |
| [convertible](skills/qmt-bridge-convertible/SKILL.md) | `可转债列表和条款快照` |
| [option](skills/qmt-bridge-option/SKILL.md) | `查 510050 期权链` |
| [hk-connect](skills/qmt-bridge-hk-connect/SKILL.md) | `港股通标的有哪些` |

更多变体见 [skills/README.md](skills/README.md)。写操作（下单、撤单、调仓、下载财报等）须你确认后再执行。

## 开发（对照并修改 Bridge）

`vendor/qmt-bridge` 为 Git submodule。改 Bridge 后先在子模块提交推送，再 `git add vendor/qmt-bridge` 更新指针。打开 `qmt-trading-skill.code-workspace` 可同时浏览两仓。

## 许可

[MIT](LICENSE)