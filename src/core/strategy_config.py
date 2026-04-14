"""
策略配置模块 - 支持多币种多策略配置
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Strategy:
    """单个策略配置"""
    name: str                    # 策略名称
    enabled: bool = True         # 是否启用
    
    # 评分条件
    min_total_score: float = 5.0
    min_macd: float = 0.0
    min_boll: float = 0.0
    min_rsi: float = 0.0
    min_kdj: float = 0.0
    min_volume: float = 0.0
    min_trend: float = 0.0
    
    # 卖出条件
    sell_threshold: float = 3.0
    
    # 仓位配置
    position_pct: float = 0.1    # 仓位百分比
    
    # 风控（优化版：止损2.5%，止盈4%，更适合15分钟K线）
    stop_loss_pct: float = 2.5
    take_profit_pct: float = 4.0
    
    # 描述
    description: str = ""
    win_rate: float = 0.0        # 历史胜率
    avg_profit: float = 0.0      # 历史平均收益


@dataclass
class SymbolConfig:
    """币种配置"""
    symbol: str
    enabled: bool = True
    strategies: List[Strategy] = field(default_factory=list)


# 预定义的高胜率策略（基于回测结果）
DEFAULT_STRATEGIES = {
    "BTCUSDT": [
        Strategy(
            name="策略1: 高分买入",
            enabled=True,
            min_total_score=7.0,  # 提高到7.0，减少噪音信号
            min_macd=0.0,
            min_boll=0.0,
            min_rsi=0.0,
            min_kdj=0.0,
            min_volume=0.0,
            min_trend=0.0,
            sell_threshold=3.0,
            position_pct=0.15,
            stop_loss_pct=2.5,  # 优化为止损2.5%
            take_profit_pct=4.0,  # 优化为止盈4%
            description="总分≥7.0买入，止损2.5%止盈4%，盈亏比1:1.6",
            win_rate=72.4,
            avg_profit=4.83
        ),
        Strategy(
            name="策略2: 高分+RSI",
            enabled=False,
            min_total_score=5.5,
            min_macd=0.0,
            min_boll=0.0,
            min_rsi=0.5,
            min_kdj=0.0,
            min_volume=0.0,
            min_trend=0.0,
            sell_threshold=3.0,
            position_pct=0.15,
            stop_loss_pct=5.0,
            take_profit_pct=15.0,
            description="总分≥5.5且RSI≥0.5买入，胜率71.4%，平均收益4.43%",
            win_rate=71.4,
            avg_profit=4.43
        ),
    ],
    "ETHUSDT": [
        Strategy(
            name="策略1: 高分+趋势",
            enabled=True,
            min_total_score=7.0,  # 提高到7.0
            min_macd=0.0,
            min_boll=0.0,
            min_rsi=0.0,
            min_kdj=0.0,
            min_volume=0.0,
            min_trend=0.5,
            sell_threshold=3.0,
            position_pct=0.15,
            stop_loss_pct=2.5,  # 优化为止损2.5%
            take_profit_pct=4.0,  # 优化为止盈4%
            description="总分≥7.0且趋势≥0.5买入，止损2.5%止盈4%",
            win_rate=80.0,
            avg_profit=3.36
        ),
        Strategy(
            name="策略2: 高分+KDJ",
            enabled=False,
            min_total_score=5.5,
            min_macd=0.0,
            min_boll=0.0,
            min_rsi=0.0,
            min_kdj=1.0,
            min_volume=0.0,
            min_trend=0.0,
            sell_threshold=3.0,
            position_pct=0.15,
            stop_loss_pct=5.0,
            take_profit_pct=20.0,
            description="总分≥5.5且KDJ≥1.0买入，胜率75.0%，平均收益7.48%",
            win_rate=75.0,
            avg_profit=7.48
        ),
    ],
    "SOLUSDT": [
        Strategy(
            name="策略1: 基础高分",
            enabled=True,
            min_total_score=7.0,  # 提高到7.0，减少SOL噪音信号
            min_macd=0.0,
            min_boll=0.0,
            min_rsi=0.0,
            min_kdj=0.0,
            min_volume=0.0,
            min_trend=0.0,
            sell_threshold=3.0,
            position_pct=0.1,
            stop_loss_pct=2.5,  # 优化为止损2.5%
            take_profit_pct=4.0,  # 优化为止盈4%
            description="总分≥7.0买入，止损2.5%止盈4%（高胜率设计）",
            win_rate=54.0,
            avg_profit=1.13
        ),
        Strategy(
            name="策略2: MACD+KDJ强势",
            enabled=False,
            min_total_score=0.0,
            min_macd=2.0,
            min_boll=0.0,
            min_rsi=0.0,
            min_kdj=1.0,
            min_volume=0.0,
            min_trend=0.0,
            sell_threshold=3.0,
            position_pct=0.2,
            stop_loss_pct=5.0,
            take_profit_pct=25.0,
            description="MACD≥2且KDJ≥1买入，胜率100%（样本3次），平均收益11.80%",
            win_rate=100.0,
            avg_profit=11.80
        ),
    ],
}


def get_default_symbol_config(symbol: str) -> SymbolConfig:
    """获取币种的默认配置"""
    strategies = DEFAULT_STRATEGIES.get(symbol, [Strategy(name="默认策略")])
    return SymbolConfig(
        symbol=symbol,
        enabled=True,
        strategies=strategies
    )
