# 黄金ETF日内波段策略 · 实施方案

> 518880 黄金ETF x 上期所AU期货价差回归 · 2万测试资金 · 基于 qmt-bridge 基建

---

## 一、基建评估：qmt-bridge 能力对照

### 结论：完全支持，qmt-bridge 不需要任何改动

策略所需的每一项数据和交易能力，qmt-bridge 都已覆盖。策略代码作为独立项目（`gold-etf-strategy/`），通过 `QMTClient` 远程调用即可。

### 数据获取能力

| 策略需求 | qmt-bridge 接口 | 备注 |
|---------|-----------------|------|
| AU主力合约代码 | `client.get_main_contract("AU.SHFE")` | 返回当前主力合约如 `AU2506.SHFE` |
| AU期货实时行情 | `client.subscribe_realtime(["AU2506.SHFE"], cb, period="tick")` | WebSocket `/ws/realtime`，tick 级推送 |
| 518880 实时行情 | `client.subscribe_realtime(["518880.SH"], cb, period="tick")` | 同上 |
| 历史1分钟K线 | `client.get_history_ex(stocks, period="1m", start_time=..., end_time=...)` | 返回 DataFrame |
| 历史日线 | `client.get_history_ex(stocks, period="1d", ...)` | 同上 |
| 实时快照（单次查询） | `client.get_market_snapshot(["518880.SH", "AU2506.SHFE"])` | REST 轮询备用方案 |
| 数据预下载 | `client.download_batch(stocks, period="1m", start_time=..., end_time=...)` | 服务端缓存，后续读取更快 |
| 过期合约下载 | `client.download_history_contracts()` | 主力合约映射等 |

### 交易执行能力

| 策略需求 | qmt-bridge 接口 | 备注 |
|---------|-----------------|------|
| 限价买入/卖出 | `client.place_order(stock_code, order_type, volume, price_type=11, price=x)` | `order_type`: 23=买入, 24=卖出 |
| 异步下单 | `client.place_order_async(...)` | 结果通过 `/ws/trade` 回调 |
| 撤单 | `client.cancel_order(order_id)` | 同步撤单 |
| 查持仓 | `client.query_positions()` / `client.query_single_position("518880.SH")` | 实盘引擎用 |
| 查余额 | `client.query_asset()` | 返回 cash, frozen_cash, total_asset 等 |
| 查委托 | `client.query_orders(cancelable_only=True)` | 可筛选未成交 |
| 查成交 | `client.query_trades()` | 当日成交明细 |
| 成交回报推送 | `client.subscribe_trade_events(callback)` | WebSocket `/ws/trade`，事件类型：order/trade/order_error/cancel_error |

### 辅助能力

| 需求 | qmt-bridge 接口 | 备注 |
|------|-----------------|------|
| 交易日历 | `client.get_trading_dates("SH", start_time, end_time)` | 判断是否交易日 |
| 是否交易日 | `client.is_trading_date("SH", "20260211")` | 布尔返回 |
| 交易时段 | `client.get_trading_period("518880.SH")` | ETF与期货时段不同，可查询 |
| 合约详情 | `client.get_batch_instrument_detail(["AU2506.SHFE"])` | tick大小等 |
| 节假日 | `client.get_holidays()` | 自动跳过非交易日 |

### 一个不影响的差异：条件单

qmt-bridge 未封装 `order_stock_condition`（条件单）。但策略引擎自身实时监控价格并触发止损下单，日内不留仓，不需要服务端条件单。

---

## 二、策略概述

### 核心逻辑

上期所黄金期货是"快指针"，黄金ETF是"慢指针"。两者跟踪同一底层（黄金），但期货对信息反应更快。当日内涨跌幅出现显著偏离时，对ETF做高抛低吸，赚"慢指针追上快指针"的差价。

### 与现有体系的关系

```
投资策略体系
├── 中线埋伏策略（主策略）
├── 短线打板策略（AI + QMT 决策支持）
└── 黄金ETF日内波段（本策略）  ← 独立资金池，独立记账
```

### 2万资金的现实预期

测试期目标是**验证策略是否可行**，不是赚钱。底仓约1万（保证双向操作能力），机动资金约1万。核心价值是积累数据、标定参数、跑通链路。即使一切顺利，月盈利也就几百元量级。

---

## 三、系统架构

### 整体结构

```
┌─────────────────────────────────────────────────────┐
│            gold-etf-strategy（Mac 独立项目）          │
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐    │
│  │  数据模块   │→│  策略引擎   │→│  执行模块     │    │
│  │           │  │           │  │              │    │
│  │ QMTClient │  │ spread计算 │  │ Simulated /  │    │
│  │ .subscribe │  │ 信号生成   │  │ Live Engine  │    │
│  │ _realtime  │  │ 风控检查   │  │              │    │
│  └───────────┘  └───────────┘  └──────┬───────┘    │
│        │                              │            │
│   QMTClient                      QMTClient         │
│   (数据API)                     (交易API)           │
│        │                              │            │
│  ┌─────┴──────────────────────────────┴───────┐    │
│  │              记录模块 (SQLite)               │    │
│  │  trades · signals · daily_summary · risk    │    │
│  └──────────────────┬─────────────────────────┘    │
│                     │                              │
│                     ▼                              │
│  ┌────────────────────────────────────────────┐    │
│  │           通知模块 (飞书机器人)               │    │
│  │  交易通知 · 风控告警 · 每日报告 · 异常告警    │    │
│  └────────────────────────────────────────────┘    │
│                     │                              │
│              飞书 Webhook API                       │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │        Streamlit 可视化仪表盘                 │    │
│  │                                            │    │
│  │  盘中监控 · 交易复盘 · Spread分析 ·          │    │
│  │  风控面板 · 回测报告 · 策略健康度             │    │
│  │                                            │    │
│  │  数据来源：SQLite + QMTClient(实时)          │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
├──────────────── HTTP / WebSocket ────────────────────┤
│                                                     │
│                qmt-bridge（已有基建）                  │
│       Windows QMT → xtquant 数据 + xttrader 交易     │
└─────────────────────────────────────────────────────┘
```

### 模拟/实盘切换

这是架构层面最关键的设计决策——执行模块抽象为统一接口，底层可以切换实现：

```python
# 统一接口
class ExecutionEngine(ABC):
    def place_order(self, code, direction, volume, price) -> str: ...
    def cancel_order(self, order_id) -> bool: ...
    def get_positions(self) -> dict: ...
    def get_balance(self) -> float: ...

# 模拟引擎：内存维护虚拟账户，不调用 QMTClient 交易接口
class SimulatedEngine(ExecutionEngine): ...

# 实盘引擎：调用 QMTClient.place_order / cancel_order / query_positions
class LiveEngine(ExecutionEngine):
    def __init__(self, client: QMTClient): ...
```

启动时 `--mode simulated` 或 `--mode live` 决定用哪个引擎。策略引擎、风控、记录模块完全不需要改动。

可以同时运行两个引擎——实盘执行真实交易，模拟引擎同步记录"如果参数不同会怎样"，用于对照实验。

---

## 四、六个核心模块

按开发优先级排列。每个模块先实现最小可用版本，后续迭代增强。

### 模块一：数据模块

**职责：** 通过 QMTClient 获取行情，向策略引擎提供统一数据流。

**盘前初始化流程：**
```python
client = QMTClient(host, port, api_key=api_key)

# 1. 确认今天是交易日
if not client.is_trading_date("SH", today):
    exit("非交易日，不启动")

# 2. 获取AU主力合约代码（每日更新，处理换月）
main_contract = client.get_main_contract("AU.SHFE")
# 返回如 {"data": "AU2506.SHFE"}

# 3. 拉取今日之前的历史数据（用于计算开盘前的滚动均值/标准差基准）
au_hist = client.get_history_ex([main_contract], period="1m", count=240)  # 前一日全天
etf_hist = client.get_history_ex(["518880.SH"], period="1m", count=240)
```

**实时数据订阅：**
```python
# 同时订阅期货和ETF的tick数据
asyncio.run(client.subscribe_realtime(
    stocks=[main_contract, "518880.SH"],
    callback=on_tick,
    period="tick",
))
```

**数据处理关键点：**
- **用涨跌幅而非绝对价格：** `pct(t) = (price(t) - open_price) / open_price`，避免期货换月价格跳变
- **只在重叠交易时段计算spread：** 期货有夜盘(21:00-02:30)，ETF没有。spread仅在9:30-11:30和13:00-15:00计算
- **交易时段可查询确认：** `client.get_trading_period("518880.SH")` 返回确切时段
- **数据中断检测：** 超过30秒无新tick → 标记数据异常 → 暂停信号生成
- **内存滑动窗口：** 维护最近N根1分钟K线，不落盘

**存储方案：**
- 实时数据：内存滑动窗口
- 历史数据：Parquet文件（按品种+日期组织，回测用）
- 结构化数据：SQLite（交易日志、信号记录、风控状态）

### 模块二：策略引擎

**核心计算：**
```python
# 日内涨跌幅
etf_pct = (etf_price - etf_open) / etf_open
au_pct = (au_price - au_open) / au_open

# 价差
spread = etf_pct - au_pct

# 偏离度（Z-Score）
z_score = (spread - rolling_mean(spread, window)) / rolling_std(spread, window)
```

**信号类型：**

| 信号 | 触发条件 | 动作 |
|------|---------|------|
| `OPEN_LONG` | z_score < -threshold（ETF相对便宜） | 买入ETF |
| `OPEN_SHORT` | z_score > +threshold（ETF相对贵） | 卖出底仓ETF |
| `CLOSE` | z_score回归到0附近 | 平掉日内仓位 |
| `STOP_LOSS` | 浮亏超限 | 止损平仓 |
| `TIME_STOP` | 持仓超时 | 强制平仓 |
| `EOD_CLOSE` | 14:50 | 尾盘清仓 |

**待回测标定的参数：** 滚动窗口长度、偏离度阈值、止损幅度、持仓超时时间、时段过滤规则。先用经验值硬编码，Phase 0 回测后调整。不做参数配置中心，避免过早抽象。

**策略引擎不关心是模拟还是实盘**——它只生成信号，执行由下游处理。

### 模块三：执行模块

**模拟交易引擎核心逻辑：**
```python
class SimulatedEngine(ExecutionEngine):
    def __init__(self, initial_cash=20000, fee_rate=0.00025):
        self.cash = initial_cash
        self.positions = {}  # {code: volume}
        self.trades = []
        self.fee_rate = fee_rate

    def place_order(self, code, direction, volume, price):
        slippage = 0.001 if direction == "buy" else -0.001  # 模拟1个tick滑点
        exec_price = price * (1 + slippage)
        cost = exec_price * volume
        fee = cost * self.fee_rate

        if direction == "buy":
            self.cash -= (cost + fee)
            self.positions[code] = self.positions.get(code, 0) + volume
        else:
            self.cash += (cost - fee)
            self.positions[code] = self.positions.get(code, 0) - volume

        # 生成 trade record，写入 SQLite
        ...
```

**实盘交易引擎核心逻辑：**
```python
class LiveEngine(ExecutionEngine):
    def __init__(self, client: QMTClient):
        self.client = client

    def place_order(self, code, direction, volume, price):
        order_type = 23 if direction == "buy" else 24
        result = self.client.place_order(
            stock_code=code,
            order_type=order_type,
            order_volume=volume,
            price_type=11,    # 限价
            price=price,
            strategy_name="gold_etf_swing",
        )
        return result

    def cancel_order(self, order_id):
        return self.client.cancel_order(order_id)

    def get_positions(self):
        return self.client.query_positions()

    def get_balance(self):
        asset = self.client.query_asset()
        return asset.get("cash", 0)

    # 异步下单 + 成交回报监听（Phase 3 增强）
    async def place_order_and_monitor(self, code, direction, volume, price):
        result = self.client.place_order_async(...)
        # 通过 subscribe_trade_events 监听成交回报
        # 超时未成交 → 撤单
```

### 模块四：记录模块

**职责：** 记录一切，让每一笔交易和每一个信号都可追溯可分析。

**这个模块的重要性等同于策略本身**——没有完整的记录，所有的回测和优化都是空中楼阁。

**SQLite 表结构：**

```sql
-- 每笔成交
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    code TEXT NOT NULL,
    direction TEXT NOT NULL,  -- buy/sell
    volume INTEGER NOT NULL,
    price REAL NOT NULL,
    fee REAL DEFAULT 0,
    mode TEXT NOT NULL,  -- simulated/live
    signal_id TEXT,
    spread_at_entry REAL,
    spread_at_exit REAL,
    pnl REAL,
    hold_duration_seconds INTEGER,
    exit_reason TEXT  -- reversion/stop_loss/time_stop/eod/risk
);

-- 每个信号（含未执行的）
CREATE TABLE signals (
    signal_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    spread_value REAL,
    z_score REAL,
    au_price REAL,
    etf_price REAL,
    au_pct REAL,
    etf_pct REAL,
    executed INTEGER DEFAULT 0,
    skip_reason TEXT,
    market_snapshot TEXT  -- JSON: 当时的市场状态快照
);

-- 每日汇总
CREATE TABLE daily_summary (
    date TEXT PRIMARY KEY,
    mode TEXT,
    total_trades INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    max_single_loss REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    signals_generated INTEGER DEFAULT 0,
    signals_executed INTEGER DEFAULT 0,
    signals_skipped INTEGER DEFAULT 0,
    risk_events_json TEXT  -- JSON array
);

-- 风控触发记录
CREATE TABLE risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    trigger_value REAL,
    threshold REAL,
    action_taken TEXT
);
```

**为什么记录未执行的信号：** 这是后续优化的金矿。可能发现"被风控过滤掉的信号其实胜率很高"或"某个时段的信号全是假信号"——这些洞察只有在完整记录了所有信号后才能获得。

### 模块五：通知模块（飞书机器人）

**职责：** 将策略关键事件实时推送到飞书，让人不盯盘也能掌握策略运行状态。

**实现方式：** 飞书自定义机器人 Webhook（POST JSON 到 webhook URL），零依赖（stdlib `urllib` 即可），无需飞书 SDK。

**通知事件分级：**

| 级别 | 事件 | 推送时机 | 消息内容 |
|------|------|---------|---------|
| **交易通知** | 开仓成交 | 每笔成交后 | 方向、价格、数量、spread值、z_score |
| **交易通知** | 平仓成交 | 每笔平仓后 | 方向、价格、盈亏金额、持仓时长、平仓原因 |
| **风控告警** | 止损触发 | 止损平仓后 | 亏损金额、触发规则、当日累计亏损 |
| **风控告警** | 日内熔断 | 触发时 | 熔断原因（连亏/单日亏损上限）、当日统计 |
| **风控告警** | 策略级熔断 | 触发时 | 累计亏损、熔断线、策略已停止 |
| **每日报告** | 收盘汇总 | 15:05 | 当日交易笔数、胜率、盈亏、持仓状态 |
| **系统告警** | 数据中断 | 检测到时 | 中断时长、影响品种、是否暂停信号 |
| **系统告警** | 策略启动/停止 | 启停时 | 运行模式、主力合约代码、初始持仓 |
| **系统告警** | 下单失败 | 失败时 | 错误信息、失败订单详情 |

**飞书消息格式：** 使用富文本卡片（Interactive Card），结构清晰易读。

```python
import json
import urllib.request
import time
import hmac
import hashlib
import base64


class FeishuNotifier:
    """飞书机器人通知器。"""

    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def _sign(self) -> tuple[str, str]:
        """生成签名（v2 安全校验）。"""
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode(), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode()
        return timestamp, sign

    def send(self, title: str, content: list[list[dict]]):
        """发送富文本消息。"""
        msg = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content,
                    }
                }
            },
        }
        if self.secret:
            ts, sign = self._sign()
            msg["timestamp"] = ts
            msg["sign"] = sign

        data = json.dumps(msg).encode()
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)

    # ── 便捷方法 ──────────────────────────────

    def notify_trade(self, direction, code, price, volume, spread, z_score, pnl=None):
        """交易成交通知。"""
        action = "买入" if direction == "buy" else "卖出"
        lines = [
            [{"tag": "text", "text": f"{action} {code}  {volume}股 @ {price:.3f}"}],
            [{"tag": "text", "text": f"Spread: {spread:.4f}  Z-Score: {z_score:.2f}"}],
        ]
        if pnl is not None:
            emoji = "+" if pnl >= 0 else ""
            lines.append([{"tag": "text", "text": f"本笔盈亏: {emoji}{pnl:.2f}元"}])
        self.send(f"{'🟢' if direction == 'buy' else '🔴'} {action}成交", lines)

    def notify_risk_alert(self, rule_name, trigger_value, threshold, action_taken):
        """风控告警通知。"""
        self.send("⚠️ 风控告警", [
            [{"tag": "text", "text": f"触发规则: {rule_name}"}],
            [{"tag": "text", "text": f"触发值: {trigger_value:.4f}  阈值: {threshold:.4f}"}],
            [{"tag": "text", "text": f"执行动作: {action_taken}"}],
        ])

    def notify_daily_summary(self, date, trades, wins, losses, pnl, win_rate):
        """每日收盘汇总。"""
        emoji = "📈" if pnl >= 0 else "📉"
        self.send(f"{emoji} {date} 收盘汇总", [
            [{"tag": "text", "text": f"交易: {trades}笔  胜: {wins}  负: {losses}"}],
            [{"tag": "text", "text": f"胜率: {win_rate:.1%}  盈亏: {'+' if pnl >= 0 else ''}{pnl:.2f}元"}],
        ])

    def notify_system(self, event, detail):
        """系统事件通知（启停、异常等）。"""
        self.send(f"🔧 {event}", [
            [{"tag": "text", "text": detail}],
        ])
```

**防刷控制：**
- 同类通知最短间隔60秒（避免行情剧烈波动时刷屏）
- 数据中断告警：首次告警后，恢复时再发一条，中间不重复
- 每日通知上限（如50条），超限后只发风控告警和收盘汇总

**配置：**
```python
# config.py
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
FEISHU_WEBHOOK_SECRET = ""  # 可选，飞书机器人签名密钥
NOTIFY_ENABLED = True
NOTIFY_TRADE = True       # 是否推送每笔成交
NOTIFY_RISK = True        # 是否推送风控告警（建议始终开启）
NOTIFY_DAILY = True       # 是否推送每日汇总
NOTIFY_SYSTEM = True      # 是否推送系统事件
```

### 模块六：可视化仪表盘（Streamlit）

**职责：** 将策略运行的全过程——从实时行情到历史复盘——变成可交互的可视化界面。盘中用来监控，盘后用来分析优化。

**为什么用 Streamlit：**
- 纯 Python，不写前端代码，与策略项目的 pandas/numpy 生态无缝衔接
- 内置 `st.plotly_chart` / `st.altair_chart` 支持交互式图表
- 多页面应用（`st.navigation`），每个分析维度一个页面
- `st_autorefresh` 组件支持盘中定时刷新

**数据来源：**
- 历史/交易数据：读 SQLite（trades, signals, daily_summary, risk_events 表）
- 实时数据：调 QMTClient 快照接口（`get_market_snapshot`），或读策略引擎写入的内存/临时文件
- 回测数据：读 Parquet + 回测结果 JSON/CSV

---

#### 页面一：盘中监控（Dashboard）

盘中最核心的一屏，目标是**一眼看清策略当前状态**。

**顶部状态栏（Metrics）：**

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 运行模式  │ │ 当日盈亏  │ │ 当日交易  │ │ 当前持仓  │ │ 策略状态  │
│ 模拟/实盘 │ │ +12.50元  │ │  3笔/2胜  │ │ 500股    │ │ 运行中    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**核心图表区（上下两栏）：**

**图表1：Spread 实时走势（主图）**
- X轴：日内时间（9:30~15:00）
- Y轴：spread 值
- 叠加层：
  - spread 实时曲线
  - 滚动均值线
  - ±1σ / ±2σ 通道带（半透明填充）
  - 买入信号标记（绿色三角 ▲）
  - 卖出信号标记（红色三角 ▼）
  - 当前持仓区间（浅色背景标记从开仓到现在的时间段）
- 实现：Plotly（支持悬浮查看具体数值）

**图表2：ETF vs 期货日内涨跌幅对比**
- 双线叠加：ETF 日内涨跌幅 vs AU 期货日内涨跌幅
- 填充两条线之间的差值区域（spread > 0 填红，spread < 0 填绿）
- 直观展示"谁领先谁"

**右侧信息面板：**

```
┌─ 实时报价 ─────────────┐
│ 518880   6.521 +0.12%  │
│ AU2506  658.30 +0.25%  │
│ Spread   -0.0013       │
│ Z-Score  -1.82         │
├─ 当前持仓 ─────────────┤
│ 518880   500股         │
│ 成本     6.515         │
│ 浮盈     +3.00元       │
│ 持仓时长  12分钟        │
├─ 今日信号 ─────────────┤
│ 10:23 OPEN_LONG  已执行 │
│ 10:45 CLOSE      已执行 │
│ 11:02 OPEN_SHORT 跳过   │
│ 13:15 OPEN_LONG  已执行 │
├─ 风控状态 ─────────────┤
│ 日亏上限  ██░░░ 40%    │
│ 交易笔数  ███░░ 60%    │
│ 连续亏损  █░░░░ 20%    │
└────────────────────────┘
```

**自动刷新：** 每10秒刷新一次（`st_autorefresh(interval=10000)`），盘中无需手动操作。

---

#### 页面二：交易复盘

盘后复盘的核心工具，回答"今天做得怎么样、为什么"。

**日期选择器：** 顶部日期/日期范围选择。

**图表1：累计盈亏曲线**
- X轴：时间（按天或按笔）
- Y轴：累计 PnL（元）
- 附加：最大回撤区间高亮标记
- 可切换视角：按日汇总 / 按笔逐步累加

**图表2：每日盈亏柱状图**
- X轴：日期
- Y轴：当日 PnL
- 颜色：盈利绿色，亏损红色
- 叠加：滚动胜率折线（右Y轴）

**图表3：单笔盈亏分布**
- 直方图：每笔 PnL 的分布
- 标注均值、中位数
- 可以直观看出"盈利笔平均赚多少，亏损笔平均亏多少"——盈亏比

**图表4：持仓时长 vs 盈亏散点图**
- X轴：持仓时长（分钟）
- Y轴：单笔 PnL
- 颜色：按平仓原因着色（回归/止损/超时/尾盘）
- 洞察：持仓多久赚钱概率最高？超时平仓的是不是都亏？

**图表5：平仓原因分布**
- 饼图 / 环形图
- 分类：spread回归、止损、超时、尾盘清仓、风控触发
- 占比直观：理想状态是"回归"占绝大多数

**交易明细表：**
- 可排序、可筛选的表格
- 列：时间、方向、价格、数量、开仓spread、平仓spread、盈亏、持仓时长、平仓原因
- 点击某行可展开详情（开仓时的市场快照）

---

#### 页面三：Spread 深度分析

策略的根基是 spread 的统计特性，这个页面把 spread 翻个底朝天。

**图表1：Spread 日内分时热力图**
- X轴：日内时间段（每30分钟一个桶）
- Y轴：日期
- 颜色：spread 均值或波动率
- 洞察：哪个时段 spread 波动最大？是否有稳定的日内规律？

**图表2：Spread 分布直方图**
- 全量 spread 值的频率分布
- 叠加正态分布拟合曲线
- 标注均值、标准差、偏度、峰度
- 可按时段筛选（早盘 vs 午盘）

**图表3：Spread 自相关图（ACF）**
- 展示 spread 的自相关结构
- 如果短lag自相关显著为正 → 趋势性；显著为负 → 均值回复
- 这是策略成立的统计学基础

**图表4：回归速度分析**
- X轴：偏离程度（|z_score| 分桶：1~1.5σ, 1.5~2σ, 2~2.5σ, >2.5σ）
- Y轴：回归到 0.5σ 以内的平均时间（分钟）
- 洞察：偏离越大回归越快吗？多大的偏离才值得交易？

**图表5：Spread vs 黄金价格波动关系**
- 散点图：AU日内波幅（high-low）vs spread 标准差
- 洞察：黄金大涨大跌的日子，spread 是更大还是更小？策略适合哪种市场环境？

**图表6：合约换月影响分析**
- 时间线标注换月日期
- 换月前后 spread 行为是否异常
- 帮助决定换月日是否需要停策略

---

#### 页面四：风控面板

风控不是"设了就忘"的东西，需要持续监控和校准。

**顶部指标卡：**

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 累计盈亏  │ │ 最大回撤  │ │ 距熔断线  │ │ 滚动胜率  │
│ +156.00  │ │ -89.00   │ │ 还剩911元 │ │ 58.3%    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**图表1：风控事件时间线**
- 时间轴展示所有风控触发事件
- 按规则类型着色（止损/熔断/超限/...）
- 点击查看触发时的详细上下文

**图表2：每日风控触发统计**
- 堆叠柱状图：每天各类风控规则的触发次数
- 洞察：风控是越来越少触发（策略在收敛）还是越来越多（策略在失效）？

**图表3：止损 vs 非止损交易对比**
- 分组柱状图：止损交易 vs 正常平仓交易的数量和平均亏损
- 洞察：止损线设得合不合理？止损后行情是否继续恶化（验证止损的必要性）？

**图表4：信号过滤分析**
- 被风控跳过的信号 vs 被执行的信号，如果都执行了会怎样？
- 数据来源：signals 表中 `executed=0` 的记录
- 用虚拟回测估算被跳过信号的"如果盈亏"
- 洞察：风控到底是保护了你还是误杀了好机会？

**图表5：资金曲线 + 回撤图**
- 上图：账户净值曲线
- 下图：回撤百分比曲线
- 标注最大回撤的起止日期
- 叠加熔断线水平虚线

---

#### 页面五：回测报告

Phase 0 回测结果的可视化展示，也支持后续重新回测后更新。

**参数面板（侧边栏）：**
- 滚动窗口长度：滑块
- Z-Score 阈值：滑块
- 止损比例：滑块
- 持仓超时：滑块
- 点击"运行回测"重新计算

**图表1：回测权益曲线**
- 策略净值 vs 买入持有518880 vs 0基准线
- 标注最大回撤区间

**图表2：月度收益热力图**
- X轴：月份
- Y轴：年份（如果数据跨年）
- 颜色：月度收益率
- 类似量化基金的月度收益展示

**图表3：参数敏感性热力图**
- X轴：Z-Score 阈值
- Y轴：滚动窗口长度
- 颜色：夏普比率 / 总收益 / 胜率
- 找到参数的"甜蜜区"——稳健的区域比最优点更重要

**图表4：滚动胜率 & 盈亏比**
- X轴：时间
- 双Y轴：滚动20笔胜率 + 滚动盈亏比
- 洞察：策略是否稳定？有没有某段时间突然失效？

**统计摘要表：**

```
┌─────────────────────────────────┐
│ 回测区间    2025-08 ~ 2026-02   │
│ 总交易笔数  247                  │
│ 胜率        56.3%               │
│ 平均盈利    8.2元               │
│ 平均亏损    -5.1元              │
│ 盈亏比      1.61                │
│ 最大连胜    7笔                 │
│ 最大连亏    4笔                 │
│ 最大回撤    -89元 (4.5%)        │
│ 夏普比率    1.82                │
│ 日均交易    2.1笔               │
└─────────────────────────────────┘
```

---

#### 页面六：策略健康度

运行一段时间后，用这个页面判断策略是否还"活着"。

**图表1：滚动指标趋势**
- 多线图：滚动30笔胜率、滚动盈亏比、滚动夏普比率
- 叠加趋势线
- 设定健康阈值（虚线），低于阈值区域标红
- 洞察：策略在走好还是走差？

**图表2：Spread 特性漂移检测**
- 对比最近30天 vs 全历史的 spread 统计特性：
  - 均值是否偏移？
  - 标准差是否变化？
  - 回归速度是否变慢？
- 如果 spread 的统计特性发生了结构性变化，策略需要重新标定参数

**图表3：交易频率变化**
- 每日/每周的信号数量和成交数量趋势
- 频率突然下降可能意味着市场环境变了（波动率降低、spread 收窄）

**图表4：模拟 vs 实盘对比**（Phase 3 后可用）
- 同一时段的模拟交易结果 vs 实盘交易结果
- 差异分析：滑点实际有多大？执行延迟影响多少？
- 洞察：模拟和实盘的差距是否在可接受范围内？

---

#### Streamlit 实现要点

**多页面结构：**
```python
# app.py
import streamlit as st

pages = {
    "盘中监控": "pages/dashboard.py",
    "交易复盘": "pages/trades.py",
    "Spread 分析": "pages/spread.py",
    "风控面板": "pages/risk.py",
    "回测报告": "pages/backtest.py",
    "策略健康度": "pages/health.py",
}
pg = st.navigation([st.Page(v, title=k) for k, v in pages.items()])
pg.run()
```

**数据加载模式：**
```python
import sqlite3
import pandas as pd

@st.cache_data(ttl=10)  # 盘中页面：10秒缓存
def load_today_trades(db_path):
    conn = sqlite3.connect(db_path)
    return pd.read_sql("SELECT * FROM trades WHERE date(timestamp) = date('now')", conn)

@st.cache_data(ttl=300)  # 分析页面：5分钟缓存
def load_all_trades(db_path):
    conn = sqlite3.connect(db_path)
    return pd.read_sql("SELECT * FROM trades", conn)
```

**盘中自动刷新：**
```python
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10_000, key="dashboard_refresh")  # 每10秒
```

**图表库选择：**
- 交互式图表：Plotly（悬浮、缩放、框选）
- 热力图：Plotly Heatmap 或 Altair
- 简单指标：`st.metric`（内置支持 delta 箭头）
- 表格：`st.dataframe`（内置排序筛选）

---

## 五、风控三层防线

不列具体参数（这些在回测后才能确定），只描述风控的层次结构和设计原则。

```
第一层：单笔级别
├── 固定比例止损（亏X%立即平仓）
├── 时间止损（持仓超过N分钟强制平仓）
└── 尾盘强制平仓（14:50清仓，不留日内仓过夜）

第二层：日内累积级别
├── 单日最大亏损额（触发后当日停止交易）
├── 连续亏损笔数（触发后冷静期）
└── 单日最大交易笔数（防止过度交易）

第三层：策略健康度
├── 滚动胜率监控（低于阈值缩仓或暂停）
├── 底仓浮亏保护（底仓亏损过大时减仓或清仓）
└── 总亏损熔断线（策略级别止损，触发后永久停止）
```

**设计原则：**
- 风控规则硬编码在执行模块中，策略引擎无法绕过
- 模拟交易也执行完整风控逻辑（验证风控规则本身是否合理）
- 每次风控触发都写入 `risk_events` 表，盘后可以分析"风控是帮了你还是害了你"
- 参数初期从宽（避免策略还没跑起来就被风控卡死），回测后收紧

---

## 六、开发路线

### Phase 0：数据探索与回测（当前阶段）

> 目标：回答"期货-ETF价差回归是否稳定存在"这个根本问题

```
Step 1  下载数据
        ├── client.download_history_contracts()          # 过期合约/主力合约映射
        ├── main = client.get_main_contract("AU.SHFE") # 主力合约代码
        ├── client.download_batch([main], period="1m", start_time="20250801")
        ├── client.download_batch(["518880.SH"], period="1m", start_time="20250801")
        ├── au_df = client.get_history_ex([main], period="1m", start_time="20250801")
        ├── etf_df = client.get_history_ex(["518880.SH"], period="1m", start_time="20250801")
        └── 存为 Parquet，检查数据质量（缺值、时间对齐）

Step 2  分析 spread 特征
        ├── 计算每日 spread = ETF日内涨跌幅 - AU日内涨跌幅
        ├── 统计 spread 的日内分布（是否围绕0波动？标准差多大？）
        ├── 偏离后的回归速度（偏离1σ后多少分钟回归？）
        ├── 不同时段（早盘/午盘）、不同市场环境的行为差异
        └── 可视化输出（Jupyter notebook）

Step 3  回测模拟
        ├── 用历史数据跑策略逻辑
        ├── 统计胜率、平均盈亏比、最大连亏、收益曲线
        ├── 参数敏感性分析（哪些参数组合比较稳健）
        └── 产出：一份回测报告 + 初始参数选择
```

**决策点：** 回测结果不理想 → 策略到此为止，不浪费时间写交易系统。

### Phase 1：核心系统搭建

> 前提：Phase 0 回测通过

```
Step 4  实现数据模块
        └── 实时订阅 + 滑动窗口 + 数据异常检测

Step 5  实现策略引擎
        └── spread计算 + Z-Score信号生成 + 基础风控检查

Step 6  实现执行模块（模拟引擎）
        └── 虚拟账户 + 模拟成交 + 统一接口

Step 7  实现记录模块
        └── SQLite建表 + 自动记录trades/signals/daily_summary

Step 8  实现通知模块（飞书机器人）
        ├── FeishuNotifier 类（Webhook POST，支持签名）
        ├── 接入点：成交后通知、风控触发通知、收盘汇总通知、异常告警
        └── 防刷控制（同类通知最短间隔、每日上限）

Step 9  实现可视化仪表盘（Streamlit）
        ├── 盘中监控页：Spread实时图、持仓状态、信号列表
        ├── 交易复盘页：PnL曲线、交易明细表、盈亏分布
        ├── Spread分析页：分时热力图、分布直方图、回归速度
        ├── 风控面板页：风控事件时间线、信号过滤分析
        └── 回测报告页（对接Phase 0回测结果）

Step 10 集成测试
        └── 模拟模式端到端跑通：行情→信号→模拟成交→记录→飞书通知→仪表盘可见
```

### Phase 2：模拟交易验证

> 用模拟引擎跑实盘行情，不投入真金白银

```
Step 11  模拟运行2-4周（每天开盘启动系统，飞书通知 + Streamlit 监控）
Step 12  对比分析（模拟 vs 回测偏差、信号频率、风控合理性）
         └── 使用策略健康度页面评估策略稳定性
```

**决策点：** 模拟胜率达标 → 切换实盘；不达标 → 调整参数重新模拟，或放弃。

### Phase 3：实盘交易

```
Step 13  实现 LiveEngine（对接 QMTClient 交易接口 + 成交回报处理）
Step 14  切换实盘（分批建底仓 → 保守运行 → 逐步放开）
Step 15  持续迭代（每周复盘、每月参数检查）
         └── 启用"模拟 vs 实盘对比"页面，监控执行差异
```

---

## 七、技术栈

```
策略项目：Python（独立项目，pip install qmt-bridge-pro 引入客户端）

数据获取：qmt-bridge QMTClient
  ├── subscribe_realtime → 实时行情（WebSocket）
  ├── get_history_ex → 历史K线（REST）
  ├── get_market_snapshot → 实时快照（REST）
  └── get_main_contract → 主力合约查询（REST）

交易执行：qmt-bridge QMTClient
  ├── place_order / place_order_async → 下单
  ├── cancel_order → 撤单
  ├── query_positions / query_asset → 查询
  └── subscribe_trade_events → 成交回报（WebSocket）

数据存储：
  ├── SQLite → 交易日志、信号记录、风控事件
  └── Parquet → 历史K线（回测用）

通知推送：飞书自定义机器人 Webhook
  ├── 零依赖（stdlib urllib.request）
  ├── 支持 v2 签名校验
  └── 交易通知 / 风控告警 / 每日报告 / 系统异常

数据分析：pandas + numpy

可视化仪表盘：Streamlit
  ├── streamlit → 多页面应用框架
  ├── plotly → 交互式图表（悬浮、缩放、框选）
  └── streamlit-autorefresh → 盘中自动刷新

跨平台：qmt-bridge (已有) → Mac ↔ Windows QMT
```

---

## 八、文件结构

```
gold-etf-strategy/
├── pyproject.toml             # 依赖：qmt-bridge, pandas, numpy
├── config.py                  # 运行模式、QMT连接信息、策略参数
├── main.py                    # 启动入口（--mode simulated/live）
│
├── data/
│   ├── feed.py                # QMTClient 实时订阅与分发
│   └── history.py             # 历史数据下载、Parquet 管理
│
├── strategy/
│   ├── spread.py              # spread / z-score 计算
│   └── signal.py              # 信号生成逻辑
│
├── execution/
│   ├── base.py                # ExecutionEngine 抽象接口
│   ├── simulated.py           # 模拟交易引擎
│   └── live.py                # 实盘交易引擎（Phase 3）
│
├── risk/
│   └── manager.py             # 三层风控规则
│
├── notifier/
│   └── feishu.py              # 飞书机器人通知（交易/风控/日报/异常）
│
├── recorder/
│   ├── db.py                  # SQLite 建表与写入
│   └── models.py              # Trade, Signal, DailySummary 数据类
│
├── backtest/
│   ├── runner.py              # 回测引擎
│   └── analysis.py            # 回测结果分析与可视化
│
├── dashboard/
│   ├── app.py                 # Streamlit 入口（多页面导航）
│   └── pages/
│       ├── dashboard.py       # 盘中监控（Spread实时、持仓、信号）
│       ├── trades.py          # 交易复盘（PnL曲线、明细表、分布图）
│       ├── spread.py          # Spread深度分析（热力图、ACF、回归速度）
│       ├── risk.py            # 风控面板（事件时间线、信号过滤分析）
│       ├── backtest.py        # 回测报告（参数敏感性、权益曲线）
│       └── health.py          # 策略健康度（漂移检测、滚动指标）
│
├── storage/
│   ├── history/               # Parquet 历史K线
│   └── trades.db              # SQLite 交易数据库
│
└── notebooks/
    └── spread_analysis.ipynb  # Phase 0 数据探索
```

---

## 九、qmt-bridge 关键接口速查

策略开发中最常用的 QMTClient 调用汇总：

```python
from qmt_bridge import QMTClient

client = QMTClient("192.168.x.x", port=8000, api_key="xxx")

# ── 数据 ──────────────────────────────────────

# 主力合约
client.get_main_contract("AU.SHFE")

# 下载历史数据（服务端缓存）
client.download_history_contracts()
client.download_batch(["518880.SH"], period="1m", start_time="20250801", end_time="20260211")

# 读取历史K线（返回 {stock: DataFrame}）
client.get_history_ex(["518880.SH"], period="1m", start_time="20250801")
client.get_history_ex(["AU2506.SHFE"], period="1m", start_time="20250801")

# 实时快照
client.get_market_snapshot(["518880.SH", "AU2506.SHFE"])

# 实时订阅（WebSocket，异步）
await client.subscribe_realtime(["518880.SH", "AU2506.SHFE"], callback=on_tick, period="tick")

# ── 交易 ──────────────────────────────────────

# 下单（限价买入100股）
client.place_order(stock_code="518880.SH", order_type=23, order_volume=100, price_type=11, price=6.50, strategy_name="gold_etf_swing")

# 撤单
client.cancel_order(order_id=12345)

# 查持仓
client.query_positions()
client.query_single_position("518880.SH")

# 查余额
client.query_asset()

# 查成交
client.query_trades()

# 成交回报订阅（WebSocket，异步）
await client.subscribe_trade_events(callback=on_trade)

# ── 辅助 ──────────────────────────────────────

# 交易日历
client.is_trading_date("SH", "20260211")
client.get_trading_dates("SH", start_time="20260101", end_time="20260301")
client.get_trading_period("518880.SH")
client.get_holidays()

# 合约信息
client.get_batch_instrument_detail(["AU2506.SHFE", "518880.SH"])
```

---

## 十、第一步行动

**现在可以开始：Phase 0 · Step 1 + Step 2**

1. 通过 QMTClient 下载 AU主力合约和 518880 最近6个月的1分钟K线数据
2. 计算每日的 spread 序列
3. 画图看看 spread 的分布和回归特征

这一步完成后，就能判断后面还值不值得继续做。

**qmt-bridge 本身不需要任何修改。**
