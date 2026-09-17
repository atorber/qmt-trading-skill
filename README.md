# QMT Trading Skill

> 在 Cursor / Claude Code / **豆包工作** / **WorkBuddy** 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API、`qmt-server`、`QMTClient` 在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。

**在线文档**：[GitHub Pages](https://atorber.github.io/qmt-trading-skill/) · [快速开始](docs/getting-started.md) · [Agent Skills](docs/agent-skills.md) · [skills/README.md](skills/README.md)

## 一键安装（豆包工作 / WorkBuddy）

在 **豆包工作** 或 **WorkBuddy** 的对话里直接粘贴下面提示词，Agent 会自动拉取并安装本仓库的 Skills。

### 豆包工作

```text
帮我安装这个 skill：https://github.com/atorber/qmt-trading-skill
请把仓库 skills/ 目录下的全部 Agent Skills 安装到当前环境（每个子目录一个 Skill，跳过 _shared）。
安装完成后告诉我如何用自然语言查询持仓、当日盈亏和生成复盘。
```

也可走界面：电脑版进入「技能 · 连接器 · 伙伴」→「我的技能」→「新建 — 上传技能」，将本地 `skills/qmt-bridge-*` 目录拖入即可（豆包工作也会自动发现本机 `.agents/skills`、`.codex/skills`）。

### WorkBuddy

```text
帮我安装这个 skill：https://github.com/atorber/qmt-trading-skill
请安装 skills/ 下全部 Agent Skills 到 ~/.workbuddy/skills/（每个子目录一个 Skill，跳过 _shared）。
安装完成后新建对话，用自然语言即可调用（例如「今天账户盈亏多少」）。
```

### 通用 CLI（可选）

任意支持 [Agent Skills](https://skills.sh/) 的环境也可用：

```bash
npx skills add atorber/qmt-trading-skill -g -y
```

安装 Skills 后，下一步是检测 / 按需启动 Bridge（见下方「使用」第 2 步），不要默认重复安装或重启已在跑的服务。

## 仓库职责

| 仓库 | 内容 | 文档 |
|------|------|------|
| [atorber/qmt-bridge](https://github.com/atorber/qmt-bridge) | `qmt-server`、REST/WebSocket、`QMTClient`、PyPI 包 **`qmt-bridge-pro`**；长期守护用 PM2 | [atorber.github.io/qmt-bridge](https://atorber.github.io/qmt-bridge/) |
| **本仓库** [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | `skills/`、复盘调度、Skill 文档 | [atorber.github.io/qmt-trading-skill](https://atorber.github.io/qmt-trading-skill/) |

典型用法：在 Windows（与 QMT 同机）启动 Bridge → 在本仓跑 Agent / 脚本。配置也分两边：

- **Bridge**：监听地址（可为 `0.0.0.0`）、交易开关、miniQMT 路径、API Key
- **本仓 `.env`**：只配客户端连接——`QMT_BRIDGE_HOST=127.0.0.1`（或 Windows 局域网 IP，**不要用 `0.0.0.0`**），端口与 API Key 须与 Bridge 一致

运行时客户端：`pip install qmt-bridge-pro`（导入名仍是 `qmt_bridge`）。克隆本仓请带 submodule：`git clone --recurse-submodules ...`；开发对照源码可用 `pip install -e ./vendor/qmt-bridge`。

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

### 3. 开始使用

对话中直接说自然语言即可（也可 `@skills/.../SKILL.md`）。每个 Skill 一条典型提示词：

| Skill | 提示词 |
|-------|--------|
| [setup](skills/qmt-bridge-setup/SKILL.md) | `检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动` |
| [trading](skills/qmt-bridge-trading/SKILL.md) | `帮我查持仓和可用资金` |
| [execution-review](skills/qmt-bridge-execution-review/SKILL.md) | `生成今日交易复盘并评价操作质量` |
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