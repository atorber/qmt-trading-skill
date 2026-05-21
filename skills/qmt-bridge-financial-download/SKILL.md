---
name: qmt-bridge-financial-download
description: >-
  通过 QMT Bridge 将财报下载到服务端缓存（POST）。在用户提到下载财报、补财务数据、
  刷新 Pershareindex、下载 ROE 数据、财报缓存时使用；筛选指标请用 fundamental-screen。
---

# QMT Bridge 财报下载 Skill

> **实现状态**：✅ `download_financial_data.py`

## 目标

向 Bridge 服务端 **写入** 财务数据缓存，供后续 `GET /api/financial/data` 或 [fundamental-screen](../qmt-bridge-fundamental-screen/SKILL.md) 使用。

## 何时用本 Skill（而非筛选 Skill）

| 场景 | 使用 |
|------|------|
| 用户明确要「下载/补全/刷新」财报 | **本 Skill** |
| 批量标的、指定表、下载后验证 | **本 Skill** |
| 按 ROE/EPS 等指标筛选 | [fundamental-screen](../qmt-bridge-fundamental-screen/SKILL.md) |
| 筛选时偶发缺数 | 筛选脚本默认 `--if-missing`；大批量仍建议先本 Skill |

## 脚本

```bash
# 下载每股指标表（默认 Pershareindex）
python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
  --host HOST --port PORT \\
  --codes 600584.SH,603986.SH --table Pershareindex

# 下载后验证缓存是否有数据
python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
  --codes 600584.SH --verify --wait 8

# 下载全部财务表（较慢，勿对全市场使用）
python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
  --codes 600519.SH --all-tables --verify
```

`python skills/qmt-bridge-financial-download/scripts/download_financial_data.py` 与上述参数相同。

## 推荐流程（Agent）

```
1. 确认用户给出的股票列表（勿擅自扩大为全市场）
2. 说明：下载会写服务端缓存，可能耗时数秒～数十秒
3. 运行 download_financial_data.py，建议加 --verify
4. 若有仍无数据的代码：加大 --wait、检查 QMT 是否登录、或换表名
5. 需要筛选时，再运行 fundamental-screen 的 screen_financial.py
```

## 主要参数

| 参数 | 说明 |
|------|------|
| `--codes` | 必填，逗号分隔 |
| `--table` | 默认 `Pershareindex` |
| `--all-tables` | 下载全部表（慢） |
| `--start-time` / `--end-time` | 可选 YYYYMMDD |
| `--wait` | 下载后等待秒数（默认 5） |
| `--verify` | 等待后查询缓存；仍缺数时自动再等一轮（最多 `--wait` 秒） |
| `--json` | JSON 输出 |

## 常用财务表

| 表名 | 含义 |
|------|------|
| `Pershareindex` | 每股指标（ROE、EPS 等） |
| `Income` | 利润表 |
| `Balance` | 资产负债表 |
| `CashFlow` | 现金流量表 |

## API

| 操作 | 路径 |
|------|------|
| 下载 | `POST /api/download/financial_data` |
| 验证查询 | `GET /api/financial/data` |
| 名称 | `GET /api/utility/batch_stock_name` |

同步阻塞版：`POST /api/download/financial_data2`（本脚本未封装，需时用 REST 或客户端）。

## 安全

- **写操作**：会触发服务端向行情源拉取并缓存数据
- 勿对「沪深 A股」等超大列表无确认地下载
- 不提供投资建议

## 参考

- [fundamental-screen](../qmt-bridge-fundamental-screen/SKILL.md) · `docs/rest-api.md` · [`_shared/financial_util.py`](../_shared/financial_util.py)
