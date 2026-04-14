"""
AI交易子策略 - 4种自适应策略
每个策略独立评分，返回信号字典
策略由AI Trader统一权重评分
"""
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict
from .ai_config import AIStrategyParams

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """交易信号"""
    action: str = "HOLD"       # BUY / SELL / HOLD
    confidence: float = 0.0     # 置信度 0~1
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_pct: float = 0.10
    reason: str = ""
    strategy_name: str = ""
    details: Dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        return self.action in ("BUY", "SELL") and self.confidence >= 0.3


def _calc_ema(closes: np.ndarray, period: int) -> np.ndarray:
    """计算EMA"""
    if len(closes) < period:
        return np.full_like(closes, closes[-1] if len(closes) > 0 else 0.0)
    ema = np.zeros_like(closes, dtype=float)
    ema[period - 1] = np.mean(closes[:period])
    multiplier = 2.0 / (period + 1)
    for i in range(period, len(closes)):
        ema[i] = (closes[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def _calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """计算RSI"""
    if len(closes) < period + 1:
        return np.full_like(closes, 50.0)
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros_like(closes, dtype=float)
    avg_loss = np.zeros_like(closes, dtype=float)
    avg_gain[period] = np.mean(gains[1:period + 1])
    avg_loss[period] = np.mean(losses[1:period + 1])
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period
    rsi = np.zeros_like(closes, dtype=float)
    for i in range(period, len(closes)):
        if avg_loss[i] == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _calc_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """计算MACD (macd_line, signal_line, histogram)"""
    ema_fast = _calc_ema(closes, fast)
    ema_slow = _calc_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _calc_boll(closes: np.ndarray, period: int = 20, std_mult: float = 2.0):
    """计算布林带 (upper, mid, lower)"""
    if len(closes) < period:
        mid = np.full_like(closes, closes[-1] if len(closes) > 0 else 0.0)
        return mid, mid * 1.05, mid * 0.95
    mid = np.zeros_like(closes, dtype=float)
    std_arr = np.zeros_like(closes, dtype=float)
    for i in range(period - 1, len(closes)):
        mid[i] = np.mean(closes[i - period + 1:i + 1])
        std_arr[i] = np.std(closes[i - period + 1:i + 1])
    std_arr[:period - 1] = std_arr[period - 1]
    upper = mid + std_mult * std_arr
    lower = mid - std_mult * std_arr
    return upper, mid, lower


def _calc_atr(highs, lows, closes, period: int = 14):
    """计算ATR"""
    if len(highs) < 2:
        return np.full_like(closes, 0.001 * closes[-1] if len(closes) > 0 else 1.0)
    tr = np.zeros(len(closes), dtype=float)
    for i in range(1, len(closes)):
        h_l = highs[i] - lows[i]
        h_c = abs(highs[i] - closes[i - 1])
        l_c = abs(lows[i] - closes[i - 1])
        tr[i] = max(h_l, h_c, l_c)
    atr = np.zeros_like(closes, dtype=float)
    if len(tr) >= period:
        atr[period - 1] = np.mean(tr[1:period])
        for i in range(period, len(tr)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    atr[:period] = atr[period] if period < len(atr) else atr[-1]
    return atr


class BaseStrategy:
    """策略基类"""
    name = "Base"

    def __init__(self, params: AIStrategyParams):
        self.params = params
        self.last_signal_time: float = 0.0

    def can_trade(self, current_time: float) -> bool:
        """冷却期检查"""
        return (current_time - self.last_signal_time) >= self.params.cooldown_seconds

    def analyze(self, kline_data, kline_1h=None) -> TradingSignal:
        raise NotImplementedError

    def _signal(self, action, confidence, price, sl_pct, tp_pct, reason, details):
        """构造信号"""
        if action == "BUY":
            sl = price * (1 - sl_pct / 100)
            tp = price * (1 + tp_pct / 100)
        else:
            sl = price * (1 + sl_pct / 100)
            tp = price * (1 - tp_pct / 100)
        return TradingSignal(
            action=action,
            confidence=confidence,
            entry_price=price,
            stop_loss=round(sl, 6),
            take_profit=round(tp, 6),
            position_pct=self.params.position_pct,
            reason=reason,
            strategy_name=self.name,
            details=details,
        )


class MomentumStrategy(BaseStrategy):
    """
    趋势跟踪策略 - 顺大势买入
    条件: 15分钟价格站上EMA20 + EMA20多头排列 + RSI在45~65(非超买) + MACD柱状体正值
    止盈: 动态（1.5x~3x），止损: 0.8%
    """
    name = "Momentum"

    def analyze(self, kline_data, kline_1h=None) -> TradingSignal:
        closes = kline_data.get('close')
        if closes is None or len(closes) < 50:
            return TradingSignal()

        price = closes[-1]
        ema20 = _calc_ema(closes, 20)
        ema50 = _calc_ema(closes, 50)
        rsi = _calc_rsi(closes, 14)
        macd, signal, hist = _calc_macd(closes)

        # 1h趋势过滤
        trend_up = True
        if kline_1h is not None:
            closes_1h = kline_1h.get('close')
            if closes_1h is not None and len(closes_1h) >= 50:
                ema50_1h = _calc_ema(closes_1h, 50)
                trend_up = closes_1h[-1] > ema50_1h[-1]

        score = 0.0
        details = {}

        # 价格在EMA20上方
        if price > ema20[-1]:
            score += 0.25
            details['above_ema20'] = True
        # EMA多头排列
        if ema20[-1] > ema50[-1] and ema20[-2] > ema50[-2]:
            score += 0.20
            details['ema_bullish'] = True
        # RSI合理区间
        if 45 < rsi[-1] < 65:
            score += 0.25
            details['rsi_ok'] = True
        # RSI趋势向上
        if rsi[-1] > rsi[-2] > rsi[-3]:
            score += 0.10
            details['rsi_rising'] = True
        # MACD柱状体为正且放大
        if hist[-1] > 0 and hist[-1] > hist[-2]:
            score += 0.15
            details['macd_positive'] = True
        # 1h趋势向上
        if trend_up:
            score += 0.05
            details['trend_1h_ok'] = True

        if score < 0.65:
            return TradingSignal()

        if score >= 0.80:
            tp_pct = self.params.take_profit_pct * 1.5
        elif score >= 0.65:
            tp_pct = self.params.take_profit_pct
        else:
            tp_pct = self.params.take_profit_pct * 0.8

        confidence = min(score, 0.95)
        reason = (f"Momentum BUY #{self.name} score={score:.2f} "
                  f"price={price:.4f} RSI={rsi[-1]:.1f} "
                  f"MACD_hist={hist[-1]:.4f} "
                  f"above_EMA20={'Y' if price > ema20[-1] else 'N'}")

        return self._signal("BUY", confidence, price,
                            self.params.stop_loss_pct, tp_pct, reason, details)


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略 - 超卖反弹
    条件: RSI<35(超卖) + 价格贴近布林带下轨 + MACD底部转正
    止盈: 布林带中轨或1.5%，止损: 1%
    """
    name = "MeanReversion"

    def analyze(self, kline_data, kline_1h=None) -> TradingSignal:
        closes = kline_data.get('close')
        if closes is None or len(closes) < 50:
            return TradingSignal()

        price = closes[-1]
        rsi = _calc_rsi(closes, 14)
        macd, signal, hist = _calc_macd(closes)
        upper, mid, lower = _calc_boll(closes, self.params.boll_period, self.params.boll_std)
        ema50 = _calc_ema(closes, 50)

        # 1h趋势过滤
        trend_up = True
        if kline_1h is not None:
            closes_1h = kline_1h.get('close')
            if closes_1h is not None and len(closes_1h) >= 50:
                ema50_1h = _calc_ema(closes_1h, 50)
                trend_up = closes_1h[-1] > ema50_1h[-1]

        score = 0.0
        details = {}

        # RSI超卖
        if rsi[-1] < 35:
            score += 0.35
            details['rsi_oversold'] = True
        elif rsi[-1] < 40:
            score += 0.15
            details['rsi_near_oversold'] = True

        # 价格贴近布林带下轨
        band_range = upper[-1] - lower[-1]
        band_pos = (price - lower[-1]) / band_range if band_range != 0 else 0.5
        if band_pos < 0.10:
            score += 0.30
            details['near_lower_band'] = True
        elif band_pos < 0.20:
            score += 0.15
            details['below_lower_band'] = True

        # MACD柱状体由负转正
        if hist[-1] > 0 and hist[-2] <= 0:
            score += 0.20
            details['macd_golden_cross'] = True
        elif hist[-1] > 0:
            score += 0.10

        if trend_up:
            score += 0.10
            details['trend_1h_ok'] = True
        if price > ema50[-1]:
            score += 0.05
            details['above_ema50'] = True

        if score < 0.60:
            return TradingSignal()

        confidence = min(score, 0.92)
        # 止盈：布林带中轨
        tp_pct = self.params.take_profit_pct
        boll_tp = (mid[-1] - price) / price * 100
        if boll_tp > 0.5:
            tp_pct = min(boll_tp, self.params.take_profit_pct * 1.5)

        reason = (f"MeanReversion BUY #{self.name} score={score:.2f} "
                  f"price={price:.4f} RSI={rsi[-1]:.1f} "
                  f"band_pos={band_pos:.2f} MACD_hist={hist[-1]:.4f}")

        return self._signal("BUY", confidence, price,
                            self.params.stop_loss_pct, tp_pct, reason, details)


class BreakoutStrategy(BaseStrategy):
    """
    突破策略 - 顺势突破
    条件: 15分钟价格突破近期高点 + 成交量放大确认
    1h趋势一致时做突破，逆势放弃
    """
    name = "Breakout"

    def analyze(self, kline_data, kline_1h=None) -> TradingSignal:
        closes = kline_data.get('close')
        highs = kline_data.get('high', closes)
        lows = kline_data.get('low', closes)
        volumes = kline_data.get('volume', np.array([1.0]))

        if closes is None or len(closes) < 60:
            return TradingSignal()

        price = closes[-1]
        rsi = _calc_rsi(closes, 14)
        macd, signal, hist = _calc_macd(closes)
        vol_ratio = np.mean(volumes[-3:]) / np.mean(volumes[-20:-3]) if len(volumes) >= 20 else 1.0

        # 1h趋势
        trend_up = True
        if kline_1h is not None:
            closes_1h = kline_1h.get('close')
            if closes_1h is not None and len(closes_1h) >= 50:
                ema50_1h = _calc_ema(closes_1h, 50)
                trend_up = closes_1h[-1] > ema50_1h[-1]

        score = 0.0
        details = {}

        # 统计近期高低价
        lookback = 20
        recent_high = np.max(highs[-lookback - 1:-1])
        recent_low = np.min(lows[-lookback - 1:-1])
        range_pct = (recent_high - recent_low) / recent_low * 100 if recent_low > 0 else 0
        breakout_up = (price - recent_high) / recent_high * 100 if recent_high > 0 else 0

        # 向上突破确认
        if breakout_up > 0.3:
            score += 0.30
            details['breakout_up'] = True
            details['breakout_pct'] = breakout_up
            # 量价配合
            if vol_ratio > 1.5:
                score += 0.20
                details['volume_confirm'] = True
            elif vol_ratio > 1.0:
                score += 0.10
            # RSI顺势
            if rsi[-1] > 50:
                score += 0.10
                details['rsi_ok'] = True
            # MACD正值
            if hist[-1] > 0:
                score += 0.10
                details['macd_positive'] = True
            # 1h趋势一致
            if trend_up:
                score += 0.15
                details['trend_ok'] = True
            # 波动率足够
            if range_pct > 1.0:
                score += 0.10
                details['volatility_ok'] = True

        if score < 0.55:
            return TradingSignal()

        confidence = min(score, 0.90)
        reason = (f"Breakout #{self.name} score={score:.2f} "
                  f"price={price:.4f} breakout={breakout_up:.2f}% "
                  f"vol={vol_ratio:.2f}x range={range_pct:.1f}%")

        return self._signal("BUY", confidence, price,
                            self.params.stop_loss_pct, self.params.take_profit_pct,
                            reason, details)


class VolumeConfirmStrategy(BaseStrategy):
    """
    量价确认策略 - 放量顺势
    条件: 持续价格变动 + 成交量放大确认
    RSI低位+放量是最强信号
    """
    name = "VolumeConfirm"

    def analyze(self, kline_data, kline_1h=None) -> TradingSignal:
        closes = kline_data.get('close')
        volumes = kline_data.get('volume', np.array([1.0]))

        if closes is None or len(closes) < 50:
            return TradingSignal()

        price = closes[-1]
        rsi = _calc_rsi(closes, 14)
        macd, signal, hist = _calc_macd(closes)
        ema20 = _calc_ema(closes, 20)
        vol_ratio = np.mean(volumes[-3:]) / np.mean(volumes[-20:-3]) if len(volumes) >= 20 else 1.0

        score = 0.0
        details = {}

        if len(closes) >= 5:
            recent_changes = np.diff(closes[-5:])
            # 持续上涨+放量
            if np.sum(recent_changes > 0) >= 3 and vol_ratio > 1.3:
                score += 0.45
                details['bullish_vol'] = True
            # 缩量上涨（主力控盘）
            elif np.sum(recent_changes > 0) >= 3 and vol_ratio < 0.8:
                score += 0.30
                details['thin_bull'] = True
            # 下跌后反弹+放量
            price_change = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] != 0 else 0
            if price_change < -0.005 and vol_ratio > 1.5:
                score += 0.25
                details['volume_rebound'] = True

        if price > ema20[-1]:
            score += 0.15
            details['above_ema20'] = True

        if 40 < rsi[-1] < 60:
            score += 0.15
            details['rsi_neutral'] = True
        elif rsi[-1] < 40:
            score += 0.25
            details['rsi_cheap'] = True

        if hist[-1] > 0 and hist[-1] > hist[-2]:
            score += 0.10
            details['macd_strengthening'] = True

        if score < 0.55:
            return TradingSignal()

        confidence = min(score, 0.88)
        reason = (f"VolumeConfirm #{self.name} score={score:.2f} "
                  f"price={price:.4f} vol_ratio={vol_ratio:.2f}x "
                  f"RSI={rsi[-1]:.1f}")

        return self._signal("BUY", confidence, price,
                            self.params.stop_loss_pct, self.params.take_profit_pct,
                            reason, details)
