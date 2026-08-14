# CLAUDE.md — QMT Trading Skill

Agent Skills 仓库。运行时通过 HTTP 调用 **QMT Bridge**（`C:\GitHub\qmt-bridge` 或 `pip install qmt-bridge`）。

- 禁止 `import qmt_bridge.server`
- 账户解析用 `qmt_bridge.accounts`
- 客户端用 `from qmt_bridge import QMTClient`

改 Bridge 协议时到并列目录 `../qmt-bridge` 修改，并 `pip install -e ../qmt-bridge`。
