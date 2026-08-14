# QMT Trading Skill

> 在 Cursor / Claude Code 中用**自然语言**完成 A 股行情、交易、当日盈亏、复盘与飞书同步。底层通过独立仓库 **[QMT Bridge](https://github.com/atorber/qmt-bridge)** 对接 miniQMT。

原先与 QMT Bridge 同仓，现已拆出：本仓只有 Skills，API 在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。影响说明见 [仓库 README](https://github.com/atorber/qmt-trading-skill#仓库拆分升级说明)。

**在线文档**：[QMT Trading Skill（GitHub Pages）](https://atorber.github.io/qmt-trading-skill/)

```
主力机（本仓库）                            Windows（QMT Bridge）
┌──────────────────────┐                ┌─────────────────────────┐
│ Cursor / Agent       │   HTTP/WS     │  miniQMT 客户端（登录中）  │
│ skills/*/scripts     │ ◄───────────► │  qmt-server              │
└──────────────────────┘   局域网       └─────────────────────────┘
```

## 文档

| 文档 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 安装 Skill、连接 Bridge、对话用法 |
| [配置参考](configuration.md) | Skill 侧环境变量（连接 Bridge） |
| [开发指南](development.md) | 脚本路径、测试、飞书、submodule |
| [Agent Skills](agent-skills.md) | 全部 Skill 与提示词 |
| [每日复盘示例](examples/daily-eval-report.md) | 复盘 Markdown 结构（金额已脱敏） |
| [QMT Bridge 文档](https://atorber.github.io/qmt-bridge/) | HTTP/WS API、`qmt-server` 启动 |

## 安装

```bash
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
cd qmt-trading-skill
pip install qmt-bridge-pro
pip install -e ".[dev]"
cp .env.example .env
```

开发对照源码：`pip install -e "./vendor/qmt-bridge"`。导入仍为 `from qmt_bridge import QMTClient`。

Windows 上须先启动 Bridge，见 [qmt-bridge 快速开始](https://github.com/atorber/qmt-bridge/blob/main/docs/getting-started.md)。
