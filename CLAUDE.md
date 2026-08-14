# CLAUDE.md — QMT Trading Skill

Agent Skills 仓库。运行时通过 HTTP 调用 **QMT Bridge**（独立仓库，见 README「仓库拆分」）。

- 禁止 `import qmt_bridge.server`
- 账户解析用 `qmt_bridge.accounts`
- 客户端用 `from qmt_bridge import QMTClient`
- 介绍与用法见 `docs/getting-started.md`、`docs/agent-skills.md`
- 本仓无 `qmt-server` / PM2；API 守护在 GitHub 仓 qmt-bridge
- 运行时 PyPI 包：`pip install qmt-bridge-pro`（import 仍为 `qmt_bridge`）

改 Bridge：`vendor/qmt-bridge` 或并列目录 `../qmt-bridge`，`pip install -e` 后生效。
