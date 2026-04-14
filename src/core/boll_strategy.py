"""
布林带策略 - 低买高卖，支持反手做空
"""
from dataclasses import dataclass
from typing import Optional, List
import numpy as np


@dataclass
class BollConfig:
    """布林带策略配置"""
    symbol: str
    enabled: bool = True
    
    # 布林带参数
    period: int = 20
    std_dev: float = 2.0
    
    # 交易参数
    position_pct: float = 0.3        # 每次交易仓位
    
    # 止盈止损
    take_profit_pct: float = 8.0     # 止盈 (%)
    stop_loss_pct: float = 5.0       # 止损 (%)
    
    # 极端行情
    extreme_change_pct: float = 10.0  # 极端行情阈值
    
    # 做空设置
    short_enabled: bool = True       # 是否允许做空


class BollStrategy:
    """布林带策略实现"""
    
    def __init__(self, config: BollConfig):
        self.config = config
        self.position: str = 'NONE'     # NONE, LONG, SHORT
        self.entry_price: float = 0.0
        self.highest_price: float = 0.0  # 用于追踪止盈
        self.lowest_price: float = float('inf')
        
    def calculate_bollinger(self, prices: List[float]) -> tuple:
        """
        计算布林带
        返回: (中轨, 上轨, 下轨)
        """
        if len(prices) < self.config.period:
            return None, None, None
        
        recent_prices = prices[-self.config.period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        upper = middle + self.config.std_dev * std
        lower = middle - self.config.std_dev * std
        
        return middle, upper, lower
    
    def analyze(self, klines: list) -> Optional[dict]:
        """
        分析K线数据，返回交易信号
        """
        if not self.config.enabled or len(klines) < self.config.period:
            return None
        
        prices = [float(k[4]) for k in klines]
        current_price = prices[-1]
        
        middle, upper, lower = self.calculate_bollinger(prices)
        if middle is None:
            return None
        
        # 更新追踪价格
        if self.position == 'LONG':
            self.highest_price = max(self.highest_price, current_price)
        elif self.position == 'SHORT':
            self.lowest_price = min(self.lowest_price, current_price)
        
        # 检查极端行情
        extreme_signal = self._check_extreme(klines)
        if extreme_signal:
            return extreme_signal
        
        # 检查止盈止损
        exit_signal = self._check_exit(current_price)
        if exit_signal:
            return exit_signal
        
        # 布林带交易逻辑
        if self.position == 'NONE':
            # 没有持仓，寻找入场机会
            if current_price <= lower:
                # 价格触及下轨，做多
                self.position = 'LONG'
                self.entry_price = current_price
                self.highest_price = current_price
                return {
                    'action': 'BUY',
                    'quantity_pct': self.config.position_pct,
                    'reason': f'布林带下轨做多: 价格{current_price:.4f} <= 下轨{lower:.4f}'
                }
            
            elif current_price >= upper and self.config.short_enabled:
                # 价格触及上轨，做空
                self.position = 'SHORT'
                self.entry_price = current_price
                self.lowest_price = current_price
                return {
                    'action': 'SHORT',
                    'quantity_pct': self.config.position_pct,
                    'reason': f'布林带上轨做空: 价格{current_price:.4f} >= 上轨{upper:.4f}'
                }
        
        elif self.position == 'LONG':
            # 持有多单，寻找平仓或反手机会
            if current_price >= upper:
                # 价格触及上轨，平多开空
                self.position = 'SHORT'
                old_entry = self.entry_price
                self.entry_price = current_price
                self.lowest_price = current_price
                return {
                    'action': 'FLIP_SHORT',  # 平多开空
                    'quantity_pct': self.config.position_pct,
                    'reason': f'布林带上轨反手做空: 价格{current_price:.4f} >= 上轨{upper:.4f}'
                }
        
        elif self.position == 'SHORT':
            # 持有空单，寻找平仓或反手机会
            if current_price <= lower:
                # 价格触及下轨，平空开多
                self.position = 'LONG'
                self.entry_price = current_price
                self.highest_price = current_price
                return {
                    'action': 'FLIP_LONG',  # 平空开多
                    'quantity_pct': self.config.position_pct,
                    'reason': f'布林带下轨反手做多: 价格{current_price:.4f} <= 下轨{lower:.4f}'
                }
        
        return None
    
    def _check_exit(self, current_price: float) -> Optional[dict]:
        """检查止盈止损"""
        if self.position == 'NONE' or self.entry_price <= 0:
            return None
        
        if self.position == 'LONG':
            profit_pct = (current_price - self.entry_price) / self.entry_price * 100
            
            # 止盈
            if profit_pct >= self.config.take_profit_pct:
                self.position = 'NONE'
                return {
                    'action': 'SELL',
                    'quantity_pct': 1.0,
                    'reason': f'布林带止盈: 盈利{profit_pct:.1f}%'
                }
            
            # 止损
            if profit_pct <= -self.config.stop_loss_pct:
                self.position = 'NONE'
                return {
                    'action': 'SELL',
                    'quantity_pct': 1.0,
                    'reason': f'布林带止损: 亏损{profit_pct:.1f}%'
                }
        
        elif self.position == 'SHORT':
            profit_pct = (self.entry_price - current_price) / self.entry_price * 100
            
            # 止盈 (空单盈利)
            if profit_pct >= self.config.take_profit_pct:
                self.position = 'NONE'
                return {
                    'action': 'COVER',  # 平空
                    'quantity_pct': 1.0,
                    'reason': f'布林带止盈(空): 盈利{profit_pct:.1f}%'
                }
            
            # 止损 (空单亏损)
            if profit_pct <= -self.config.stop_loss_pct:
                self.position = 'NONE'
                return {
                    'action': 'COVER',  # 平空
                    'quantity_pct': 1.0,
                    'reason': f'布林带止损(空): 亏损{profit_pct:.1f}%'
                }
        
        return None
    
    def _check_extreme(self, klines: list) -> Optional[dict]:
        """检查极端行情"""
        if len(klines) < 2 or self.position == 'NONE':
            return None
        
        last_close = float(klines[-1][4])
        prev_close = float(klines[-2][4])
        change_pct = abs(last_close - prev_close) / prev_close * 100
        
        if change_pct >= self.config.extreme_change_pct:
            # 极端行情，平仓
            old_position = self.position
            self.position = 'NONE'
            
            if old_position == 'LONG':
                return {
                    'action': 'SELL',
                    'quantity_pct': 1.0,
                    'reason': f'极端行情平仓: 单根K线波动{change_pct:.1f}%'
                }
            elif old_position == 'SHORT':
                return {
                    'action': 'COVER',
                    'quantity_pct': 1.0,
                    'reason': f'极端行情平仓: 单根K线波动{change_pct:.1f}%'
                }
        
        return None
    
    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            'position': self.position,
            'entry_price': self.entry_price,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price
        }
    
    def reset(self):
        """重置策略"""
        self.position = 'NONE'
        self.entry_price = 0.0
        self.highest_price = 0.0
        self.lowest_price = float('inf')
