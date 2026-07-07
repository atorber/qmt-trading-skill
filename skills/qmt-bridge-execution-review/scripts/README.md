# execution-review 脚本

## 单账户

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md
```

默认飞书 Markdown：`reports/feishu_daily_eval.md`

## 全账户综合（普通户 + 信用户）

```bash
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md
```

默认飞书 Markdown：`reports/feishu_combined_daily_eval.md`

需在 `.env` 配置 `QMT_BRIDGE_STOCK_ACCOUNT_ID` / `QMT_BRIDGE_CREDIT_ACCOUNT_ID`（或等价变量）。

## 共用说明

- `--json` 的 `operation_evaluation` 含 `no_trade_total_pnl`、`op_alpha_total_pnl` 及分标的 `no_trade_pnl` / `op_alpha_pnl`
- `--feishu-md` 第五节含 **基线对比** 与 **不操作少赚/多亏明细** 表
- 默认自动拉取当日两市成交额与近 3 日量能热度（`market_turnover_util`）；可用 `--market-turnover-yi` 覆盖。历史缺口见 `qmt-bridge-kline-backfill`
