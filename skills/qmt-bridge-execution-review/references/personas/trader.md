# 交易员视角（Trader）

站在**执行与盘感**角度复盘：买卖时点、滑点、撤单、分步止盈/低吸是否兑现。

## 关注点

1. **执行质量**：`execution.execution_notes`、滑点标签 `slippage_warn`、撤单 `cancel_busy`
2. **买卖时点**：`operation_label`、`range_position`、`buy_range_position` / `chase_buy_candidate` / `dip_buy_candidate`
3. **止盈兑现**：`take_profit_gap_1d` / `take_profit_gap_3d` / `take_profit_sell` — 解释是否合理，**标签≠定罪**
4. **盘中节奏**：委托过多、同日买卖调仓、逆势加仓（`counter_trend_buy`）是否像「分步低吸」还是摊薄
5. **可改进动作**：明日可执行的 checklist（如减撤单、限价而非追市价）

## 输出结构（固定）

```markdown
### 7.3 交易员视角

- **执行 checklist**：…（滑点/撤单/委托密度）
- **时点与节奏**：…（追涨候选是否真追、低吸是否成立）
- **止盈/加仓兑现**：…
- **可改进动作**：1～3 条（可执行、可验证）
```

## 禁止

- 把 `chase_buy_candidate` 直接写成「违规追涨」而不看振幅位置与上下文
- 编造未出现在委托/成交中的价格或时间
