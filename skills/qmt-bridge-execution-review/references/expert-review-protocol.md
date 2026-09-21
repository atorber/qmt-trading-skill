# 专家复盘总控规程（Expert Review Protocol）

Agent 在生成「三角色复盘」或同步飞书第七节时 **必须** 遵守本规程。

## 优先级

| 层级 | 内容 | 权威性 |
|------|------|--------|
| 客观证据 | `reports/daily_eval_evidence.json` 或 `combined_daily_eval_evidence.json` | **最高** — 数字不可改写 |
| 规则标签 | `rule_tags` | 供解释，**非定罪** |
| 算法参考分 | `score_hints`（`algorithmic_only: true`） | **仅对照** |
| 专家综合 | 本节 7.4 | **展示以本裁决为准** |

## 工作流

1. **跑脚本**（若尚无当日证据）：
   - 单账户：`daily_trade_report.py --feishu-md`（默认 `--eval-mode=evidence`，写出 evidence）
   - 双账户：`combined_trade_report.py --feishu-md`
2. **读取证据包** JSON；确认 `meta.trade_date` 为当日。
3. **顺序（或并行）套用三角色**：
   - [personas/advisor.md](personas/advisor.md)
   - [personas/fund-manager.md](personas/fund-manager.md)
   - [personas/trader.md](personas/trader.md)
4. **综合裁决**（7.4）：
   - **共识**：三角色一致的结论（须各附依据字段，如 `pnl.op_alpha_total_pnl`、某 `rule_tags[].tag`）
   - **分歧**：何处不一致及取舍理由
   - **综合结论**：一段话；可给专家综合感受分（1～10），并注明「非算法分」
   - **明日纪律**：恰好 1～3 条，可验证
5. **落盘**：
   - 将完整「## 七、专家评审」写入 `reports/feishu_daily_eval_expert.md`（综合账户用 `feishu_combined_daily_eval_expert.md`）
   - 用专家节 **替换** 客观 MD 中第七节占位（或追加合并后覆盖 `reports/feishu_daily_eval.md`）
   - 再按 [feishu-doc 工作流](../../qmt-bridge-feishu-doc/references/workflows/daily-eval-sync.md) 上传

## 硬约束

- **禁止编造** evidence 中不存在的金额、股数、涨跌幅、滑点、日期
- **禁止**跳过脚本、凭终端印象手写客观章节一～六
- **允许**基于 evidence 撰写 7.1～7.4 评语（这是专家层的职责）
- 每处关键数字旁用括号标注来源，例：`操作增量 -3,200 元（pnl.op_alpha_total_pnl）`
- 文末声明：统计归纳与专家评述，**非投资建议**

## 提示词（可复制）

```text
用投顾/基金经理/交易员三角色做今日复盘并综合裁决。
先确认 Bridge 与证据包；禁止编造数字；按 expert-review-protocol 输出第七节并写入 feishu_*_expert.md。
```

## 与旧 rules 模式

`--eval-mode=rules` 仍可输出旧版模板「做得好的/需改进」；专家规程仍以 evidence JSON 为准。对比校准算法分时可用 rules，日常默认 evidence。
