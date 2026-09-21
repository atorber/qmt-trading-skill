# execution-review 脚本

## 单账户

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --host 127.0.0.1 --port 8080 --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --json --api-key KEY
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py --feishu-md
```

默认：`--eval-mode=evidence` → `reports/daily_eval_evidence.json` + `reports/feishu_daily_eval.md`（一～六客观，七专家占位）。

## 全账户综合

```bash
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py --feishu-md
```

证据包：`reports/combined_daily_eval_evidence.json`；MD：`reports/feishu_combined_daily_eval.md`。

## 参数

| 参数 | 说明 |
|------|------|
| `--eval-mode evidence\|rules` | 默认 evidence；rules=旧模板评语 |
| `--evidence-json [PATH]` | 证据包路径 |
| `--feishu-md` | 客观 Markdown |
| `--json` | stdout（含 `rule_tags`、`score_hints`） |

专家第七节：Agent 读 evidence，按 `references/expert-review-protocol.md` 写入 `feishu_*_expert.md` 后合并。

## 定时调度

```bash
python scripts/daily_eval_scheduler.py
python scripts/daily_eval_scheduler.py --run-now
```

Windows：`scripts\daily_eval_scheduler.bat`。
