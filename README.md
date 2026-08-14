# QMT Trading Skill

> 在 Cursor / Claude Code 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API 与 `qmt-server` 在 qmt-bridge。

**在线文档**：[GitHub Pages](https://atorber.github.io/qmt-trading-skill/) · [快速开始](docs/getting-started.md) · [Agent Skills](docs/agent-skills.md) · [skills/README.md](skills/README.md)

## 使用

1. Windows 上启动 Bridge：`qmt-server --port 8080 --trading`（见 [qmt-bridge](https://github.com/atorber/qmt-bridge)）
2. 克隆本仓并安装：

```powershell
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install -e ".\vendor\qmt-bridge"
pip install -e ".[dev]"
cp .env.example .env
```

3. `.env` 配置 `QMT_BRIDGE_HOST=127.0.0.1`、`QMT_BRIDGE_PORT`、`QMT_BRIDGE_API_KEY`
4. 对话中说「今天账户盈亏多少」，或 `@skills/qmt-bridge-daily-pnl/SKILL.md`

## 开发（对照并修改 Bridge）

`vendor/qmt-bridge` 为 Git submodule。改 Bridge 后先在子模块提交推送，再 `git add vendor/qmt-bridge` 更新指针。打开 `qmt-trading-skill.code-workspace` 可同时浏览两仓。

## 许可

[MIT](LICENSE)
