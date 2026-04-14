"""
剥头皮2.0网格策略配置
震荡行情中高频低买高卖，捕捉布林带区间内的价格波动

核心逻辑（2.0升级版）：
  买入信号（三重共振）：
    1. 价格 <= 布林带下轨 * 1.005（紧贴下轨）
    2. RSI < rsi_oversold（默认35，超卖信号）
    3. 1小时EMA50方向向上 OR 价格在1小时EMA50之上（趋势过滤，防逆势）
  止盈目标：动态止盈
    - 布林带宽度 > boll_wide_threshold → 止盈 take_profit_wide_pct（宽幅行情用大止盈）
    - 布林带宽度 <= boll_wide_threshold → 止盈 take_profit_narrow_pct（震荡行情用小止盈）
  止损线：买入均价下方 stop_loss_pct%，快速止损
  冷却期：止损后 N 分钟不开同一币，防止连续亏损

网格加仓：
  价格继续下跌到更低档位时，允许补仓（最多3次），拉低均价
  每次补仓后重新计算止盈止损位置

手续费估算（币安现货）：
  挂单买入：0.1%
  挂单卖出：0.1%
  合计摩擦成本：0.2%
  → 每笔止盈至少要 > 0.2% 才有钱赚

2.0 相较于 1.0 的主要改进：
  1. 去掉弱信号入场（RSI<45），只保留 RSI<35 强信号
  2. 加入1小时EMA50趋势方向过滤，防止逆势入场
  3. 加入动态止盈，根据布林带宽窄自动调整目标
  4. 入场条件收紧（1.01→1.005），减少假突破
"""
from dataclasses import dataclass


@dataclass
class ScalpingConfig:
    """剥头皮2.0策略配置"""
    symbol: str

    # ==================== 信号条件 ====================
    enabled: bool = True

    # RSI超卖阈值（低于此值触发买入信号）
    rsi_oversold: float = 35.0
    # RSI超买阈值（高于此值触发卖出信号）
    rsi_overbought: float = 70.0

    # 布林带参数
    boll_period: int = 20        # 布林带周期
    boll_std: float = 2.0        # 布林带标准差倍数

    # 入场下轨误差（2.0收紧为0.5%，原来是1%）
    lower_band_tolerance: float = 1.005   # price <= boll_lower * lower_band_tolerance

    # ==================== 动态止盈（2.0新增） ====================
    # 布林带宽度阈值：宽度 = (upper - lower) / mid * 100
    # 宽于此值认为是"宽幅行情"，用更大止盈；窄于此值是"震荡"，用小止盈
    boll_wide_threshold: float = 3.0      # 布林带宽度3%为分界线

    take_profit_wide_pct: float = 0.8     # 宽幅行情止盈 0.8%
    take_profit_narrow_pct: float = 0.35  # 震荡行情止盈 0.35%（覆盖手续费后净赚约0.15%）

    # 兼容旧版：固定止盈（动态止盈关闭时使用）
    take_profit_pct: float = 0.5          # 默认止盈 0.5%（备用）
    dynamic_tp_enabled: bool = True       # 是否启用动态止盈

    # ==================== 止损 ====================
    # 止损：价格跌破 avg_cost * (1 - stop_loss_pct/100) 强制平仓
    stop_loss_pct: float = 0.3            # 止损线 0.3%（最大单笔亏损）

    # ==================== 1小时趋势过滤（2.0新增） ====================
    trend_filter_enabled: bool = True     # 是否启用1小时趋势过滤
    trend_ema_period: int = 50            # 1小时EMA周期（默认EMA50）

    # ==================== 仓位管理 ====================
    # 每次买入仓位（占账户可用资金的百分比）
    position_pct: float = 0.10            # 10%
    # 最大总仓位（同一币最多持有总资金的百分比）
    max_position_pct: float = 0.30        # 30%
    # 最大加仓次数（价格继续下跌时补仓次数）
    max_add_positions: int = 3            # 最多加仓3次（4笔买入）

    # ==================== 冷却 & 风控 ====================
    # 止损后冷却期（秒）
    cooldown_seconds: int = 15 * 60       # 15分钟
    # 最大连续止损次数（超过后暂停该币种）
    max_consecutive_losses: int = 5
    # 每日最大交易次数（该币）
    max_daily_trades: int = 20

    # ==================== K线周期 ====================
    kline_interval: str = '5m'            # 剥头皮用5分钟K线，高频
    trend_kline_interval: str = '1h'      # 趋势过滤用1小时K线
