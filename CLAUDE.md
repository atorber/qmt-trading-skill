# CLAUDE.md — QMT Trading Skill

Agent Skills 仓库。运行时通过 HTTP 调用 **QMT Bridge**。

- 禁止 `import qmt_bridge.server`
- 账户解析用 `qmt_bridge.accounts`
- 客户端用 `from qmt_bridge import QMTClient`
- 介绍与用法见 `docs/getting-started.md`、`docs/agent-skills.md`

改 Bridge：`vendor/qmt-bridge` 或并列目录 `../qmt-bridge`，`pip install -e` 后生效。
