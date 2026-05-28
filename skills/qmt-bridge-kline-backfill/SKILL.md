---
name: qmt-bridge-kline-backfill
description: >-
  补齐并校验近N个交易日指数日K（000001.SH、399106.SZ/399001.SZ）缓存，
  用于复盘前确保量能序列可用。用户提到补齐K线、近3日数据缺失、复盘前先下载时使用。
---

# QMT Trading Skill · 近3日K线补齐

> **实现状态**：✅ `backfill_recent_index_kline.py`

## 目标

在执行复盘前，先对关键指数日K进行“下载 + 校验”：

- 上证指数：`000001.SH`
- 深市指数：`399106.SZ`（缺失时回退 `399001.SZ`）

确保近 N 日（默认 3）有可用数据，避免复盘出现“近3日历史不足”。

## 脚本

```bash
# 默认补齐近3日，下载后立刻校验
python skills/qmt-bridge-kline-backfill/scripts/backfill_recent_index_kline.py \
  --host 127.0.0.1 --port 8080

# 指定检查近5日
python skills/qmt-bridge-kline-backfill/scripts/backfill_recent_index_kline.py \
  --days 5 --host 127.0.0.1 --port 8080

# 输出JSON
python skills/qmt-bridge-kline-backfill/scripts/backfill_recent_index_kline.py \
  --json
```

## 参数

| 参数 | 说明 |
|------|------|
| `--days` | 需要覆盖的最近交易日数量（默认 3） |
| `--lookback` | 下载回看自然日窗口（默认 45） |
| `--json` | 输出机器可读结果 |

## 输出说明

- `ok=true`：近 N 日沪深指数日K均可用（按 amount>0 判定）
- `ok=false`：仍有缺失，会列出缺失交易日和缺失侧（沪/深）

> 本 Skill 只负责数据补齐与诊断，不做交易建议。

## 推荐用法

在“今日复盘”前先执行一次本 Skill；若仍缺失，优先排查：

1. QMT 客户端是否登录并行情正常
2. Bridge 服务是否连接正确端口
3. 数据源当日是否存在停牌/未更新异常
