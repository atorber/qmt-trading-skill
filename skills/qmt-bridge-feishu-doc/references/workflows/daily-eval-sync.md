# 当日复盘 → 飞书云文档

**前置**：[lark-cli-setup.md](../lark-cli-setup.md)。执行前读 **lark-shared**、**lark-doc**；知识库节点读 **lark-wiki**。专家规程读 **qmt-bridge-execution-review** 的 [expert-review-protocol.md](../../../qmt-bridge-execution-review/references/expert-review-protocol.md)。

## 固定流程

1. **拉取客观报告 + 证据包**（脚本）
2. **三角色专家评审**（Agent，基于 evidence JSON，写入 `*_expert.md` 并合并第七节）
3. **新建或更新**飞书 docx（正文为合并后的 Markdown）

| 层级 | 规则 |
|------|------|
| 一～六（客观） | **必须**用脚本产物；禁止 Agent 手写/篡改数字 |
| 七（专家） | **必须**基于 `*_evidence.json`；禁止编造；允许撰写评语 |

## 1. 客观层：QMT 脚本

**单账户**：

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY \
  --feishu-md
```

**全账户综合**：

```bash
python skills/qmt-bridge-execution-review/scripts/combined_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY \
  --feishu-md
```

产物（相对**工作区根**，勿写死机器绝对路径；以脚本 stderr 打印的路径为准）：

| 文件 | 说明 |
|------|------|
| `reports/feishu_daily_eval.md` / `feishu_combined_daily_eval.md` | 客观 MD（含第七节占位） |
| `reports/daily_eval_evidence.json` / `combined_daily_eval_evidence.json` | 证据包（专家必读） |

默认 `--eval-mode=evidence`。旧模板对比可用 `--eval-mode=rules`。

## 2. 专家层：三角色评审

```text
用投顾/基金经理/交易员三角色做今日复盘并综合裁决。
```

1. 读 evidence JSON（禁止编造）
2. 按 persona 写 7.1～7.3，再写 7.4 综合裁决
3. 完整第七节写入：
   - `reports/feishu_daily_eval_expert.md`（或 `feishu_combined_daily_eval_expert.md`）
4. 用专家节**替换**客观 MD 中「## 七、专家评审」至文末说明之前的占位，保存回 `feishu_*_daily_eval.md`

章节结构：

1. 统计概览  
2. 当日委托  
3. 当日成交  
4. 按标的汇总  
5. 盈亏与不操作基线（客观）  
6. 规则标签与算法参考分  
7. 专家评审（投顾 / 基金经理 / 交易员 / 综合裁决）

## 3. 放置位置（Agent 决策）

| 用户意图 | 做法 |
|----------|------|
| **未指定父文档/目录**（默认） | 知识库根新建（§4A） |
| **给出 wiki 父页面** | 父节点下新建（§4B） |
| **云空间「每日复盘」文件夹** | `docs +create --folder-token`（§4C） |
| **覆盖已有** | 仅 `docs +update`（§5） |

**不要**在未获用户指定时擅自使用历史 `parent_node_token`。

可选：`FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN` / `feishu_doc_ids.json` 的 `daily-eval-wiki-parent`。

## 4. 新建文档

标题与 Markdown H1 一致。

### 4A. 知识库根

```bash
lark-cli wiki +node-create --as user \
  --title "QMT Trading Skill 当日复盘 2026-05-22 14:30:00"

lark-cli docs +update --api-version v2 --doc OBJ_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

### 4B. 指定 wiki 父页

```bash
lark-cli wiki +node-create --as user \
  --parent-node-token PARENT_WIKI_TOKEN \
  --title "QMT Trading Skill 当日复盘 2026-05-22 14:30:00"

lark-cli docs +update --api-version v2 --doc OBJ_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

### 4C. 云空间文件夹

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --as user \
  --folder-token FEISHU_FOLDER_DAILY_EVAL_TOKEN \
  --title "QMT Trading Skill 当日复盘 2026-05-22 14:30:00" \
  --content @reports/feishu_daily_eval.md
```

## 5. 滚动更新

```bash
# 先 §1～§2 更新本地 MD，再：
lark-cli docs +update --api-version v2 --doc DOC_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

## 6～7. 列表标题与本地记录

同前：按 **lark-drive** 同步标题；token 记入 `reports/feishu_doc_ids.json`（勿提交 git）。
