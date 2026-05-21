# 当日复盘 → 飞书云文档

**前置**：[lark-cli-setup.md](../lark-cli-setup.md)（安装、`config init`、`auth login`）。执行前读 **lark-shared**、**lark-doc** Skill。

## 1. 拉取复盘数据（QMT）

```bash
python skills/qmt-bridge-execution-review/scripts/daily_trade_report.py \
  --host 127.0.0.1 --port 8080 --api-key KEY --json
```

## 2. 写入 Markdown

路径：`reports/feishu_daily_eval.md`（UTF-8，仓库根下相对路径）。

- H1 / 云文档标题：[doc-registry.md](../doc-registry.md)  
  例：`# QMT Bridge 当日复盘 2026-05-21 15:30:00`
- 正文：委托统计、`operation_evaluation` 分标的表等

## 3. 覆盖更新（lark-doc 快捷命令）

`DOC_TOKEN` ← `reports/feishu_doc_ids.json` 的 `daily-eval` 或 `FEISHU_DAILY_EVAL_DOC_ID`。

```bash
cd <qmt-bridge 仓库根>
lark-cli docs +update --api-version v2 --doc DOC_TOKEN --as user \
  --command overwrite --doc-format markdown \
  --content @reports/feishu_daily_eval.md
```

预览：`加上 --dry-run`。

## 4. 同步云空间列表标题

与 H1 相同。按 **lark-drive** Skill 执行 `drive files patch`（`type=docx`，`new_title` 为 H1 文本）。

## 5. 新建文档（可选）

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --as user \
  --folder-token FEISHU_FOLDER_DAILY_EVAL_TOKEN \
  --title "QMT Bridge 当日复盘 2026-05-21 15:30:00" \
  --content @reports/feishu_daily_eval.md
```

从返回 JSON 取 `document_id` 写入 `feishu_doc_ids.json` 供下次滚动更新。
