# Agent Skills

本目录包含与 **QMT Bridge** 配套的 [Agent Skills](https://docs.cursor.com/context/skills)。**21 个 Skill** 均已提供可执行脚本（见 [ROADMAP.md](ROADMAP.md)）。

在线文档：[Agent Skills](../docs/agent-skills.md)

## 怎么用（推荐）

1. **自然语言**：在 Cursor / Claude 对话中直接说下面表格「提示词示例」里的句子（可改股票代码、数量）。
2. **@ Skill 文件**：`@skills/qmt-bridge-daily-pnl/SKILL.md` 等，让 Agent 读取规程后执行对应 `scripts/*.py`。
3. **命令行**（可选）：各 Skill 的 `SKILL.md` 中有 `python skills/.../scripts/....py` 示例；Agent 自动执行时无需人工敲命令。

提示词与各 Skill 的 `description` 触发语一致；写操作（下单、撤单、调仓、下载财报）须你确认后加 `--execute --confirm`。

## 全部 Skills

| Skill | 说明 | 提示词示例 |
|-------|------|------------|
| [qmt-bridge-trading](qmt-bridge-trading/SKILL.md) | 下单、清仓、状态 | `帮我查持仓和可用资金` · `用 Bridge 下一笔买入（先预览）` · `清仓某只股票` |
| [qmt-bridge-execution-review](qmt-bridge-execution-review/SKILL.md) | 当日复盘/操作评价 | `今日操作评估` · `交易复盘+执行质量` · `评价今天买卖是否合理` |
| [qmt-bridge-feishu-doc](qmt-bridge-feishu-doc/SKILL.md) | 上传报告到飞书 | `把今日复盘同步到飞书` · `上传涨跌分析到飞书文档` |
| [qmt-bridge-portfolio-risk](qmt-bridge-portfolio-risk/SKILL.md) | 组合风险 | `组合风险快照` · `持仓集中度是否过高` · `下单前现金够不够、有没有 T+1` |
| [qmt-bridge-daily-pnl](qmt-bridge-daily-pnl/SKILL.md) | 当日盈亏 | `今天账户盈亏多少` · `分标的列当日盈亏表` · `包含今天买卖和已清仓的盈亏` |
| [qmt-bridge-order-ops](qmt-bridge-order-ops/SKILL.md) | 查单、撤单 | `查今日委托和可撤单` · `撤销 order_id 为 xxx 的委托` |
| [qmt-bridge-return-analysis](qmt-bridge-return-analysis/SKILL.md) | 累计涨幅/涨跌概率 | `评估持仓涨幅概率并总结明日策略` · `1/5/10/30日阶段强弱` · `量价形态次日统计` |
| [qmt-bridge-market-watch](qmt-bridge-market-watch/SKILL.md) | 自选快照 | `自选行情快照` · `盘前看下指数和自选涨跌` |
| [qmt-bridge-sector-theme](qmt-bridge-sector-theme/SKILL.md) | 板块排序 | `板块内涨幅排名` · `今天行业强弱怎么排` |
| [qmt-bridge-financial-download](qmt-bridge-financial-download/SKILL.md) | 下载财报 | `下载财报到 Bridge 缓存` · `补全这几只股票的财务数据` |
| [qmt-bridge-fundamental-screen](qmt-bridge-fundamental-screen/SKILL.md) | 财报筛选 | `按 ROE、EPS 做基本面筛选` · `财报排雷` |
| [qmt-bridge-technical-signal](qmt-bridge-technical-signal/SKILL.md) | 公式检查 | `用 QMT 公式检查是否金叉` · `列出可用指标/公式` |
| [qmt-bridge-smart-execution](qmt-bridge-smart-execution/SKILL.md) | 下单预览 | `预览这笔买单会不会涨跌停` · `限价还是市价更合适` |
| [qmt-bridge-rebalance](qmt-bridge-rebalance/SKILL.md) | 再平衡 | `按目标权重生成调仓计划` · `组合再平衡要买卖多少` |
| [qmt-bridge-credit-margin](qmt-bridge-credit-margin/SKILL.md) | 两融快照 | `查两融保证金和担保品` |
| [qmt-bridge-realtime-monitor](qmt-bridge-realtime-monitor/SKILL.md) | WS 示例 | `WebSocket 订阅实时行情` · `盘中推送成交回报` |
| [qmt-bridge-event-calendar](qmt-bridge-event-calendar/SKILL.md) | 交易日历 | `今天是不是交易日` · `下一个交易日是哪天` |
| [qmt-bridge-etf](qmt-bridge-etf/SKILL.md) | ETF | `查 ETF 列表和申赎清单` |
| [qmt-bridge-convertible](qmt-bridge-convertible/SKILL.md) | 可转债 | `可转债列表和条款快照` |
| [qmt-bridge-option](qmt-bridge-option/SKILL.md) | 期权链 | `查 510050 期权链` · `认沽认购合约有哪些` |
| [qmt-bridge-hk-connect](qmt-bridge-hk-connect/SKILL.md) | 港股通 | `港股通标的有哪些` · `沪港通深港通名单` |

## 推荐工作流

```
calendar → watchlist / sector-rank
    → download-financial → fundamental-screen
    → return-analysis / watchlist → portfolio-risk → daily-pnl → execution-preview → trading → order-ops → daily-report → feishu-doc
```

## 连接与编码

- **端口**：以 `.env` 中 `QMT_BRIDGE_PORT` 为准；常用 8080 时请显式 `--port 8080`
- **客户端地址**：脚本连接请用 `127.0.0.1`，不要用 `0.0.0.0`
- **Windows 中文乱码**：`chcp 65001` 或 `PYTHONIOENCODING=utf-8`

## 共享模块

[`_shared/common.py`](_shared/common.py) · [`kline_util.py`](_shared/kline_util.py) · [`financial_util.py`](_shared/financial_util.py) · [`positions_util.py`](_shared/positions_util.py) · [`stock_names.py`](_shared/stock_names.py) · [`trading_fmt.py`](_shared/trading_fmt.py) · [`orders_util.py`](_shared/orders_util.py) · [`pnl_util.py`](_shared/pnl_util.py) · [`pnl_display.py`](_shared/pnl_display.py) · [`table_fmt.py`](_shared/table_fmt.py) · [`feishu_doc.py`](_shared/feishu_doc.py)

## Cursor 启用

```bash
mkdir -p .cursor/skills
for d in skills/qmt-bridge-*/; do
  name=$(basename "$d")
  ln -sf "../../skills/$name" ".cursor/skills/$name"
done
```

## 前置条件

- Bridge 已启动；交易脚本需 `QMT_BRIDGE_API_KEY` 与 Bridge 侧 `--trading`
- 写操作须用户确认；交易类脚本加 `--execute --confirm`

## 测试

```bash
pytest tests/test_skills_smoke.py -q
```
