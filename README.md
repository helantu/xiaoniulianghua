# 🐂 小牛量化交易系统 v1.0

> 一个基于币安API的智能量化交易系统，支持现货/合约交易，集成MACD/BOLL/RSI/KDJ等多维技术指标，采用9分制评分机制

## 🌟 核心特性

### 1. 智能分析引擎
- **9分制综合评分**：MACD(2分) + 布林带(2分) + RSI(1.5分) + KDJ(1.5分) + 成交量(1分) + 均线趋势(1分)
- **多维技术指标**：
  - MACD：趋势跟踪、动能指标
  - 布林带：超买超卖判断
  - RSI：强弱指数
  - KDJ：随机指标
  - 成交量分析：配合趋势判断
  - 均线系统：MA7/MA25/MA99三重滤波

- **灵活的评分规则**：所有指标参数可动态调整，支持后续自定义规则

### 2. 量化交易引擎
- **规则驱动架构**：可扩展的规则系统，支持自定义策略
- **内置规则**：
  - 评分买入规则：评分≥6分时买入
  - 评分卖出规则：评分≤2分时卖出
  - 止损规则：亏损超过阈值自动平仓
  - 止盈规则：盈利达到目标自动获利
  - 合约做多规则：可选的杠杆交易

- **风险管理**：
  - 单币最大仓位限制
  - 止损/止盈自动控制
  - 仓位百分比灵活配置
  - 资金管理规则

### 3. 币安API集成
- **现货交易**：市价/限价买卖
- **合约交易**：带杠杆的多空交易
- **订单管理**：下单、撤单、查询
- **账户管理**：余额、持仓查询
- **行情数据**：K线、行情、价格查询
- **支持测试网络**：开发调试友好

### 4. 可视化交互界面
- **深色护眼主题**：专业的暗黑风格
- **实时监控面板**：
  - 币种实时评分卡片
  - 账户余额展示
  - 开仓持仓管理

- **监控日志面板**：
  - 实时扫描日志
  - 彩色分级显示
  - 完整的操作记录

- **成交记录面板**：
  - 历史成交查看
  - 成交详情（价格、数量、盈亏）
  - 评分记录

- **营收统计面板**：
  - 累计盈亏统计
  - 每日盈亏统计
  - 营收目标进度条
  - 盈亏曲线图表

- **参数调节面板**：
  - 交易模式切换（模拟/实盘）
  - API配置管理
  - 扫描参数调整
  - 评分阈值设置
  - 仓位与风控参数
  - 合约参数配置
  - 营收目标设置

- **规则管理面板**：
  - 规则启用/禁用
  - 规则信息展示
  - 自定义规则开发指南

## 📁 项目结构

```
小牛量化/
├── main.py                      # 启动文件
├── config.env                   # API配置（需填入）
├── requirements.txt             # 依赖清单
│
├── src/
│   ├── core/                    # 核心引擎
│   │   ├── __init__.py
│   │   ├── binance_client.py    # 币安API客户端
│   │   ├── analyzer.py          # 技术指标分析（9分制）
│   │   ├── rules.py             # 规则引擎（可扩展）
│   │   └── engine.py            # 主交易引擎
│   │
│   ├── ui/                      # 界面模块
│   │   ├── __init__.py
│   │   └── main_window.py       # PyQt5主窗口
│   │
│   └── strategies/              # 策略模块（预留）
│
├── logs/                        # 日志文件
├── data/                        # 数据文件
│   └── trade_data.json         # 成交记录持久化
│
└── README.md                    # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `python-binance`：币安API SDK
- `PyQt5`：用户界面
- `pandas/numpy`：数据分析
- `ta`：技术指标库
- `pyqtgraph`：图表绘制

### 2. 配置币安API

编辑 `config.env`：

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
USE_TESTNET=false    # true=测试网，false=正式网
```

**获取API密钥**：
- 登录 [币安官网](https://www.binance.com)
- 进入账户中心 → API Management
- 创建新的API密钥
- 复制 `API Key` 和 `Secret Key`
- ⚠️ **千万不要在代码中硬编码密钥！**

### 3. 运行程序

```bash
python main.py
```

初次运行会看到：
- PyQt5窗口启动
- 默认监控 BTC、ETH、SOL、DOGE
- 模拟交易模式（不会真实下单）

## 📊 使用指南

### 启动交易引擎

1. 点击左上角 **"▶ 启动引擎"** 按钮
2. 引擎状态将显示为 **"🟢 运行中"**
3. 开始自动扫描和分析

### 监控币种评分

**监控币种面板** 显示实时评分卡片：
- **评分条**：绿色(≥6=买) → 黄色(中性) → 红色(≤2=卖)
- **各维度分数**：MACD、BOLL、RSI、KDJ等
- **当前价格**：实时更新

### 查看成交记录

**成交记录面板**：
- 时间戳、币种、操作类型、成交价格
- 成交数量、成交金额（USDT）
- 盈亏金额（仅卖出时计算）

### 监看营收统计

**营收统计面板**：
- **累计盈亏 + 今日盈亏**：红绿显示
- **营收目标进度**：两条进度条
  - 总目标：默认1000 USDT
  - 每日目标：默认100 USDT
- **盈亏曲线**：历史盈亏累积走势图

### 调整参数

**参数调节面板** 完全可定制：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| **模拟交易** | 不真实下单，仅记录 | ✅ 开启 |
| **扫描间隔** | 每多少秒扫描一次 | 60秒 |
| **K线周期** | 分析用的K线时间 | 15分钟 |
| **监控币种** | 逗号分隔 | BTC、ETH、SOL、DOGE |
| **买入阈值** | 评分≥N时买入 | 6.0分 |
| **卖出阈值** | 评分≤N时卖出 | 2.0分 |
| **每次买入仓位** | 投入比例 | 10% |
| **单币最大仓位** | 防止过度集中 | 30% |
| **止损比例** | 亏损多少自动平 | 5% |
| **止盈比例** | 盈利多少自动卖 | 10% |
| **合约杠杆** | 倍数(1-20x) | 3x |
| **营收目标** | 总目标盈利 | 1000 USDT |

所有参数修改后点击 **"✅ 保存所有参数"** 即可生效。

### 管理交易规则

**规则管理面板**：
- 查看所有已加载的规则
- 点击行后点 **"切换选中规则"** 启用/禁用
- 支持自定义规则（见开发者指南）

## 💡 9分制评分详解

系统采用 **9分制综合评分**，分为6个维度：

### 评分维度
```
┌─────────────────────────────────────────┐
│        技术指标综合评分体系              │
├─────────────────────────────────────────┤
│ MACD (2.0分) - 趋势动能                 │
│  ├─ 多头排列 +0.5分                     │
│  ├─ 零轴上方 +0.5分                     │
│  ├─ 红柱增大 +1.0分                     │
│  └─ 金叉信号 +0.5分(加成)               │
│                                         │
│ 布林带 (2.0分) - 超买超卖               │
│  ├─ 下轨超卖(买入区) 2.0分              │
│  ├─ 中下区间 1.5分                      │
│  ├─ 中轨附近 1.0分                      │
│  ├─ 中上区间 0.5分                      │
│  └─ 上轨超买 0.0分                      │
│                                         │
│ RSI (1.5分) - 强弱指数                  │
│  ├─ RSI<30(超卖) 1.5分                  │
│  ├─ 30-45(偏低) 1.2分                   │
│  ├─ 45-55(中性) 0.8分                   │
│  ├─ 55-70(偏高) 0.4分                   │
│  └─ RSI>70(超买) 0.0分                  │
│                                         │
│ KDJ (1.5分) - 随机指标                  │
│  ├─ 超卖区(K,D<20) +0.8分               │
│  ├─ 偏低(K<50) +0.5分                   │
│  ├─ 金叉信号 +0.7分                     │
│  └─ K在D上 +0.3分                       │
│                                         │
│ 成交量 (1.0分) - 量能                   │
│  ├─ 放量(>2.0x) 1.0分                   │
│  ├─ 温和放量(1.2-2.0x) 0.8分            │
│  ├─ 正常量 0.5分                        │
│  └─ 缩量 0.2分                          │
│                                         │
│ 均线趋势 (1.0分) - 长期趋势              │
│  ├─ 多头排列(价>MA7>MA25) 1.0分         │
│  ├─ 中期看多(价>MA25) 0.7分             │
│  ├─ 长期支撑(价>MA99) 0.4分             │
│  └─ 空头排列 0.0分                      │
│                                         │
│  ╔═══════════════════════════════╗      │
│  ║  总分 = MACD + BOLL + RSI +   ║      │
│  ║        KDJ + VOL + TREND      ║      │
│  ║  ≤2分 = 卖出 | ≥6分 = 买入   ║      │
│  ╚═══════════════════════════════╝      │
└─────────────────────────────────────────┘
```

### 信号含义
- **BUY (买入信号)** ⬆️：评分≥6分，技术面强势
- **SELL (卖出信号)** ⬇️：评分≤2分，技术面弱势
- **HOLD (观望)** ➡️：评分在2-6分之间，等待机会

## 🔧 开发者指南 - 添加自定义规则

小牛量化采用 **规则引擎架构**，允许灵活扩展交易策略。

### 创建自定义规则

编辑 `src/core/rules.py`，添加新规则类：

```python
from .rules import BaseRule, TradeDecision
from .analyzer import SignalScore

class MyCustomRule(BaseRule):
    """我的自定义规则"""
    name = "我的规则"
    description = "规则描述"
    enabled = True
    
    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        """
        评估规则逻辑
        
        参数:
            score: SignalScore - 当前币种的技术面评分
            context: dict - 上下文信息
                ├─ params: 引擎配置参数
                ├─ positions: 当前持仓
                └─ balance: 账户余额
        
        返回:
            TradeDecision - 交易决策，或 None(不操作)
        """
        params = context.get('params', {})
        
        # 自定义判断逻辑
        if score.total_score >= 7.0:
            return TradeDecision(
                should_trade=True,
                action="BUY",
                trade_type="SPOT",
                quantity_pct=0.15,
                reason=f"自定义规则触发: {score.symbol} 评分{score.total_score:.1f}",
                score=score.total_score
            )
        return None
```

### 注册规则

在 `RuleEngine._load_default_rules()` 中添加：

```python
def _load_default_rules(self):
    self._rules = [
        ScoreBasedBuyRule(),
        ScoreBasedSellRule(),
        StopLossRule(),
        TakeProfitRule(),
        MyCustomRule(),  # 👈 添加这行
        FuturesLongRule(),
    ]
```

### 规则开发示例

#### 示例1：MACD金叉买入规则
```python
class MACDCrossRule(BaseRule):
    name = "MACD金叉规则"
    description = "当MACD出现金叉时买入"
    
    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        # 通过 score.details['macd_signal'] 判断
        if '⭐金叉信号' in score.details.get('macd_signal', ''):
            return TradeDecision(
                should_trade=True,
                action="BUY",
                trade_type="SPOT",
                quantity_pct=0.1,
                reason="MACD金叉入场",
                score=score.total_score
            )
        return None
```

#### 示例2：根据仓位控制的规则
```python
class PositionLimitRule(BaseRule):
    name = "仓位限制规则"
    description = "已有持仓时拒绝继续买入"
    
    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        positions = context.get('positions', {})
        
        # 如果已有该币持仓，则不再买入
        if score.symbol in positions:
            return None
        
        # 执行原有逻辑
        if score.total_score >= 6.0:
            return TradeDecision(...)
        return None
```

### 规则上下文 (context)
规则评估时会收到完整上下文：

```python
context = {
    'params': {                    # 引擎配置
        'buy_threshold': 6.0,
        'sell_threshold': 2.0,
        'stop_loss_pct': 5.0,
        'take_profit_pct': 10.0,
        # ... 更多参数
    },
    'positions': {                 # 当前持仓
        'BTCUSDT': {
            'qty': 0.5,
            'entry_price': 45000.0,
            'entry_time': '2024-03-30 14:00:00',
            'amount': 22500.0,
        },
        # ...
    },
    'balance': 8000.0,            # 可用余额 (USDT)
}
```

### 交易决策返回值
```python
TradeDecision(
    should_trade=True,            # 是否执行交易
    action="BUY",                 # BUY / SELL / HOLD
    trade_type="SPOT",            # SPOT / FUTURES
    quantity_pct=0.1,             # 仓位百分比 (10%)
    leverage=1,                   # 杠杆倍数(仅FUTURES)
    reason="买入原因",             # 交易理由（日志记录）
    score=6.5                     # 当前评分
)
```

## ⚙️ 高级配置

### 动态指标参数调整

所有技术指标参数都可动态调整：

```python
from src.core.analyzer import TechnicalAnalyzer

analyzer = TechnicalAnalyzer(params={
    'macd_fast': 12,              # MACD快速EMA
    'macd_slow': 26,              # MACD慢速EMA
    'boll_period': 20,            # 布林带周期
    'boll_std': 2.0,              # 布林带标准差倍数
    'rsi_period': 14,             # RSI周期
    'rsi_oversold': 30,           # RSI超卖阈值
    'rsi_overbought': 70,         # RSI超买阈值
})

# 动态更新
analyzer.update_params({'macd_fast': 11, 'rsi_period': 13})
```

### 多币种自定义监控

```python
engine.update_config({
    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT'],
    'scan_interval': 30,          # 30秒扫描一次
    'kline_interval': '5m',       # 5分钟K线
})
```

### 实盘交易步骤

**⚠️ 操作前请务必：**
1. 在币安测试网络充分测试
2. 从小额开始试盘
3. 确保止损规则生效
4. 实时监看日志和持仓

**开启实盘：**
1. 界面 → 参数调节 → 交易模式
2. **取消勾选** "模拟交易"
3. 输入真实API密钥
4. 点击 "保存并测试连接"
5. 再次确认后启动引擎

## 📝 日志说明

日志分为三级：

| 等级 | 颜色 | 说明 |
|------|------|------|
| ℹ️ **INFO** | 🟢 绿色 | 正常操作信息 |
| ⚠️ **WARNING** | 🟡 黄色 | 警告信息（异常但可继续） |
| ❌ **ERROR** | 🔴 红色 | 错误信息（需要处理） |

常见日志：
```
[16:30:15] 🚀 小牛量化引擎启动 | 📋模拟交易 | 监控: BTC, ETH, SOL, DOGE
[16:30:20] 🔍 开始扫描 [16:30:20] | 周期:15m
[16:30:21]   BTCUSDT: 45230.50 | 评分:7.2/9 | 信号:BUY | [MACD:2.0 BOLL:1.8 RSI:0.9 KDJ:1.2]
[16:30:22]   📊 决策触发: BUY BTCUSDT | 数量:0.022 | 金额:1000.00U | 原因:评分7.2≥阈值6.0，买入信号
[16:30:22]   ✅ [模拟] 成交: BUY BTCUSDT @45230.50 数量:0.022
```

## 🐛 常见问题

### Q: "币安API连接失败"
**A:** 检查：
1. API密钥是否正确复制（无空格）
2. IP地址是否已在币安后台白名单
3. 网络连接是否正常
4. 是否在正确的币安账号获取的密钥

### Q: "K线数据不足，无法分析"
**A:** 系统需要至少30根K线才能计算技术指标，建议使用 ≥15分钟周期

### Q: 评分总是很低（≤2分）
**A:**
1. 市场下跌期间评分会较低（这是正常的保护机制）
2. 检查参数设置是否过于严苛
3. 尝试调整 `买入阈值` 和 `卖出阈值`

### Q: 如何导出成交记录？
**A:** 成交数据自动保存在 `data/trade_data.json`，可用Excel打开编辑

### Q: 能否同时运行多个实例？
**A:** 不建议，会造成仓位混乱。建议创建多个API子账户，每个运行一个实例

## 📊 性能指标

| 指标 | 说明 |
|------|------|
| **扫描延迟** | 4-6币种 每60秒 |
| **数据精度** | ±0.5秒 (基于服务器时间) |
| **内存占用** | ~120-150 MB (PyQt5 + 数据) |
| **CPU占用** | 1-3% (单线程等待) |

## 📄 许可证

MIT License - 自由使用和修改

## 🤝 反馈与建议

发现问题？有好建议？

- 📧 Email: niuquant@example.com
- 💬 Issues: 在项目中提交Issue
- 📢 讨论: 参与开发讨论

## 🔄 更新日志

### v1.0.0 (2026-03-30)
- ✅ 完整的9分制评分系统
- ✅ 可视化PyQt5界面
- ✅ 币安现货/合约支持
- ✅ 规则引擎架构
- ✅ 成交记录与统计
- ✅ 模拟交易模式
- ✅ 完整日志系统

### 规划中...
- 🔄 WebSocket实时行情
- 🔄 更多技术指标（布林带宽度、ATR等）
- 🔄 机器学习评分优化
- 🔄 策略回测模块
- 🔄 Web仪表板
- 🔄 Email/微信告警

---

**小牛量化** - 让量化交易更简单！🚀

_Powered by Python + PyQt5 + Binance API_
