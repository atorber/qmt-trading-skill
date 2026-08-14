# 快速开始

本仓库是 **Agent Skills** 层：在 Cursor 里用自然语言驱动脚本，通过 HTTP 调用已启动的 **QMT Bridge**。Bridge 的安装与 `qmt-server` 见 [qmt-bridge](https://github.com/atorber/qmt-bridge)。

## 架构

```
Mac / Linux / Windows（主力机 · 本仓库）     Windows（中转站）
┌──────────────────────┐                ┌─────────────────────────┐
│ Cursor / Claude      │   HTTP/WS     │  QMT 客户端（登录中）      │
│ @skills/.../SKILL.md │ ◄───────────► │  qmt-server (qmt-bridge) │
│ 分析 / 本地报告       │   局域网       │  xtquant                 │
└──────────────────────┘                └─────────────────────────┘
```

## 1. 启动 Bridge（Windows，QMT 同机）

1. QMT 勾选「独立交易」登录并保持运行。
2. 在 [qmt-bridge](https://github.com/atorber/qmt-bridge) 仓库：

```bash
pip install -e ".[full]"
qmt-server --port 8080 --trading --api-key your-secret-key \
  --mini-qmt-path "C:\你的QMT路径\userdata_mini" \
  --stock-account-id 普通账户ID --credit-account-id 信用账户ID
```

验证：`http://127.0.0.1:8080/docs` 或 `GET /api/meta/health`。

## 2. 安装本仓库（主力机）

```bash
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install -e "./vendor/qmt-bridge"
pip install -e ".[dev]"
cp .env.example .env
```

编辑 `.env`：`QMT_BRIDGE_HOST` / `QMT_BRIDGE_PORT` / `QMT_BRIDGE_API_KEY` 须与 Bridge 一致。

!!! tip "客户端地址"
    服务端可监听 `0.0.0.0`；**Skill 脚本请连接 `127.0.0.1` 或 Windows 局域网 IP**，不要把 `0.0.0.0` 当作 HTTP 目标。

## 3. 在 Cursor 中使用

**自然语言**（推荐），例如：

- `今天账户盈亏多少`
- `生成今日交易复盘`
- `把复盘同步到飞书`

**@ Skill 文件**：`@skills/qmt-bridge-execution-review/SKILL.md`

完整提示词见 [Agent Skills](agent-skills.md) 与 [skills/README.md](../skills/README.md)。写操作须确认后脚本才加 `--execute --confirm`。

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
