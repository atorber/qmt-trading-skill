---
name: qmt-bridge-kline-backfill
description: >-
  校验近N个交易日两市成交额（上证+深证）是否可用于复盘。默认仅用 get_full_tick 写当日
  与本地日缓存，不拉历史 K 线。用户提到补齐K线、近3日量能缺失、复盘前校验时使用。
---

# QMT Trading Skill · 近3日量能校验

> **实现状态**：✅ `index_turnover_recent.py` · `backfill_recent_index_kline.py`  
> 共享逻辑：`_shared/market_turnover_util.py`

## 目标

在执行复盘前，校验近 N 日（默认 3）两市成交额是否齐全：

- 上证指数：`000001.SH`
- 深市指数：`399106.SZ`（tick 缺 amount 时回退 `399001.SZ`）

## 官方推荐 vs 本项目策略

迅投知识库（[指数数据](http://dict.thinktrader.net/dictionary/indexes.html)）：

| 场景 | 官方 API | 本项目复盘热路径 |
|------|----------|------------------|
| **当日成交额** | `get_full_tick` → `amount` | ✅ `GET /api/market/full_tick` |
| **历史指数日 K** | `download_history_data` + `get_market_data_ex` | ❌ 禁用（易 BSON 崩溃） |
| **历史缺口** | 需本地已下载数据 | ✅ `reports/market_turnover_daily.json` 每日 tick 累积 |

复盘/校验**默认不调用** `download_batch`、`get_local_data`、`get_market_data_ex`、`get_market_data`。

可选 `--try-history`：先 `download_batch` 指数日线，再 `get_market_data` 子进程补历史并写入缓存（QMT 异常时慎用）。

**推荐补齐近 3 日缺口**（历史缺失时）：

```bash
# 1. 下载指数日线（仅 3 只，勿全市场）
python -c "
from datetime import date, timedelta
import sys; sys.path.insert(0,'skills/_shared')
from common import load_env_files, make_client
import argparse
load_env_files()
c,_=make_client(argparse.Namespace(host='127.0.0.1',port=8080,api_key='test-auto',account_id=None),False)
e=date.today().strftime('%Y%m%d'); s=(date.today()-timedelta(days=12)).strftime('%Y%m%d')
print(c.download_batch(['000001.SH','399106.SZ','399001.SZ'], period='1d', start_time=s, end_time=e))
"

# 2. 读 amount 写入缓存并展示明细
python skills/qmt-bridge-kline-backfill/scripts/index_turnover_recent.py \
  --host 127.0.0.1 --port 8080 --try-history
```

## 脚本

```bash
# 查看近3日上证+深证成交额明细（亿元）
python skills/qmt-bridge-kline-backfill/scripts/index_turnover_recent.py \
  --host 127.0.0.1 --port 8080

# 查看近3日成交额明细；历史缺口加 --try-history
python skills/qmt-bridge-kline-backfill/scripts/index_turnover_recent.py \
  --host 127.0.0.1 --port 8080

# 可选：尝试从本地 K 线补历史（慎用，优先用上一条）
python skills/qmt-bridge-kline-backfill/scripts/index_turnover_recent.py \
  --try-history --host 127.0.0.1 --port 8080

# 兼容旧入口（同上逻辑）
python skills/qmt-bridge-kline-backfill/scripts/backfill_recent_index_kline.py --json
```

## 参数

| 参数 | 说明 |
|------|------|
| `--days` | 需要覆盖的最近交易日数量（默认 3） |
| `--try-history` | 可选尝试 `get_market_data` 补历史（默认关闭） |
| `--json` | 输出机器可读结果 |

## 输出说明

- `ok=true`：近 N 个交易日缓存/tick 均有沪+深成交额
- `ok=false`：列出缺失交易日；连续多日收盘复盘会自动写入缓存
- `method`：默认 `full_tick+cache`

## 排障

1. 当日 tick 失败 → 检查 QMT 登录与行情
2. 历史不足 → 正常（需多日累积）；勿反复跑 `--try-history`
3. BSON / 服务无响应 → **重启 QMT 客户端**，再重启 Bridge
