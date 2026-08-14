# QMT Trading Skill

> 在 Cursor / Claude Code 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API、`qmt-server`、`QMTClient` 在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。

**在线文档**：[GitHub Pages](https://atorber.github.io/qmt-trading-skill/) · [快速开始](docs/getting-started.md) · [Agent Skills](docs/agent-skills.md) · [skills/README.md](skills/README.md)

## 仓库拆分（升级说明）

原先 **API 服务** 与 **Agent Skills** 在同一个 Git 仓库里。现已拆成两个仓库，职责如下：

| 仓库 | 内容 | 文档 |
|------|------|------|
| [atorber/qmt-bridge](https://github.com/atorber/qmt-bridge) | `qmt-server`、REST/WebSocket、`QMTClient`、PyPI 包 **`qmt-bridge-pro`** | [atorber.github.io/qmt-bridge](https://atorber.github.io/qmt-bridge/) |
| **本仓库** [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | `skills/`、复盘调度、Skill 文档 | [atorber.github.io/qmt-trading-skill](https://atorber.github.io/qmt-trading-skill/) |

对已有用户的影响：

1. **不能再只克隆一个仓就同时跑服务端和 Skills。** 先在 Windows（与 QMT 同机）按 Bridge 文档启动 `qmt-server`，再在本仓跑 Agent / 脚本。
2. **本仓不再提供** `qmt-server`、`scripts/pm2-start.bat`、`ecosystem.config.cjs`、Streamlit 仪表盘。长期守护 API 请到 **qmt-bridge** 使用 PM2。
3. **PyPI 包名**：`pip install qmt-bridge-pro`（导入仍是 `qmt_bridge`）。Skills 运行时依赖 `qmt-bridge-pro>=2.10.1`；开发建议 `pip install -e ./vendor/qmt-bridge`（Git submodule）。
4. **克隆须带子模块**：`git clone --recurse-submodules ...`。已克隆过的目录执行 `git submodule update --init --recursive`。
5. **`.env` 拆成两份**：Bridge 仓配置监听地址（可为 `0.0.0.0`）、交易开关、miniQMT 路径；本仓只配**客户端连接**（`QMT_BRIDGE_HOST=127.0.0.1` 或 Windows 局域网 IP，**不要用 `0.0.0.0`**），端口和 API Key 须与 Bridge 实际监听一致。
6. **旧书签**：REST / `QMTClient` 文档改看 Bridge Pages；自然语言工作流改看本仓 Pages。若你本地目录仍叫 `qmt-bridge` 但远程是 Skill 仓，请按上面两个 URL 重新认领仓库。

对话用法（「今天账户盈亏多少」等）不变，脚本仍在 `skills/*/scripts/`。

## 使用

1. Windows 上启动 Bridge：`qmt-server --port 8080 --trading`（见 [qmt-bridge](https://github.com/atorber/qmt-bridge)）
2. 克隆本仓并安装：

```powershell
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install qmt-bridge-pro
pip install -e ".[dev]"
cp .env.example .env
```

开发对照 Bridge 源码时用 `pip install -e ".\vendor\qmt-bridge"` 代替上一行 PyPI 安装。

3. `.env` 配置 `QMT_BRIDGE_HOST=127.0.0.1`、`QMT_BRIDGE_PORT`、`QMT_BRIDGE_API_KEY`
4. 对话中说「今天账户盈亏多少」，或 `@skills/qmt-bridge-daily-pnl/SKILL.md`

## 开发（对照并修改 Bridge）

`vendor/qmt-bridge` 为 Git submodule。改 Bridge 后先在子模块提交推送，再 `git add vendor/qmt-bridge` 更新指针。打开 `qmt-trading-skill.code-workspace` 可同时浏览两仓。

## 许可

[MIT](LICENSE)
