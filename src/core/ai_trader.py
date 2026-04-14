"""
AI交易引擎 - 自适应多策略核心
全权负责: 市场分析、多策略评分、自适应调参、风控执行
每小时自动复盘，持续优化策略表现
"""
import json
import os
import time
import logging
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from threading import Lock
import numpy as np

from .ai_config import AIConfig, AIStrategyParams
from .ai_strategies import (
    MomentumStrategy, MeanReversionStrategy,
    BreakoutStrategy, VolumeConfirmStrategy,
    TradingSignal
)

logger = logging.getLogger(__name__)


@dataclass
class AITradeRecord:
    """AI交易记录"""
    id: str
    symbol: str
    action: str          # BUY / SELL
    entry_price: float
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    strategy: str = ""
    confidence: float = 0.0
    reason: str = ""
    entry_time: str = ""
    exit_time: str = ""
    stop_loss: float = 0.0
    take_profit: float = 0.0
    tp_reached: bool = False   # 是否止盈出局
    sl_reached: bool = False   # 是否止损出局
    hourly_stats: Dict = field(default_factory=dict)  # 入场时的各策略状态

    def __post_init__(self):
        if not self.entry_time:
            self.entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@dataclass
class StrategyPerformance:
    """单策略表现追踪"""
    name: str
    trades: List[AITradeRecord] = field(default_factory=list)
    hourly_pnl: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    current_weight: float = 1.0

    @property
    def win_rate(self) -> float:
        total = self.win_count + self.loss_count
        return self.win_count / total if total > 0 else 0.0

    @property
    def total_trades(self) -> int:
        return self.win_count + self.loss_count


class AITrader:
    """
    AI自适应交易引擎
    核心功能:
    1. 多策略并行评分，动态权重
    2. 实时持仓监控，追踪止盈止损
    3. 每小时复盘，自动调整策略权重和参数
    4. 日亏损上限$20，超限自动暂停
    5. 持续学习，进化策略表现
    """

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    JOURNAL_FILE = os.path.join(DATA_DIR, 'ai_trades.json')
    STATS_FILE = os.path.join(DATA_DIR, 'ai_stats.json')

    def __init__(self, client, log_func=None):
        """
        client: BinanceClientManager 实例
        log_func: 日志回调函数
        """
        self.client = client
        self.log_func = log_func or (lambda x, level='INFO': logger.info(x))
        self.config = AIConfig()
        self._lock = Lock()

        # === 策略实例 ===
        self.strategies = {}
        self._init_strategies()

        # === 状态 ===
        self.ai_positions: Dict[str, Dict] = {}   # {symbol: {qty, entry_price, signal, ...}}
        self.ai_trades: List[AITradeRecord] = []    # 历史交易记录
        self.performance: Dict[str, StrategyPerformance] = {}  # 各策略表现
        self._init_performance()

        # === 每日/每小时统计 ===
        self.daily_pnl: float = 0.0
        self.daily_start_time: str = ""
        self.last_review_time: float = time.time()
        self.consecutive_losses: int = 0
        self.paused_until: float = 0.0   # 暂停时间戳
        self._last_entry_time: float = 0.0  # 上次开仓时间（防止密集开仓）
        self._max_positions: int = 2       # 最多同时持有2个AI仓位

        # === 回调 ===
        self.on_trade: Optional[callable] = None
        self.on_review: Optional[callable] = None
        self.on_status_update: Optional[callable] = None

        # === 加载历史数据 ===
        self._load_data()

    def _init_strategies(self):
        """初始化4个子策略"""
        p = self.config
        self.strategies = {
            'Momentum': MomentumStrategy(p.momentum_params),
            'MeanReversion': MeanReversionStrategy(p.mean_reversion_params),
            'Breakout': BreakoutStrategy(p.breakout_params),
            'VolumeConfirm': VolumeConfirmStrategy(p.volume_params),
        }

    def _init_performance(self):
        """初始化各策略表现追踪"""
        for name in self.strategies:
            self.performance[name] = StrategyPerformance(name=name)

    # ==================== 核心分析 ====================

    def analyze_symbol(self, symbol: str, klines_15m: list,
                       klines_1h: Optional[list] = None) -> List[Tuple[TradingSignal, float]]:
        """
        分析单个币种，返回带权重的有效信号列表
        返回: [(signal, weighted_score), ...] 按加权分数降序
        """
        if self._is_paused():
            return []

        # 冷却期检查
        if symbol in self.ai_positions:
            return []

        # 转换为numpy数组
        kline_data = self._klines_to_arrays(klines_15m)
        kline_1h_data = self._klines_to_arrays(klines_1h) if klines_1h else None

        current_time = time.time()
        results = []

        for name, strategy in self.strategies.items():
            if not strategy.params.enabled:
                continue
            if not strategy.can_trade(current_time):
                continue

            signal = strategy.analyze(kline_data, kline_1h_data)
            if not signal.is_valid():
                continue

            # 应用策略权重
            perf = self.performance.get(name)
            weight = perf.current_weight if perf else 1.0
            weighted_score = signal.confidence * weight

            results.append((signal, weighted_score))

        # 按加权分数降序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _klines_to_arrays(self, klines: list) -> Dict[str, np.ndarray]:
        """将K线列表转换为numpy数组"""
        if not klines:
            return {}
        closes = np.array([float(k[4]) for k in klines])
        highs = np.array([float(k[2]) for k in klines])
        lows = np.array([float(k[3]) for k in klines])
        volumes = np.array([float(k[5]) for k in klines])
        return {'close': closes, 'high': highs, 'low': lows, 'volume': volumes}

    # ==================== 交易执行 ====================

    def should_enter(self, symbol: str, top_signal: TradingSignal,
                     weighted_score: float, balance: float) -> bool:
        """判断是否应该开仓"""
        # 基础条件
        if self._is_paused():
            return False
        if symbol in self.ai_positions:
            return False
        # 最多同时持有2个仓位
        if len(self.ai_positions) >= self._max_positions:
            return False
        # 全局入场间隔：至少20秒后才能开新仓
        if time.time() - self._last_entry_time < 20:
            return False
        # 置信度门槛提升到0.55（原0.40太低）
        if top_signal.confidence < 0.55:
            return False
        # 胜率要求：连续亏损3次后，只接受置信度>0.65的信号
        if self.consecutive_losses >= 3 and top_signal.confidence < 0.65:
            return False
        # 动态仓位调整：日亏超过5美元，只接受置信度>0.60
        if self.daily_pnl < -5.0:
            if top_signal.confidence < 0.60:
                return False
        return True

    def open_position(self, symbol: str, signal: TradingSignal, balance: float) -> bool:
        """开仓买入（真实下单到币安现货）"""
        with self._lock:
            # 计算金额
            amount = balance * signal.position_pct
            if amount < 10.0:
                return False

            price = signal.entry_price
            # 用目标金额法计算并取整数量（确保每单约等于 amount USDT）
            quantity = self.client.round_quantity(symbol, 0, target_usdt=amount)

            # 真实下单到币安现货
            if not hasattr(self.client, 'spot_market_buy'):
                self.log_func(f"[AI交易] ⚠️ {symbol} 无法下单：client缺少spot_market_buy方法")
                return False

            order_result = self.client.spot_market_buy(symbol, quantity)
            if not order_result or not order_result.get('orderId'):
                self.log_func(f"[AI交易] ❌ {symbol} 买入失败，API返回: {order_result}")
                return False

            # 下单成功后记录持仓
            self.ai_positions[symbol] = {
                'qty': quantity,
                'entry_price': price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'signal': signal,
                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sl_pct': self._calc_sl_pct(signal),
                'tp_pct': self._calc_tp_pct(signal),
                'weighted_score': signal.confidence,
                'highest_price': price,
                'trailing_activated': False,
                'order_id': order_result.get('orderId'),
            }

            trade_id = f"AI-{symbol}-{int(time.time())}"
            record = AITradeRecord(
                id=trade_id,
                symbol=symbol,
                action='BUY',
                entry_price=price,
                quantity=quantity,
                strategy=signal.strategy_name,
                confidence=signal.confidence,
                reason=signal.reason,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
            )
            self.ai_trades.append(record)
            self._save_data()

            self.log_func(
                f"[AI交易] ✅ {symbol} 真实买入成功: 订单号={order_result['orderId']} "
                f"价格={price:.4f} 数量={quantity:.6f} 策略={signal.strategy_name} "
                f"置信度={signal.confidence:.0%} "
                f"止盈={signal.take_profit:.4f}({signal.details.get('_tp_pct', '?')}%) "
                f"止损={signal.stop_loss:.4f}"
            )
            self._last_entry_time = time.time()
            return True

    def check_and_close(self, symbol: str, current_price: float) -> Optional[AITradeRecord]:
        """
        检查持仓是否触发止盈/止损/移动止损，返回平仓记录（如果有）
        移动止损：当价格超过入场价+0.5%后激活，
        从最高点回落0.3%即平仓锁定利润
        """
        if symbol not in self.ai_positions:
            return None

        pos = self.ai_positions[symbol]
        entry_price = pos['entry_price']
        tp = pos['take_profit']
        sl = pos['stop_loss']
        qty = pos['qty']

        # 兼容存量持仓（新增字段）
        if 'highest_price' not in pos:
            pos['highest_price'] = entry_price
        if 'trailing_activated' not in pos:
            pos['trailing_activated'] = False

        tp_reached = False
        sl_reached = False
        trailing_reached = False

        if pos['signal'].action == "BUY":
            # 更新追踪最高价
            if current_price > pos['highest_price']:
                pos['highest_price'] = current_price

            # 止盈触发
            if current_price >= tp:
                tp_reached = True
            # 固定止损触发
            elif current_price <= sl:
                sl_reached = True
            # 移动止损：盈利超过0.5%后激活，从高点回落0.3%即平
            else:
                profit_pct = (current_price - entry_price) / entry_price * 100
                if profit_pct >= 0.5:
                    pos['trailing_activated'] = True
                if pos['trailing_activated']:
                    peak = pos['highest_price']
                    drop_pct = (peak - current_price) / peak * 100
                    if drop_pct >= 0.30:
                        trailing_reached = True

        pnl = (current_price - entry_price) * qty
        pnl_pct = (current_price - entry_price) / entry_price * 100

        if tp_reached or sl_reached or trailing_reached:
            reason = '止盈' if tp_reached else '移动止损' if trailing_reached else '止损'

            # 真实卖出平仓
            sell_result = {}
            if hasattr(self.client, 'spot_market_sell'):
                sell_result = self.client.spot_market_sell(symbol, qty)

            closed_record = self._close_position(
                symbol, current_price, pnl, pnl_pct,
                tp_reached=tp_reached, sl_reached=sl_reached or trailing_reached
            )

            order_id = sell_result.get('orderId', 'N/A') if sell_result else 'SELL_FAILED'
            self.log_func(
                f"[AI交易] {'✅' if sell_result.get('orderId') else '⚠️'} {symbol} "
                f"{reason}平仓: 订单号={order_id} "
                f"价格={current_price:.4f} 盈亏=${pnl:.2f}({pnl_pct:.2f}%)"
            )
            return closed_record

        return None

    def close_all_positions(self, current_prices: Dict[str, float]) -> List[AITradeRecord]:
        """强制平所有持仓（用于暂停或收盘）"""
        closed = []
        for symbol in list(self.ai_positions.keys()):
            price = current_prices.get(symbol)
            if price:
                rec = self.check_and_close(symbol, price)
                if rec:
                    closed.append(rec)
        return closed

    def _close_position(self, symbol: str, exit_price: float,
                        pnl: float, pnl_pct: float,
                        tp_reached: bool, sl_reached: bool) -> AITradeRecord:
        """内部平仓方法"""
        with self._lock:
            pos = self.ai_positions.pop(symbol, None)
            if not pos:
                raise ValueError(f"{symbol} 没有持仓")

            # 找对应记录
            record = None
            for rec in reversed(self.ai_trades):
                if rec.symbol == symbol and rec.exit_price == 0.0:
                    record = rec
                    break

            if record:
                record.exit_price = exit_price
                record.pnl = round(pnl, 4)
                record.pnl_pct = round(pnl_pct, 3)
                record.exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                record.tp_reached = tp_reached
                record.sl_reached = sl_reached

                # 更新策略表现
                self._update_performance(record)

            self.daily_pnl += pnl
            if pnl < 0:
                self.consecutive_losses += 1
                self.log_func(
                    f"[AI交易] ❌ {symbol} 平仓: 亏损 ${pnl:.2f} ({pnl_pct:.2f}%) "
                    f"{'止盈' if tp_reached else '止损'} "
                    f"连损:{self.consecutive_losses}次 日亏:${self.daily_pnl:.2f}"
                )
                # 检查日亏上限
                self._check_loss_limit()
            else:
                self.consecutive_losses = 0
                self.log_func(
                    f"[AI交易] 🎉 {symbol} 平仓: 盈利 ${pnl:.2f} ({pnl_pct:.2f}%) "
                    f"日盈:${self.daily_pnl:.2f}"
                )

            self._save_data()
            if self.on_trade:
                self.on_trade(record)
            return record

    def _calc_sl_pct(self, signal: TradingSignal) -> float:
        return abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100

    def _calc_tp_pct(self, signal: TradingSignal) -> float:
        return abs(signal.take_profit - signal.entry_price) / signal.entry_price * 100

    # ==================== 自适应调参 ====================

    def hourly_review(self) -> Dict:
        """
        每小时复盘核心函数
        1. 统计各策略胜率和盈亏比
        2. 调整策略权重（好的加权重，差的减权重）
        3. 调整参数（止盈止损）
        4. 记录复盘报告
        """
        recent_trades = self._get_recent_trades(hours=1)
        recent_all = self._get_recent_trades(hours=24)

        if len(recent_trades) < self.config.account.min_trades_for_review:
            return {'action': 'SKIP', 'reason': f'交易不足({len(recent_trades)}笔)'}

        self.log_func(f"[AI复盘] 开始每小时复盘 | 近1小时:{len(recent_trades)}笔 近24h:{len(recent_all)}笔")

        report = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hourly_trades': len(recent_trades),
            'daily_trades': len(recent_all),
            'daily_pnl': self.daily_pnl,
            'strategy_adjustments': [],
            'parameter_changes': [],
        }

        # 1. 按策略统计
        for name, perf in self.performance.items():
            strat_trades = [t for t in recent_trades if t.strategy == name]
            if not strat_trades:
                continue

            wins = sum(1 for t in strat_trades if t.pnl > 0)
            losses = sum(1 for t in strat_trades if t.pnl <= 0)
            strat_pnl = sum(t.pnl for t in strat_trades)
            win_rate = wins / len(strat_trades) if strat_trades else 0

            # 计算盈亏比
            win_values = [t.pnl for t in strat_trades if t.pnl > 0]
            loss_values = [t.pnl for t in strat_trades if t.pnl < 0]
            avg_win = np.mean(win_values) if win_values else 0
            avg_loss = abs(np.mean(loss_values)) if loss_values else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

            # 权重调整
            old_weight = perf.current_weight
            adjustment = ''

            if win_rate >= self.config.min_win_rate_for_up and profit_factor >= self.config.min_profit_factor_for_up:
                # 表现好，加权重
                new_weight = min(old_weight * 1.2, self.config.max_weight)
                adjustment = f'↑权重 {old_weight:.2f}→{new_weight:.2f} (胜率{win_rate:.0%}盈亏比{profit_factor:.2f})'
            elif win_rate <= 0.3 and len(strat_trades) >= 2:
                # 连续表现差，减权重
                new_weight = max(old_weight * 0.7, self.config.min_weight)
                adjustment = f'↓权重 {old_weight:.2f}→{new_weight:.2f} (胜率{win_rate:.0%})'
            else:
                new_weight = old_weight
                adjustment = f'维持权重 {old_weight:.2f}'

            perf.current_weight = new_weight
            # 更新策略参数
            strategy = self.strategies.get(name)
            if strategy:
                # 根据表现调整止盈止损参数
                old_sl = strategy.params.stop_loss_pct
                old_tp = strategy.params.take_profit_pct

                if strat_pnl < -1.0 and old_sl < 2.0:  # 亏损大，止损稍微放宽
                    strategy.params.stop_loss_pct = min(old_sl + 0.2, 2.0)
                elif strat_pnl > 2.0 and old_tp < 3.0:  # 盈利好，止盈稍微拉高
                    strategy.params.take_profit_pct = min(old_tp + 0.3, 3.5)

                if strategy.params.stop_loss_pct != old_sl or strategy.params.take_profit_pct != old_tp:
                    report['parameter_changes'].append(
                        f'{name}: 止损{old_sl}%→{strategy.params.stop_loss_pct}% '
                        f'止盈{old_tp}%→{strategy.params.take_profit_pct}%'
                    )

            report['strategy_adjustments'].append({
                'strategy': name,
                'trades': len(strat_trades),
                'wins': wins,
                'losses': losses,
                'pnl': round(strat_pnl, 2),
                'win_rate': round(win_rate, 3),
                'avg_win': round(avg_win, 3) if avg_win else 0,
                'avg_loss': round(avg_loss, 3) if avg_loss else 0,
                'weight': round(new_weight, 2),
                'adjustment': adjustment,
            })

        # 2. 全局参数调整
        if self.daily_pnl < -10.0:
            # 日亏严重，降仓
            for name, strategy in self.strategies.items():
                old_pct = strategy.params.position_pct
                strategy.params.position_pct = old_pct * 0.5
                if strategy.params.position_pct != old_pct:
                    report['parameter_changes'].append(
                        f'{name}: 仓位{old_pct*100:.0f}%→{strategy.params.position_pct*100:.0f}% (日亏${self.daily_pnl:.2f})'
                    )
            self.log_func("[AI复盘] ⚠️ 日亏严重，全面降仓50%")

        # 3. 连续亏损检查
        if self.consecutive_losses >= self.config.pause_on_consecutive_losses:
            self.paused_until = time.time() + 300  # 暂停5分钟
            report['paused'] = True
            report['pause_reason'] = f'连续{self.consecutive_losses}次亏损，暂停5分钟'
            self.log_func(f"[AI复盘] ⛔ 连续{self.consecutive_losses}次亏损，暂停5分钟")

        # 4. 每日清零重置（跨日检查）
        today = date.today().strftime('%Y-%m-%d')
        if self.daily_start_time and not self.daily_start_time.startswith(today):
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.log_func("[AI复盘] 📅 新的一天，重置日统计数据")
            report['daily_reset'] = True

        self.last_review_time = time.time()
        self._save_data()

        if self.on_review:
            self.on_review(report)
        return report

    def _get_recent_trades(self, hours: int) -> List[AITradeRecord]:
        """获取最近N小时内的交易"""
        cutoff = datetime.now().timestamp() - hours * 3600
        return [t for t in self.ai_trades
                if datetime.strptime(t.entry_time, '%Y-%m-%d %H:%M:%S').timestamp() >= cutoff]

    def _update_performance(self, record: AITradeRecord):
        """更新策略表现"""
        name = record.strategy
        if name not in self.performance:
            return
        perf = self.performance[name]
        perf.trades.append(record)
        perf.total_trades  # just reference
        if record.pnl > 0:
            perf.win_count += 1
        elif record.pnl < 0:
            perf.loss_count += 1
        perf.total_pnl += record.pnl

    def _check_loss_limit(self):
        """检查日亏损上限"""
        if self.daily_pnl <= -self.config.account.daily_loss_limit:
            self.paused_until = time.time() + 3600  # 暂停1小时
            self.log_func(
                f"[AI风控] 🚨 触及日亏上限(${self.config.account.daily_loss_limit}) "
                f"当前日亏${self.daily_pnl:.2f}，暂停1小时"
            )

    def _is_paused(self) -> bool:
        """检查是否暂停"""
        return time.time() < self.paused_until

    # ==================== 状态获取 ====================

    def get_status(self) -> Dict:
        """获取AI交易状态"""
        total_weight = sum(p.current_weight for p in self.performance.values())
        return {
            'running': True,
            'paused': self._is_paused(),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_target': self.config.account.daily_target,
            'loss_limit': self.config.account.daily_loss_limit,
            'active_positions': len(self.ai_positions),
            'consecutive_losses': self.consecutive_losses,
            'total_trades': len(self.ai_trades),
            'strategies': {
                name: {
                    'weight': round(p.current_weight, 2),
                    'win_rate': round(p.win_rate, 2),
                    'total_pnl': round(p.total_pnl, 2),
                    'trades': p.total_trades,
                }
                for name, p in self.performance.items()
            },
            'weights': {
                name: round(p.current_weight, 2) for name, p in self.performance.items()
            },
        }

    def get_all_positions(self) -> Dict:
        """获取所有持仓"""
        return dict(self.ai_positions)

    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """获取最近交易"""
        records = sorted(self.ai_trades, key=lambda x: x.entry_time, reverse=True)[:limit]
        return [asdict(r) for r in records]

    # ==================== 数据持久化 ====================

    def _load_data(self):
        """加载历史数据"""
        try:
            if os.path.exists(self.JOURNAL_FILE):
                with open(self.JOURNAL_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.ai_trades = [AITradeRecord(**r) for r in data.get('trades', [])]
                    self.daily_pnl = data.get('daily_pnl', 0.0)
                    self.daily_start_time = data.get('daily_start_time', '')
                    # 加载权重
                    weights = data.get('weights', {})
                    for name, w in weights.items():
                        if name in self.performance:
                            self.performance[name].current_weight = w
                            self.performance[name].win_count = data.get('win_counts', {}).get(name, 0)
                            self.performance[name].loss_count = data.get('loss_counts', {}).get(name, 0)
                    # 重建策略参数
                    params = data.get('strategy_params', {})
                    for name, p in params.items():
                        if name in self.strategies:
                            sp = self.strategies[name].params
                            sp.stop_loss_pct = p.get('stop_loss_pct', sp.stop_loss_pct)
                            sp.take_profit_pct = p.get('take_profit_pct', sp.take_profit_pct)
                            sp.position_pct = p.get('position_pct', sp.position_pct)
                self.log_func(f"[AI交易] 加载历史数据: {len(self.ai_trades)}笔交易记录")

            if os.path.exists(self.STATS_FILE):
                with open(self.STATS_FILE, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.consecutive_losses = stats.get('consecutive_losses', 0)
        except Exception as e:
            self.log_func(f"[AI交易] 加载数据失败: {e}", level='WARNING')

    def _save_data(self):
        """保存数据"""
        try:
            os.makedirs(self.DATA_DIR, exist_ok=True)
            # 交易记录
            journal = {
                'daily_pnl': self.daily_pnl,
                'daily_start_time': self.daily_start_time or datetime.now().strftime('%Y-%m-%d'),
                'trades': [asdict(r) for r in self.ai_trades[-500:]],  # 只保留最近500笔
                'weights': {name: p.current_weight for name, p in self.performance.items()},
                'win_counts': {name: p.win_count for name, p in self.performance.items()},
                'loss_counts': {name: p.loss_count for name, p in self.performance.items()},
                'strategy_params': {
                    name: {
                        'stop_loss_pct': s.params.stop_loss_pct,
                        'take_profit_pct': s.params.take_profit_pct,
                        'position_pct': s.params.position_pct,
                    }
                    for name, s in self.strategies.items()
                },
            }
            with open(self.JOURNAL_FILE, 'w', encoding='utf-8') as f:
                json.dump(journal, f, ensure_ascii=False, indent=2)

            # 统计数据
            stats = {
                'consecutive_losses': self.consecutive_losses,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(self.STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_func(f"[AI交易] 保存数据失败: {e}", level='WARNING')
