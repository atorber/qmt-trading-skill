# execution-review 脚本

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY --feishu-md
```

默认自动拉取当日两市成交额与近 3 日量能热度（`market_turnover_util`：tick + 本地缓存）；可用 `--market-turnover-yi` 覆盖当日数值。历史缺口见 `qmt-bridge-kline-backfill`。
