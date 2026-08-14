# 开发指南

本仓库只含 **Agent Skills**。HTTP API 实现在 [qmt-bridge](https://github.com/atorber/qmt-bridge)。人类使用时优先**自然语言 + `@skills/.../SKILL.md`**；下列命令供开发与调试。

## 安装

```bash
git clone --recurse-submodules https://github.com/atorber/qmt-trading-skill.git
# 或已有目录：
git submodule update --init --recursive
pip install -e "./vendor/qmt-bridge"
pip install -e ".[dev,docs]"
```

改 Bridge 源码：在 `vendor/qmt-bridge` 提交并推送后，回到本仓 `git add vendor/qmt-bridge` 更新指针。也可 `pip install -e ../qmt-bridge` 指向并列检出。

禁止 `import qmt_bridge.server`。账户解析用 `qmt_bridge.accounts`，HTTP 用 `QMTClient`。

## Agent 脚本路径

均需 Bridge 已运行；交易类需 `QMT_BRIDGE_API_KEY`。连接用 **`127.0.0.1`**。

```bash
python skills/qmt-bridge-trading/scripts/trading_status.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
```

完整列表与提示词：[skills/README.md](../skills/README.md)、[Agent Skills](agent-skills.md)。写操作须 `--execute --confirm`。

## 文档与测试

```bash
mkdocs serve -a 127.0.0.1:8001
python -m pytest tests/ -q
```

## 飞书报告（可选）

使用 [qmt-bridge-feishu-doc](../skills/qmt-bridge-feishu-doc/SKILL.md) + [lark-cli](https://github.com/larksuite/cli)：

```bash
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
```

上传复盘：`lark-cli docs +update --api-version v2 --doc TOKEN --command overwrite --content @reports/feishu_daily_eval.md`（见 Skill 内 workflow）。
