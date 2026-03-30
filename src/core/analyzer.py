"""
技术指标分析模块 - MACD/BOLL/RSI/KDJ等指标计算与9分制评分系统
"""
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalScore:
    """评分结果"""
    symbol: str
    total_score: float = 0.0
    max_score: float = 9.0
    macd_score: float = 0.0
    boll_score: float = 0.0
    rsi_score: float = 0.0
    kdj_score: float = 0.0
    volume_score: float = 0.0
    trend_score: float = 0.0
    details: dict = field(default_factory=dict)
    signal: str = "HOLD"       # BUY / SELL / HOLD
    price: float = 0.0

    @property
    def score_str(self) -> str:
        return f"{self.total_score:.1f}/{self.max_score}"

    @property
    def should_buy(self, threshold: float = 6.0) -> bool:
        """是否应该买入（根据动态阈值判断）"""
        return self.total_score >= threshold

    @property
    def should_sell(self, threshold: float = 2.0) -> bool:
        """是否应该卖出（根据动态阈值判断）"""
        return self.total_score <= threshold


class TechnicalAnalyzer:
    """技术指标分析器 - 9分制综合评分"""

    # 各指标权重（满分9分，共5大维度）
    WEIGHTS = {
        'macd': 2.0,     # MACD趋势
        'boll': 2.0,     # 布林带位置
        'rsi': 1.5,      # RSI超买超卖
        'kdj': 1.5,      # KDJ金叉死叉
        'volume': 1.0,   # 成交量
        'trend': 1.0,    # 均线趋势
    }

    def __init__(self, params: Optional[dict] = None):
        """
        params: 可配置参数字典，支持动态调整
        """
        self.params = {
            # MACD参数
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            # 布林带参数
            'boll_period': 20,
            'boll_std': 2.0,
            # RSI参数
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            # KDJ参数
            'kdj_period': 9,
            # 均线参数
            'ma_short': 7,
            'ma_mid': 25,
            'ma_long': 99,
            # 评分阈值
            'buy_threshold': 6.0,
            'sell_threshold': 2.0,
        }
        if params:
            self.params.update(params)

    def update_params(self, new_params: dict):
        """动态更新参数"""
        self.params.update(new_params)
        logger.info(f"参数已更新: {new_params}")

    def klines_to_df(self, klines: list) -> pd.DataFrame:
        """K线数据转DataFrame"""
        if not klines:
            return pd.DataFrame()
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    # ==================== 指标计算 ====================

    def calc_macd(self, close: pd.Series) -> tuple:
        """计算MACD (DIF, DEA, MACD柱)"""
        fast = self.params['macd_fast']
        slow = self.params['macd_slow']
        signal_period = self.params['macd_signal']

        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal_period, adjust=False).mean()
        macd_hist = (dif - dea) * 2
        return dif, dea, macd_hist

    def calc_boll(self, close: pd.Series) -> tuple:
        """计算布林带 (上轨, 中轨, 下轨)"""
        period = self.params['boll_period']
        std_mult = self.params['boll_std']
        mid = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = mid + std_mult * std
        lower = mid - std_mult * std
        return upper, mid, lower

    def calc_rsi(self, close: pd.Series) -> pd.Series:
        """计算RSI"""
        period = self.params['rsi_period']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        return 100 - 100 / (1 + rs)

    def calc_kdj(self, high: pd.Series, low: pd.Series, close: pd.Series) -> tuple:
        """计算KDJ (K, D, J)"""
        period = self.params['kdj_period']
        low_min = low.rolling(window=period).min()
        high_max = high.rolling(window=period).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-10) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3 * K - 2 * D
        return K, D, J

    def calc_ma(self, close: pd.Series) -> tuple:
        """计算均线"""
        ma7 = close.rolling(window=self.params['ma_short']).mean()
        ma25 = close.rolling(window=self.params['ma_mid']).mean()
        ma99 = close.rolling(window=self.params['ma_long']).mean()
        return ma7, ma25, ma99

    # ==================== 评分逻辑 ====================

    def score_macd(self, dif: pd.Series, dea: pd.Series, hist: pd.Series) -> tuple:
        """MACD评分 (0-2分)"""
        score = 0.0
        details = {}
        if len(dif) < 3:
            return 0.0, details

        cur_dif, cur_dea = dif.iloc[-1], dea.iloc[-1]
        prev_dif, prev_dea = dif.iloc[-2], dea.iloc[-2]
        cur_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]

        # 1. DIF与DEA位置关系（0-1分）
        if cur_dif > cur_dea:  # 金叉/DIF在上
            score += 0.5
            details['macd_cross'] = '多头排列'
        else:
            details['macd_cross'] = '空头排列'

        # 2. 零轴位置（0-0.5分）
        if cur_dif > 0 and cur_dea > 0:
            score += 0.5
            details['macd_zero'] = '零轴上方'
        else:
            details['macd_zero'] = '零轴下方'

        # 3. MACD柱趋势（0-1分）- 柱子增大说明动能增强
        if cur_hist > 0 and cur_hist > prev_hist:  # 红柱增大
            score += 1.0
            details['macd_hist'] = '红柱增大(强势)'
        elif cur_hist > 0:  # 红柱缩小
            score += 0.5
            details['macd_hist'] = '红柱缩小(弱势)'
        elif cur_hist < 0 and cur_hist > prev_hist:  # 绿柱缩小（转折信号）
            score += 0.3
            details['macd_hist'] = '绿柱缩小(潜在反转)'
        else:
            details['macd_hist'] = '绿柱(下行)'

        # 判断是否金叉
        if prev_dif < prev_dea and cur_dif > cur_dea:
            details['macd_signal'] = '⭐金叉信号'
            score = min(2.0, score + 0.5)

        return min(2.0, score), details

    def score_boll(self, close: float, upper: float, mid: float, lower: float) -> tuple:
        """布林带评分 (0-2分)"""
        score = 0.0
        details = {}
        band_width = upper - lower
        if band_width == 0:
            return 0.0, {}

        position = (close - lower) / band_width  # 0=下轨, 1=上轨

        details['boll_position'] = f"{position*100:.1f}%"

        if position < 0.2:  # 接近下轨：超卖
            score = 2.0
            details['boll_signal'] = '下轨超卖(买入区)'
        elif position < 0.4:
            score = 1.5
            details['boll_signal'] = '中下区间'
        elif position < 0.6:
            score = 1.0
            details['boll_signal'] = '中轨附近'
        elif position < 0.8:
            score = 0.5
            details['boll_signal'] = '中上区间'
        else:
            score = 0.0
            details['boll_signal'] = '上轨超买(谨慎)'

        return score, details

    def score_rsi(self, rsi: float) -> tuple:
        """RSI评分 (0-1.5分)"""
        score = 0.0
        details = {'rsi_value': f"{rsi:.1f}"}
        oversold = self.params['rsi_oversold']
        overbought = self.params['rsi_overbought']

        if rsi < oversold:
            score = 1.5
            details['rsi_signal'] = f'超卖({rsi:.0f}<{oversold})'
        elif rsi < 45:
            score = 1.2
            details['rsi_signal'] = '偏低区间'
        elif rsi < 55:
            score = 0.8
            details['rsi_signal'] = '中性区间'
        elif rsi < overbought:
            score = 0.4
            details['rsi_signal'] = '偏高区间'
        else:
            score = 0.0
            details['rsi_signal'] = f'超买({rsi:.0f}>{overbought})'

        return score, details

    def score_kdj(self, K: float, D: float, J: float,
                   prev_K: float, prev_D: float) -> tuple:
        """KDJ评分 (0-1.5分)"""
        score = 0.0
        details = {'kdj_kd': f"K:{K:.1f} D:{D:.1f} J:{J:.1f}"}

        # 超卖区
        if K < 20 and D < 20:
            score += 0.8
            details['kdj_zone'] = '超卖区'
        elif K < 50:
            score += 0.5
            details['kdj_zone'] = '偏低'
        else:
            details['kdj_zone'] = '偏高'

        # 金叉判断
        if prev_K <= prev_D and K > D:
            score += 0.7
            details['kdj_signal'] = '⭐KDJ金叉'
        elif K > D:
            score += 0.3
            details['kdj_signal'] = 'K在D上'
        else:
            details['kdj_signal'] = 'K在D下'

        return min(1.5, score), details

    def score_volume(self, volume: pd.Series) -> tuple:
        """成交量评分 (0-1分)"""
        if len(volume) < 10:
            return 0.5, {'volume': '数据不足'}

        vol_ma10 = volume.rolling(10).mean()
        cur_vol = volume.iloc[-1]
        avg_vol = vol_ma10.iloc[-1]
        ratio = cur_vol / (avg_vol + 1e-10)

        details = {'vol_ratio': f"{ratio:.2f}x"}

        if ratio > 2.0:
            return 1.0, {**details, 'vol_signal': '放量(1.0)'}
        elif ratio > 1.2:
            return 0.8, {**details, 'vol_signal': '温和放量'}
        elif ratio > 0.8:
            return 0.5, {**details, 'vol_signal': '正常量'}
        else:
            return 0.2, {**details, 'vol_signal': '缩量'}

    def score_trend(self, close: float, ma7: float, ma25: float, ma99: float) -> tuple:
        """均线趋势评分 (0-1分)"""
        score = 0.0
        details = {}

        if close > ma7 > ma25:
            score = 1.0
            details['trend'] = '多头排列'
        elif close > ma25:
            score = 0.7
            details['trend'] = '中期看多'
        elif close > ma99:
            score = 0.4
            details['trend'] = '长期支撑'
        else:
            score = 0.0
            details['trend'] = '空头排列'

        return score, details

    # ==================== 综合评分入口 ====================

    def analyze(self, symbol: str, klines: list,
                buy_threshold: float = 6.0, sell_threshold: float = 2.0) -> SignalScore:
        """对单个币种进行综合分析，返回评分结果
        
        Args:
            symbol: 币种符号
            klines: K线数据
            buy_threshold: 买入阈值
            sell_threshold: 卖出阈值
        """
        result = SignalScore(symbol=symbol)

        df = self.klines_to_df(klines)
        if df.empty or len(df) < 30:
            logger.warning(f"{symbol} 数据不足，无法分析")
            return result

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        result.price = close.iloc[-1]

        try:
            # 计算各指标
            dif, dea, hist = self.calc_macd(close)
            upper, mid, lower = self.calc_boll(close)
            rsi = self.calc_rsi(close)
            K, D, J = self.calc_kdj(high, low, close)
            ma7, ma25, ma99 = self.calc_ma(close)

            # 各维度评分
            result.macd_score, macd_detail = self.score_macd(dif, dea, hist)
            result.boll_score, boll_detail = self.score_boll(
                close.iloc[-1], upper.iloc[-1], mid.iloc[-1], lower.iloc[-1]
            )
            result.rsi_score, rsi_detail = self.score_rsi(rsi.iloc[-1])
            result.kdj_score, kdj_detail = self.score_kdj(
                K.iloc[-1], D.iloc[-1], J.iloc[-1],
                K.iloc[-2], D.iloc[-2]
            )
            result.volume_score, vol_detail = self.score_volume(volume)
            result.trend_score, trend_detail = self.score_trend(
                close.iloc[-1], ma7.iloc[-1], ma25.iloc[-1], ma99.iloc[-1]
            )

            result.total_score = (
                result.macd_score + result.boll_score + result.rsi_score +
                result.kdj_score + result.volume_score + result.trend_score
            )

            # 合并详情
            result.details = {
                **macd_detail, **boll_detail, **rsi_detail,
                **kdj_detail, **vol_detail, **trend_detail,
                'indicators': {
                    'dif': float(dif.iloc[-1]),
                    'dea': float(dea.iloc[-1]),
                    'macd': float(hist.iloc[-1]),
                    'boll_upper': float(upper.iloc[-1]),
                    'boll_mid': float(mid.iloc[-1]),
                    'boll_lower': float(lower.iloc[-1]),
                    'rsi': float(rsi.iloc[-1]),
                    'k': float(K.iloc[-1]),
                    'd': float(D.iloc[-1]),
                    'j': float(J.iloc[-1]),
                    'ma7': float(ma7.iloc[-1]),
                    'ma25': float(ma25.iloc[-1]),
                    'ma99': float(ma99.iloc[-1]) if len(close) > 99 else 0,
                }
            }

            # 确定信号（使用动态阈值）
            if result.should_buy(buy_threshold):
                result.signal = "BUY"
            elif result.should_sell(sell_threshold):
                result.signal = "SELL"
            else:
                result.signal = "HOLD"

            logger.info(
                f"{symbol} 评分: {result.score_str} "
                f"信号:{result.signal} "
                f"[MACD:{result.macd_score:.1f} BOLL:{result.boll_score:.1f} "
                f"RSI:{result.rsi_score:.1f} KDJ:{result.kdj_score:.1f} "
                f"VOL:{result.volume_score:.1f} TREND:{result.trend_score:.1f}]"
            )

        except Exception as e:
            logger.error(f"分析 {symbol} 失败: {e}", exc_info=True)

        return result
