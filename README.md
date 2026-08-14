# QMT Trading Skill

> 在 Cursor / Claude Code 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API 与 `qmt-server` 在 `qmt-bridge`。

## 开发（对照并修改 Bridge）

本仓已嵌套 `vendor/qmt-bridge`（Git submodule）。改 Bridge 后先在子模块里提交推送，再更新本仓指针。

```powershell
cd C:\GitHub\qmt-trading-skill
git submodule update --init --recursive
pip install -e ".\vendor\qmt-bridge"
pip install -e ".[dev]"
```

也可以继续用并列目录 `C:\GitHub\qmt-bridge`（与 submodule 是同一远程）。打开 `qmt-trading-skill.code-workspace` 可同时浏览两仓。

## 使用

1. Windows 上启动 Bridge：`qmt-server --port 8080 --trading`（见 qmt-bridge 文档）
2. 本机 `.env` 配置 `QMT_BRIDGE_HOST` / `QMT_BRIDGE_PORT` / `QMT_BRIDGE_API_KEY`
3. 对话中直接说「今天账户盈亏多少」，或 `@skills/qmt-bridge-daily-pnl/SKILL.md`

Skill 列表见 [skills/README.md](skills/README.md)。

## 许可

[MIT](LICENSE)
