"""
剥头皮2.0网格策略 - 高频低买高卖（升级版）

在震荡行情中：
  布林带下轨附近买入 → 布林带中轨附近卖出 → 循环套利
  价格继续下跌 → 补仓拉低均价 → 更早止盈

2.0 核心升级：
  1. 入场三重共振（缺一不可）：
     - 价格 <= 布林带下轨 * lower_band_tolerance（紧贴下轨，收紧为0.5%误差）
     - RSI < rsi_oversold（必须超卖，去掉弱信号入场）
     - 1小时EMA50趋势向上（防止逆势下跌被套）
  2. 动态止盈：
     - 布林带宽幅行情 → 止盈0.8%
     - 布林带窄幅震荡 → 止盈0.35%
     - 自动根据当前波动率切换
  3. 去除弱信号（RSI<45入场），彻底消除假信号

关键参数：
  - 止盈：0.35%（震荡）~ 0.8%（宽幅）
  - 止损：0.3%（快速止损，避免扛单）
  - RSI: < 35 超卖信号（强信号，无弱信号）
  - 1小时EMA50：确保顺势操作
  - 最多加仓3次，防止深套
  - 止损后15分钟冷却
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime
from .scalping_config import ScalpingConfig


@dataclass
class ScalpingState:
    """剥头皮策略状态（每个币一个）"""
    symbol: str
    in_position: bool = False           # 当前是否持仓
    avg_cost: float = 0.0              # 平均成本价
    total_qty: float = 0.0             # 总持仓数量
    add_count: int = 0                 # 加仓次数（已用了几次补仓）
    entry_price: float = 0.0           # 首次买入价格
    entry_time: str = ""               # 首次买入时间
    stop_loss_price: float = 0.0       # 止损价
    take_profit_price: float = 0.0     # 止盈价
    tp_triggered: bool = False         # 止盈是否已触发（已挂单）
    sl_triggered: bool = False         # 止损是否已触发

    # 风控计数
    consecutive_losses: int = 0         # 连续止损次数
    daily_trade_count: int = 0          # 今日交易次数
    last_trade_date: str = ""           # 上次交易日期（用于重置日计数）
    cooldown_until: float = 0.0         # 冷却截止时间戳


class ScalpingStrategy:
    """
    剥头皮2.0网格策略

    核心买卖逻辑：
      买入条件（同时满足，三重共振）：
        1. 当前无持仓
        2. 未在冷却期
        3. 价格靠近布林带下轨（close <= boll_lower * lower_band_tolerance）
        4. RSI < rsi_oversold（超卖强信号，35以下）
        5. 1小时EMA50趋势向上（价格 > 1小时EMA50 或 EMA50斜率向上）

      买入后立即：
        - 计算动态止盈价：根据布林带宽窄自动选择止盈幅度
          * 宽幅行情（BB宽度>3%）→ 止盈0.8%
          * 窄幅震荡（BB宽度<=3%）→ 止盈0.35%
        - 计算止损价 = 买入价 * (1 - stop_loss_pct)
        - 记录状态，等待价格触发

      检查持仓状态（每次扫描）：
        1. 止盈触发 → 卖出全部，+1胜场，重置状态
        2. 止损触发 → 卖出全部，+1止损，启动冷却期，重置状态
        3. 价格继续下跌 + 未达最大加仓次数 → 补仓，拉低均价，重算止盈止损
        4. 无触发 → 继续持有

      强制止盈（有持仓时额外检查）：
        - 有持仓 + RSI > rsi_overbought + 价格 > 成本价 → 提前卖出锁利
    """

    def __init__(self, config: ScalpingConfig):
        self.config = config
        self.state = ScalpingState(symbol=config.symbol)
        self._df: Optional[pd.DataFrame] = None           # 5分钟K线
        self._df_1h: Optional[pd.DataFrame] = None        # 1小时K线（趋势过滤）

    # ==================== 公开接口 ====================

    def update_klines(self, klines: list) -> None:
        """每次扫描时传入5分钟K线数据，计算5分钟指标"""
        self._df = self._klines_to_df(klines)
        if len(self._df) < self.config.boll_period + 5:
            return
        self._calc_indicators(self._df)

    def update_klines_1h(self, klines_1h: list) -> None:
        """传入1小时K线数据，用于趋势方向判断（2.0新增）"""
        if not klines_1h:
            return
        self._df_1h = self._klines_to_df(klines_1h)
        if len(self._df_1h) >= self.config.trend_ema_period + 5:
            self._calc_ema(self._df_1h, self.config.trend_ema_period)

    def should_buy(self) -> bool:
        """
        检查是否应买入（2.0三重共振逻辑）
        条件：布林带下轨 + RSI<35 + 1小时EMA50趋势向上
        """
        if self.state.in_position:
            return False
        if self._is_in_cooldown():
            return False
        if self._is_max_losses():
            return False
        if self._df is None or len(self._df) < self.config.boll_period + 5:
            return False

        price = self._df['close'].iloc[-1]
        boll_lower = self._df['boll_lower'].iloc[-1]
        rsi = self._df['rsi'].iloc[-1]

        # 条件1：价格紧贴布林带下轨（2.0收紧：1.005，原来1.01）
        at_lower_band = price <= boll_lower * self.config.lower_band_tolerance

        # 条件2：RSI超卖（只保留强信号，去掉弱信号RSI<45）
        rsi_signal = rsi < self.config.rsi_oversold

        # 条件3：1小时趋势方向过滤（2.0新增，防逆势入场）
        trend_ok = self._check_trend_filter()

        return at_lower_band and rsi_signal and trend_ok

    def should_sell(self) -> bool:
        """检查是否应卖出（有持仓时检查止盈/止损触发）"""
        if not self.state.in_position:
            return False
        if self._df is None:
            return False

        price = self._df['close'].iloc[-1]
        rsi = self._df['rsi'].iloc[-1]

        # 止盈触发
        if price >= self.state.take_profit_price:
            return True

        # 止损触发
        if price <= self.state.stop_loss_price:
            return True

        # 极端超买 + 持仓盈利 → 提前止盈
        if rsi > self.config.rsi_overbought and price > self.state.entry_price:
            return True

        return False

    def should_add_position(self) -> bool:
        """检查是否应补仓（价格继续下跌时拉低均价）"""
        if not self.state.in_position:
            return False
        if self.state.add_count >= self.config.max_add_positions:
            return False
        if self._df is None:
            return False

        price = self._df['close'].iloc[-1]
        # 持仓均价再跌 stop_loss_pct * 1.5 时补仓
        add_trigger_price = self.state.avg_cost * (1 - self.config.stop_loss_pct * 1.5 / 100)

        return price <= add_trigger_price

    def execute_buy(self, buy_price: float, buy_qty: float) -> None:
        """执行买入后，更新状态并计算动态止盈止损（2.0动态止盈）"""
        if not self.state.in_position:
            # 首次买入
            self.state.in_position = True
            self.state.entry_price = buy_price
            self.state.entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.state.total_qty = buy_qty
            self.state.avg_cost = buy_price
            self.state.add_count = 0
        else:
            # 补仓：重新计算均价
            total_cost = self.state.avg_cost * self.state.total_qty + buy_price * buy_qty
            self.state.total_qty += buy_qty
            self.state.avg_cost = total_cost / self.state.total_qty
            self.state.add_count += 1

        # 止损：以最新均价为基准
        self.state.stop_loss_price = self.state.avg_cost * (1 - self.config.stop_loss_pct / 100)

        # 动态止盈（2.0新增）
        tp_pct = self._get_dynamic_tp_pct()
        if self.state.add_count == 0:
            # 首次买入：止盈以买入价为基准
            self.state.take_profit_price = buy_price * (1 + tp_pct / 100)
        else:
            # 补仓后：止盈以均价为基准
            self.state.take_profit_price = self.state.avg_cost * (1 + tp_pct / 100)

        self.state.tp_triggered = False
        self.state.sl_triggered = False

    def execute_sell(self, sell_price: float) -> dict:
        """执行卖出，计算盈亏，返回结果"""
        if not self.state.in_position:
            return {'action': 'HOLD', 'reason': '无持仓'}

        sell_value = sell_price * self.state.total_qty
        cost = self.state.avg_cost * self.state.total_qty
        pnl = sell_value - cost
        pnl_pct = pnl / cost * 100 if cost > 0 else 0

        result = {
            'action': 'SELL',
            'qty': self.state.total_qty,
            'sell_price': sell_price,
            'avg_cost': self.state.avg_cost,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'add_count': self.state.add_count,
            'reason': '止盈' if pnl > 0 else '止损',
        }

        if pnl <= 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

        self._reset_state()
        return result

    def get_status(self) -> dict:
        """获取当前剥头皮2.0状态"""
        rsi = 0.0
        boll_width = 0.0
        trend_ok = False
        tp_pct = self.config.take_profit_pct

        if self._df is not None and len(self._df) > 0 and 'rsi' in self._df.columns:
            rsi = float(self._df['rsi'].iloc[-1])

        if self._df is not None and 'boll_upper' in self._df.columns:
            boll_width = self._get_boll_width()
            tp_pct = self._get_dynamic_tp_pct()

        if self.config.trend_filter_enabled:
            trend_ok = self._check_trend_filter()

        return {
            'in_position': self.state.in_position,
            'avg_cost': self.state.avg_cost,
            'total_qty': self.state.total_qty,
            'stop_loss_price': self.state.stop_loss_price,
            'take_profit_price': self.state.take_profit_price,
            'add_count': self.state.add_count,
            'consecutive_losses': self.state.consecutive_losses,
            'in_cooldown': self._is_in_cooldown(),
            'cooldown_remaining': max(0, int(self.state.cooldown_until - datetime.now().timestamp())),
            'rsi': rsi,
            # 2.0新增状态字段
            'boll_width_pct': round(boll_width, 2),
            'dynamic_tp_pct': tp_pct,
            'trend_ok': trend_ok,
        }

    # ==================== 内部方法 ====================

    def _calc_indicators(self, df: pd.DataFrame) -> None:
        """计算布林带和RSI指标"""
        close = df['close']

        boll_period = self.config.boll_period
        mid = close.rolling(window=boll_period).mean()
        std = close.rolling(window=boll_period).std()
        df['boll_upper'] = mid + self.config.boll_std * std
        df['boll_mid'] = mid
        df['boll_lower'] = mid - self.config.boll_std * std

        # RSI (14周期)
        rsi_period = 14
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - 100 / (1 + rs)

    def _calc_ema(self, df: pd.DataFrame, period: int) -> None:
        """计算EMA（用于1小时趋势过滤）"""
        df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    def _get_boll_width(self) -> float:
        """计算当前布林带宽度（%），用于动态止盈判断"""
        if self._df is None or 'boll_upper' not in self._df.columns:
            return 0.0
        row = self._df.iloc[-1]
        upper = row.get('boll_upper', 0)
        lower = row.get('boll_lower', 0)
        mid = row.get('boll_mid', 1)
        if mid <= 0:
            return 0.0
        return (upper - lower) / mid * 100

    def _get_dynamic_tp_pct(self) -> float:
        """
        动态止盈百分比（2.0新增）
        根据布林带宽度自动选择：
          宽幅行情（宽度>阈值）→ 用大止盈
          窄幅震荡（宽度<=阈值）→ 用小止盈
        """
        if not self.config.dynamic_tp_enabled:
            return self.config.take_profit_pct

        boll_width = self._get_boll_width()
        if boll_width <= 0:
            return self.config.take_profit_pct

        if boll_width > self.config.boll_wide_threshold:
            return self.config.take_profit_wide_pct
        else:
            return self.config.take_profit_narrow_pct

    def _check_trend_filter(self) -> bool:
        """
        1小时趋势过滤（2.0核心新增）
        只有满足以下任一条件才允许入场：
          - 当前价格 > 1小时EMA50（价格在均线之上，趋势偏多）
          - 1小时EMA50斜率向上（最近3根K线EMA值递增）
        如果1小时数据不可用，默认放行（不阻止交易）
        """
        if not self.config.trend_filter_enabled:
            return True

        if self._df_1h is None or len(self._df_1h) < self.config.trend_ema_period + 5:
            return True  # 没有1小时数据时默认放行

        ema_col = f'ema{self.config.trend_ema_period}'
        if ema_col not in self._df_1h.columns:
            return True  # EMA未计算时默认放行

        current_price = self._df['close'].iloc[-1] if self._df is not None else None
        ema_latest = self._df_1h[ema_col].iloc[-1]
        ema_3ago = self._df_1h[ema_col].iloc[-4]  # 3根1小时K线前的EMA值

        # 条件A：价格在EMA50之上（顺势做多）
        price_above_ema = (current_price is not None) and (current_price > ema_latest)

        # 条件B：EMA50斜率向上（均线处于上升状态）
        ema_rising = ema_latest > ema_3ago

        return price_above_ema or ema_rising

    def _klines_to_df(self, klines: list) -> pd.DataFrame:
        if not klines:
            return pd.DataFrame()
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df

    def _is_in_cooldown(self) -> bool:
        if self.state.cooldown_until <= 0:
            return False
        return datetime.now().timestamp() < self.state.cooldown_until

    def _is_max_losses(self) -> bool:
        return self.state.consecutive_losses >= self.config.max_consecutive_losses

    def _reset_state(self) -> None:
        self.state.in_position = False
        self.state.avg_cost = 0.0
        self.state.total_qty = 0.0
        self.state.add_count = 0
        self.state.entry_price = 0.0
        self.state.stop_loss_price = 0.0
        self.state.take_profit_price = 0.0
        self.state.tp_triggered = False
        self.state.sl_triggered = False

    def start_cooldown(self) -> None:
        """启动冷却期"""
        self.state.cooldown_until = datetime.now().timestamp() + self.config.cooldown_seconds

    def on_trade(self) -> None:
        """每次交易后更新日计数"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.state.last_trade_date != today:
            self.state.daily_trade_count = 0
            self.state.last_trade_date = today
        self.state.daily_trade_count += 1
