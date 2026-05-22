# 开发指南

**QMT Trading Skill** = QMT Bridge（`qmt-server` / `QMTClient`）+ `skills/` 脚本。常用命令均在仓库根目录执行。人类使用 Agent Skill 时**优先自然语言 + `@skills/.../SKILL.md`**，由 Agent 调用 `skills/*/scripts/*.py`；本节命令主要供开发与 Agent 终端参考。

## 安装与依赖

```bash
pip install -e .                              # 客户端
pip install -e ".[full]"                      # 服务端
pip install -e ".[full,docs,dashboard]"       # 全部
```

## 服务与数据

```bash
qmt-server --port 8080 --trading              # 启动 API（示例参数见 .env）
qmt-scheduler                                 # 定时下载（独立进程）
python scripts/download_all.py              # 全量历史 + 财务
python scripts/download_all.py --periods 1m --skip-financial
```

## Agent Skills（脚本路径）

均需 Bridge 已运行；交易类需 `.env` 中 `QMT_BRIDGE_API_KEY`。连接请用 **`127.0.0.1`**，不要用 `0.0.0.0`。

```bash
python skills/qmt-bridge-trading/scripts/trading_status.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
python skills/qmt-bridge-daily-pnl/scripts/daily_pnl_snapshot.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key YOUR_KEY
# 飞书：见 skills/qmt-bridge-feishu-doc/SKILL.md（lark-cli，无 scripts/ 封装）
```

完整列表与**提示词示例**见 [skills/README.md](../skills/README.md)、[Agent Skills](agent-skills.md)。

写操作（下单、撤单、下载财报等）须用户确认，脚本加 `--execute --confirm`。

## 文档、测试与构建

```bash
mkdocs serve -a 127.0.0.1:8001              # 文档站点预览
mkdocs build -d site/
streamlit run dashboard/app.py                # 仪表盘 :8501
python -m pytest tests/ -q                    # 契约测试（无需 QMT）
python -m ruff format src/ tests/             # 格式化
python -m ruff check src/ tests/              # lint
python -m build                               # wheel
```

联调测试（需已启动 Bridge）：

```bash
# PowerShell
$env:QMT_BRIDGE_LIVE = "1"; python -m pytest tests/live -m live -v
```

## 飞书报告（可选）

使用 [qmt-bridge-feishu-doc](../skills/qmt-bridge-feishu-doc/SKILL.md) + 官方 [lark-cli](https://github.com/larksuite/cli)：

```bash
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
```

上传复盘：`lark-cli docs +update --api-version v2 --doc TOKEN --command overwrite --content @reports/feishu_daily_eval.md`（详见 Skill 内 workflow）。勿使用已移除的 `scripts/*feishu*` 脚本。
