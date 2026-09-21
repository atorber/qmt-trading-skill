# 快速开始

本仓库是 **Agent Skills** 层：在 Cursor / Claude Code / 豆包工作 / WorkBuddy 里用自然语言驱动脚本，通过 HTTP 调用 **QMT Bridge**。

## 架构

```
Mac / Linux / Windows（主力机 · 本仓库）     Windows（中转站）
┌──────────────────────┐                ┌─────────────────────────┐
│ Cursor / 豆包 / WorkBuddy │ HTTP/WS  │  QMT 客户端（登录中）      │
│ @skills/.../SKILL.md │ ◄───────────► │  qmt-server (qmt-bridge) │
│ 分析 / 本地报告       │   局域网       │  xtquant                 │
└──────────────────────┘                └─────────────────────────┘
```

## 1. 安装本仓库全部 Skills

先把本仓 `skills/` 下全部 Agent Skills 装进当前 Agent（跳过 `_shared`）。

### 豆包工作

```text
帮我安装这个 skill：https://github.com/atorber/qmt-trading-skill
请把仓库 skills/ 目录下的全部 Agent Skills 安装到当前环境（每个子目录一个 Skill，跳过 _shared）。
安装完成后告诉我如何用自然语言查询持仓、当日盈亏和生成复盘。
```

也可走界面：「技能 · 连接器 · 伙伴」→「我的技能」→「新建 — 上传技能」，拖入本地 `skills/qmt-bridge-*`（豆包工作也会自动发现本机 `.agents/skills`、`.codex/skills`）。

### WorkBuddy

```text
帮我安装这个 skill：https://github.com/atorber/qmt-trading-skill
请安装 skills/ 下全部 Agent Skills 到 ~/.workbuddy/skills/（每个子目录一个 Skill，跳过 _shared）。
安装完成后新建对话，用自然语言即可调用（例如「今天账户盈亏多少」）。
```

### 通用 CLI

```bash
npx skills add atorber/qmt-trading-skill -g -y
```

### 更新已安装的 Skills

仓库发新版后需主动覆盖安装（不会自动升级）。包版本见 [`skills/VERSION`](../skills/VERSION)。

**对话提示词**（豆包工作 / WorkBuddy / Cursor 等）：

```text
帮我把 qmt-trading-skill 更新到最新版：https://github.com/atorber/qmt-trading-skill
请覆盖安装 skills/ 目录下的全部 Agent Skills（每个子目录一个 Skill，跳过 _shared）。
更新后读取并告诉我 skills/VERSION 的内容，确认已是最新。
```

**CLI**：

```bash
npx skills check
npx skills update -g -y
# 或
npx skills add atorber/qmt-trading-skill -g -y
```

**git 克隆**：`git pull --recurse-submodules` 后查看 `skills/VERSION`。更新后建议新开对话再调用 Skill。

完整说明见 [仓库 README · 更新 Skills](https://github.com/atorber/qmt-trading-skill#更新-skills已安装用户)。

### 开发克隆（需跑脚本时）

```bash
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install qmt-bridge-pro
pip install -e ".[dev]"
cp .env.example .env
```

开发对照 Bridge 源码：`pip install -e "./vendor/qmt-bridge"`。

编辑 `.env`：`QMT_BRIDGE_HOST` / `QMT_BRIDGE_PORT` / `QMT_BRIDGE_API_KEY` 须与 Bridge 一致。

!!! tip "客户端地址"
    服务端可监听 `0.0.0.0`；**Skill 脚本请连接 `127.0.0.1` 或 Windows 局域网 IP**，不要把 `0.0.0.0` 当作 HTTP 目标。

## 2. 检测并（按需）安装 / 启动 QMT Bridge

Skills 装好后，在对话中说：

```text
检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动。已在跑则不要重复安装或重启。
```

或 `@skills/qmt-bridge-setup/SKILL.md`（见 [qmt-bridge-setup](../skills/qmt-bridge-setup/SKILL.md)）。Agent 规程：

1. **先健康检查**（`bridge_health.py` / `GET /api/meta/health`）
2. **已可达** → 直接报告状态，**不重复安装、不重启**
3. **不可达** → 再安装 / 配置 / 启动（Windows 与 QMT 同机；QMT 需「独立交易」登录）

手动启动示例：

```bash
# 在 qmt-bridge 仓库
pip install -e ".[full]"
qmt-server --port 8080 --trading --api-key your-secret-key \
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" \
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
```

验证：`http://127.0.0.1:8080/docs`、`GET /api/meta/health`，或：

```bash
python skills/qmt-bridge-setup/scripts/bridge_health.py
```

## 3. 开始使用

对话中直接说自然语言即可。每个 Skill 一条典型提示词（共 23 条）：

| Skill | 提示词 |
|-------|--------|
| [setup](../skills/qmt-bridge-setup/SKILL.md) | `检查 QMT Bridge 是否已启动；若未启动再帮我安装并启动` |
| [trading](../skills/qmt-bridge-trading/SKILL.md) | `帮我查持仓和可用资金` |
| [execution-review](../skills/qmt-bridge-execution-review/SKILL.md) | `用投顾/基金经理/交易员三角色做今日复盘并综合裁决` |
| [feishu-doc](../skills/qmt-bridge-feishu-doc/SKILL.md) | `把今日复盘同步到飞书` |
| [portfolio-risk](../skills/qmt-bridge-portfolio-risk/SKILL.md) | `组合风险快照，看下持仓集中度` |
| [daily-pnl](../skills/qmt-bridge-daily-pnl/SKILL.md) | `今天账户盈亏多少` |
| [order-ops](../skills/qmt-bridge-order-ops/SKILL.md) | `查今日委托和可撤单` |
| [kline-backfill](../skills/qmt-bridge-kline-backfill/SKILL.md) | `复盘前检查近3日两市成交额` |
| [return-analysis](../skills/qmt-bridge-return-analysis/SKILL.md) | `评估持仓涨幅概率并总结明日策略` |
| [market-watch](../skills/qmt-bridge-market-watch/SKILL.md) | `自选行情快照` |
| [sector-theme](../skills/qmt-bridge-sector-theme/SKILL.md) | `今天行业强弱怎么排` |
| [financial-download](../skills/qmt-bridge-financial-download/SKILL.md) | `下载财报到 Bridge 缓存` |
| [fundamental-screen](../skills/qmt-bridge-fundamental-screen/SKILL.md) | `按 ROE、EPS 做基本面筛选` |
| [technical-signal](../skills/qmt-bridge-technical-signal/SKILL.md) | `用 QMT 公式检查是否金叉` |
| [smart-execution](../skills/qmt-bridge-smart-execution/SKILL.md) | `预览这笔买单会不会涨跌停` |
| [rebalance](../skills/qmt-bridge-rebalance/SKILL.md) | `按目标权重生成调仓计划` |
| [credit-margin](../skills/qmt-bridge-credit-margin/SKILL.md) | `查两融保证金和担保品` |
| [realtime-monitor](../skills/qmt-bridge-realtime-monitor/SKILL.md) | `WebSocket 订阅实时行情` |
| [event-calendar](../skills/qmt-bridge-event-calendar/SKILL.md) | `今天是不是交易日` |
| [etf](../skills/qmt-bridge-etf/SKILL.md) | `查 ETF 列表和申赎清单` |
| [convertible](../skills/qmt-bridge-convertible/SKILL.md) | `可转债列表和条款快照` |
| [option](../skills/qmt-bridge-option/SKILL.md) | `查 510050 期权链` |
| [hk-connect](../skills/qmt-bridge-hk-connect/SKILL.md) | `港股通标的有哪些` |

更多变体见 [Agent Skills](agent-skills.md) 与 [skills/README.md](../skills/README.md)。写操作须确认后脚本才加 `--execute --confirm`。

## 4. 本机手动跑脚本（调试）

```bash
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py \
  --host 127.0.0.1 --port 8080 --api-key YOUR_KEY

python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key YOUR_KEY --feishu-md
```

Windows 中文乱码：`chcp 65001` 或 `$env:PYTHONIOENCODING='utf-8'`。

## 每日复盘定时调度

前台常驻，到点生成复盘并同步飞书（需 Bridge、QMT、`lark-cli auth`）：

```bat
scripts\daily_eval_scheduler.bat
scripts\daily_eval_scheduler.bat --run-now
scripts\daily_eval_scheduler.bat --run-now --skip-feishu
```

时间见 `.env` 中 `DAILY_EVAL_SCHEDULE_TIME`（默认每交易日 15:10）。日志：`logs/daily_eval_scheduler.log`。

复盘报告长什么样：[每日复盘报告示例](examples/daily-eval-report.md)。
