# QMT Trading Skill

> 在 Cursor / Claude Code 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API 与 `qmt-server` 在 `qmt-bridge`。

## 开发（对照并修改 Bridge）

本地并列检出，可编辑安装后改 Bridge 立即生效：

```powershell
# 已有 C:\GitHub\qmt-bridge 与本仓库时
cd C:\GitHub\qmt-trading-skill
pip install -e "..\qmt-bridge"
pip install -e ".[dev]"
```

用多根工作区同时打开两仓：打开 `qmt-trading-skill.code-workspace`。

独立 GitHub 仓建好后，可再加 submodule（把 Bridge commit 锁进本仓）：

```powershell
git submodule add https://github.com/atorber/qmt-bridge.git vendor/qmt-bridge
pip install -e ".\vendor\qmt-bridge"
```

> 注意：历史上 `github.com/atorber/qmt-bridge` 曾重定向到本仓库。请先在 GitHub **新建空仓库**（不要沿用旧重定向），再把 `C:\GitHub\qmt-bridge` 推上去，然后执行上面的 `submodule add`。

## 使用

1. Windows 上启动 Bridge：`qmt-server --port 8080 --trading`（见 qmt-bridge 文档）
2. 本机 `.env` 配置 `QMT_BRIDGE_HOST` / `QMT_BRIDGE_PORT` / `QMT_BRIDGE_API_KEY`
3. 对话中直接说「今天账户盈亏多少」，或 `@skills/qmt-bridge-daily-pnl/SKILL.md`

Skill 列表见 [skills/README.md](skills/README.md)。

## 许可

[MIT](LICENSE)
