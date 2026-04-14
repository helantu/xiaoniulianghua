"""
网格抄底策略 - 大跌时自动分批买入
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class GridConfig:
    """网格策略配置"""
    symbol: str
    enabled: bool = True
    
    # 触发条件
    drop_pct_trigger: float = 10.0      # 首次触发跌幅 (%)
    drop_pct_step: float = 10.0         # 每档跌幅间隔 (%)
    
    # 仓位配置
    initial_position_pct: float = 0.5   # 首次抄底仓位 (50%)
    add_position_pct: float = 0.2       # 每跌一档加仓 (20%)
    max_position_pct: float = 0.9       # 最大总仓位 (90%)
    
    # 止盈
    take_profit_pct: float = 15.0       # 止盈目标 (%)
    
    # 风控
    max_drop_pct: float = 50.0          # 最大跌幅限制，超过停止加仓
    stop_loss_pct: float = 60.0         # 止损线 (%)


class GridStrategy:
    """网格抄底策略实现"""
    
    def __init__(self, config: GridConfig):
        self.config = config
        self.grid_levels: Dict[float, bool] = {}  # 价格档位 -> 是否已买入
        self.base_price: Optional[float] = None   # 基准价格
        self.total_invested: float = 0.0
        self.avg_cost: float = 0.0
        self.position_qty: float = 0.0
        
    def update_price(self, current_price: float) -> Optional[dict]:
        """
        更新价格，检查是否触发买入
        返回: {'action': 'BUY', 'quantity_pct': x} 或 None
        """
        if not self.config.enabled:
            return None
            
        # 初始化基准价格
        if self.base_price is None:
            self.base_price = current_price
            self._init_grid_levels()
            return None
        
        # 计算当前跌幅
        drop_pct = (self.base_price - current_price) / self.base_price * 100
        
        # 检查是否触发首次买入
        if drop_pct >= self.config.drop_pct_trigger:
            # 找到对应的档位
            level = int(drop_pct / self.config.drop_pct_step)
            level_price = self.base_price * (1 - level * self.config.drop_pct_step / 100)
            
            # 检查是否已买入该档位
            if level_price not in self.grid_levels or not self.grid_levels[level_price]:
                # 计算买入仓位
                if level == 0:
                    buy_pct = self.config.initial_position_pct
                else:
                    buy_pct = self.config.add_position_pct
                
                # 检查总仓位限制
                total_position = self._calc_total_position(current_price)
                if total_position + buy_pct > self.config.max_position_pct:
                    buy_pct = max(0, self.config.max_position_pct - total_position)
                
                if buy_pct > 0:
                    self.grid_levels[level_price] = True
                    self._update_position(current_price, buy_pct)
                    return {
                        'action': 'BUY',
                        'quantity_pct': buy_pct,
                        'reason': f'网格抄底: 跌幅{drop_pct:.1f}%, 档位{level}',
                        'level': level,
                        'drop_pct': drop_pct
                    }
        
        return None
    
    def check_sell(self, current_price: float) -> Optional[dict]:
        """
        检查是否触发止盈卖出
        """
        if self.position_qty <= 0 or self.avg_cost <= 0:
            return None
        
        profit_pct = (current_price - self.avg_cost) / self.avg_cost * 100
        
        if profit_pct >= self.config.take_profit_pct:
            return {
                'action': 'SELL',
                'quantity_pct': 1.0,  # 卖出全部
                'reason': f'网格止盈: 盈利{profit_pct:.1f}%'
            }
        
        # 止损检查
        if profit_pct <= -self.config.stop_loss_pct:
            return {
                'action': 'SELL',
                'quantity_pct': 1.0,
                'reason': f'网格止损: 亏损{profit_pct:.1f}%'
            }
        
        return None
    
    def check_extreme(self, current_price: float, klines: list) -> Optional[dict]:
        """
        检查极端行情，需要平仓
        """
        if len(klines) < 2:
            return None
        
        # 计算最近一根K线的涨跌幅
        last_close = float(klines[-1][4])
        prev_close = float(klines[-2][4])
        change_pct = abs(last_close - prev_close) / prev_close * 100
        
        # 极端行情：单根K线涨跌超过15%
        if change_pct > 15:
            if self.position_qty > 0:
                return {
                    'action': 'SELL',
                    'quantity_pct': 1.0,
                    'reason': f'极端行情平仓: 单根K线波动{change_pct:.1f}%'
                }
        
        return None
    
    def _init_grid_levels(self):
        """初始化网格档位"""
        for i in range(10):  # 预计算10档
            level_price = self.base_price * (1 - i * self.config.drop_pct_step / 100)
            self.grid_levels[level_price] = False
    
    def _calc_total_position(self, current_price: float) -> float:
        """计算当前仓位占比"""
        # 简化计算，实际需要根据账户总资产
        return sum(1 for v in self.grid_levels.values() if v) * self.config.add_position_pct
    
    def _update_position(self, price: float, qty_pct: float):
        """更新持仓信息"""
        new_invest = qty_pct * price
        total_invest = self.total_invested + new_invest
        self.position_qty += qty_pct
        if total_invest > 0:
            self.avg_cost = (self.avg_cost * self.total_invested + price * new_invest) / total_invest
        self.total_invested = total_invest
    
    def reset(self):
        """重置策略状态"""
        self.grid_levels = {}
        self.base_price = None
        self.total_invested = 0.0
        self.avg_cost = 0.0
        self.position_qty = 0.0
    
    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            'base_price': self.base_price,
            'avg_cost': self.avg_cost,
            'position_qty': self.position_qty,
            'grid_levels': {k: v for k, v in self.grid_levels.items()},
            'total_invested': self.total_invested
        }
