# QMT Trading Skill

> 在 Cursor / Claude Code / **豆包工作** / **WorkBuddy** 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

本仓库只含 **Agent Skills**（`skills/`）。HTTP API、`qmt-server`、`QMTClient` 在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。

```
主力机（本仓库 · Skills）                    Windows（QMT Bridge）
┌──────────────────────┐                ┌─────────────────────────┐
│ Cursor / 豆包 / WorkBuddy │  HTTP/WS   │  miniQMT 客户端（登录中）  │
│ skills/*/scripts     │ ◄───────────► │  qmt-server              │
└──────────────────────┘   局域网       └─────────────────────────┘
```

## 仓库职责

| 仓库 | 内容 | 文档 |
|------|------|------|
| [atorber/qmt-bridge](https://github.com/atorber/qmt-bridge) | `qmt-server`、REST/WebSocket、`QMTClient`、PyPI 包 **`qmt-bridge-pro`**；长期守护用 PM2 | [atorber.github.io/qmt-bridge](https://atorber.github.io/qmt-bridge/) |
| **本仓库** [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | `skills/`、复盘调度、Skill 文档 | 本文档站 |

配置分两边：**Bridge** 配监听 / 交易开关 / miniQMT；**本仓 `.env`** 只配客户端连接（`QMT_BRIDGE_HOST=127.0.0.1`，不要用 `0.0.0.0`）。

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 安装 Skills → 检测/启动 Bridge → 典型提示词 |
| [配置参考](configuration.md) | Skill 侧环境变量（连接 Bridge） |
| [开发指南](development.md) | 脚本路径、测试、飞书、submodule |
| [Agent Skills](agent-skills.md) | 全部 23 个 Skill 与提示词 |
| [每日复盘示例](examples/daily-eval-report.md) | 复盘 Markdown 结构（金额已脱敏） |
| [QMT Bridge 文档](https://atorber.github.io/qmt-bridge/) | HTTP/WS API、`qmt-server` 启动 |

## 三步上手

1. **安装本仓全部 Skills**（豆包工作 / WorkBuddy 一键提示词，或 `npx skills add atorber/qmt-trading-skill -g -y`）
2. **检测 Bridge**：已启动则跳过；未启动再安装/启动（见 [qmt-bridge-setup](../skills/qmt-bridge-setup/SKILL.md)）
3. **自然语言使用**，例如 `今天账户盈亏多少`

已安装用户升级：见 [快速开始 · 更新已安装的 Skills](getting-started.md#更新已安装的-skills)；包版本 [`skills/VERSION`](../skills/VERSION)。

详情见 [快速开始](getting-started.md)。
