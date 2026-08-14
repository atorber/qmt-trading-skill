---
name: qmt-bridge-fundamental-screen
description: >-
  通过 QMT Bridge 筛选财报指标：按字段过滤、显示中文名称。缺数时可自动补下载。
  在用户提到基本面、财报筛选、ROE、EPS、排雷时使用；仅下载缓存请用 financial-download。
---

# QMT Trading Skill · 基本面筛选

> **实现状态**：✅ `screen_financial.py`（筛选；下载见 [financial-download](../qmt-bridge-financial-download/SKILL.md)）

## 目标

基于服务端 **xtquant 财务报表缓存** 做可验证粗筛；单只或少量标的缺数时脚本可自动补下载。

## 相关 Skill

| 需求 | Skill |
|------|--------|
| **只下载 / 批量补缓存 / 下载后验证** | [qmt-bridge-financial-download](../qmt-bridge-financial-download/SKILL.md) |
| **按指标筛选** | 本 Skill |

## 脚本（优先使用）

```bash
# 筛选（默认缺数自动 download + 等待 5s）
python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py \\
  --host HOST --port PORT \\
  --codes 300394.SZ,603986.SH --table Pershareindex

# ROE ≥ 5%（别名 roe → du_return_on_equity）
python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py \\
  --codes 300394.SZ,603986.SH --table Pershareindex --field roe --min 5

# 关闭自动下载（需已缓存）
python skills/qmt-bridge-fundamental-screen/scripts/screen_financial.py \\
  --codes 600584.SH --no-if-missing
```

大批量下载请先：

```bash
python skills/qmt-bridge-financial-download/scripts/download_financial_data.py \\
  --codes ... --verify
```

## 推荐流程（Agent）

```
1. 解析股票列表与筛选条件
2. 若用户仅要「下载财报」→ 使用 financial-download，不要本脚本
3. 运行 screen_financial.py（默认 --if-missing）
4. 输出：代码 + 中文名 + 指标 + 报告期
```

## 主要参数

| 参数 | 说明 |
|------|------|
| `--codes` | 必填 |
| `--table` | 默认 `Pershareindex` |
| `--field` | 筛选字段，支持别名 `roe` |
| `--min` / `--max` | 数值过滤（ROE 等为**百分点**，5 表示 5%） |
| `--from-positions` | 使用当前持仓代码列表 |
| `--if-missing` / `--no-if-missing` | 缺数自动下载（默认开） |
| `--download` | 查询前强制下载 |
| `--wait` | 下载后等待秒数（默认 5） |
| `--json` | JSON 输出 |

## 常用字段（Pershareindex）

| 字段 | 含义 |
|------|------|
| `du_return_on_equity` | ROE（`--field roe`） |
| `s_fa_eps_basic` | 基本每股收益 |
| `s_fa_bps` | 每股净资产 |

## API

| 操作 | 路径 |
|------|------|
| 查询 | `GET /api/financial/data` |
| 下载 | `POST /api/download/financial_data`（或 financial-download Skill） |

## 安全

- 筛选以只读查询为主；自动/强制下载会写缓存
- 不输出投资建议

## 参考

- [financial-download](../qmt-bridge-financial-download/SKILL.md) · `docs/rest-api.md`
