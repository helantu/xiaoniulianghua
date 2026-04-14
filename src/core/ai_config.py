"""
AI交易模块配置 - 自适应多策略引擎
资金规模: 100~500 USDT（取300作为基准）
风控: 日亏上限20美元，策略亏损自动调整
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AIAccountConfig:
    """账户级配置"""
    # 资金
    min_balance: float = 100.0       # 最低资金门槛
    max_balance: float = 500.0       # 最高资金（超过后降仓）
    default_balance: float = 300.0  # 基准资金（用于仓位计算）

    # 风控
    daily_loss_limit: float = 20.0   # 日最大亏损（USDT）
    max_single_loss: float = 5.0     # 单笔最大亏损
    max_position_pct: float = 0.25   # 单币最大仓位（25%）
    single_trade_pct: float = 0.15   # 单笔交易金额比例（15%）

    # 目标
    daily_target: float = 10.0       # 日目标收益
    weekly_target: float = 50.0      # 周目标

    # 扫描参数
    scan_interval: int = 60          # AI扫描间隔（秒，每分钟）
    review_interval: int = 3600     # 复盘间隔（秒，每小时）
    min_trades_for_review: int = 3  # 至少需要N笔交易才复盘


@dataclass
class AIStrategyParams:
    """单策略可调参数"""
    name: str = ""

    # 仓位
    position_pct: float = 0.15       # 仓位比例（提升到15%）
    max_position_pct: float = 0.30   # 单币最大仓位

    # 止盈止损（原始值，可被AI调整）
    stop_loss_pct: float = 1.0       # 止损%
    take_profit_pct: float = 2.0     # 止盈%

    # RSI阈值
    rsi_oversold: float = 35.0
    rsi_overbought: float = 65.0
    rsi_neutral_low: float = 45.0
    rsi_neutral_high: float = 55.0

    # 均线参数
    ema_fast: int = 20
    ema_slow: int = 50

    # 布林带
    boll_period: int = 20
    boll_std: float = 2.0

    # 评分权重（AI可动态调整）
    weight: float = 1.0              # 策略权重（初始1.0）
    enabled: bool = True
    cooldown_seconds: int = 300      # 冷却时间（5分钟）

    # 动态调整记录
    total_trades: int = 0
    win_count: int = 0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.win_count / self.total_trades

    @property
    def profit_factor(self) -> float:
        if self.avg_loss == 0:
            return 0.0
        return abs(self.avg_win / self.avg_loss) if self.avg_loss < 0 else 0.0


@dataclass
class AIConfig:
    """AI交易全局配置"""
    account: AIAccountConfig = field(default_factory=AIAccountConfig)

    # 监控币种（AI自由选择，不限制）
    symbols: list = field(default_factory=lambda: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'])

    # K线周期（多周期分析）
    primary_kline: str = '15m'       # 主分析周期
    confirm_kline: str = '5m'        # 确认周期
    trend_kline: str = '1h'          # 趋势周期

    # 策略配置（4个子策略）
    momentum_params: AIStrategyParams = field(default_factory=lambda: AIStrategyParams(
        name="Momentum", stop_loss_pct=0.8, take_profit_pct=2.0, position_pct=0.15
    ))
    mean_reversion_params: AIStrategyParams = field(default_factory=lambda: AIStrategyParams(
        name="MeanReversion", stop_loss_pct=1.0, take_profit_pct=1.5, position_pct=0.15
    ))
    breakout_params: AIStrategyParams = field(default_factory=lambda: AIStrategyParams(
        name="Breakout", stop_loss_pct=1.2, take_profit_pct=2.5, position_pct=0.12
    ))
    volume_params: AIStrategyParams = field(default_factory=lambda: AIStrategyParams(
        name="VolumeConfirm", stop_loss_pct=0.8, take_profit_pct=1.8, position_pct=0.15
    ))

    # 自适应参数
    adaptive_enabled: bool = True    # 启用自适应
    min_win_rate_for_up: float = 0.60  # 胜率>60%才考虑加权重
    min_profit_factor_for_up: float = 1.5  # 盈亏比>1.5才考虑加权重
    max_weight: float = 3.0         # 最大权重
    min_weight: float = 0.1         # 最小权重（不完全关闭）

    # 每日亏损后行为
    after_daily_loss_pct: float = 0.5  # 日亏后仓位降为50%
    pause_on_consecutive_losses: int = 3  # 连续N亏后暂停

    def get_all_strategies(self) -> Dict[str, AIStrategyParams]:
        return {
            'Momentum': self.momentum_params,
            'MeanReversion': self.mean_reversion_params,
            'Breakout': self.breakout_params,
            'VolumeConfirm': self.volume_params,
        }
