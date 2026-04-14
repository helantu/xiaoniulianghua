"""
交易引擎 - 核心调度模块，驱动扫描/分析/下单全流程
"""
import json
import os
import time
import logging
import threading
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Dict
from .binance_client import BinanceClientManager
from .analyzer import TechnicalAnalyzer, SignalScore
from .rules import RuleEngine, TradeDecision
from .grid_strategy import GridStrategy, GridConfig
from .boll_strategy import BollStrategy, BollConfig
from .scalping_strategy import ScalpingStrategy
from .scalping_config import ScalpingConfig
from .ai_trader import AITrader

logger = logging.getLogger(__name__)

# 默认监控币种
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']


@dataclass
class TradeRecord:
    """成交记录"""
    id: str
    symbol: str
    action: str          # BUY / SELL
    trade_type: str      # SPOT / FUTURES
    price: float
    quantity: float
    amount: float        # 金额
    pnl: float = 0.0     # 盈亏（卖出时计算）
    score: float = 0.0
    reason: str = ""
    timestamp: str = ""
    order_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@dataclass
class EngineConfig:
    """引擎参数配置"""
    # 监控参数
    symbols: list = field(default_factory=lambda: DEFAULT_SYMBOLS.copy())
    scan_interval: int = 30          # 扫描间隔（秒）- 剥头皮用30秒
    kline_interval: str = '5m'       # K线周期 - 剥头皮用5分钟
    kline_limit: int = 200           # K线数量

    # 交易参数（优化版：止损2.5% / 止盈4%，更适合15分钟K线）
    buy_threshold: float = 7.0       # 买入评分阈值（提高到7.0，减少噪音信号）
    sell_threshold: float = 2.0      # 卖出评分阈值
    buy_quantity_pct: float = 0.1    # 买入仓位百分比
    max_position_pct: float = 0.3    # 单币最大仓位
    stop_loss_pct: float = 2.5       # 止损百分比（从5%降到2.5%，更早止损）
    take_profit_pct: float = 4.0     # 止盈百分比（从10%降到4%，更现实可达）

    # 合约参数
    futures_enabled: bool = False    # 关闭合约交易（先做现货稳定）
    futures_leverage: int = 3
    futures_buy_threshold: float = 7.0
    futures_qty_pct: float = 0.05

    # 目标营收
    target_profit: float = 1000.0    # 目标盈利（USDT）
    daily_target: float = 100.0      # 日目标

    # 模拟模式
    paper_trading: bool = True       # 模拟交易（默认开启）

    # 策略开关
    grid_strategy_enabled: bool = False   # 关闭网格抄底策略（减少重复下单）
    boll_strategy_enabled: bool = False   # 关闭布林带策略（避免FLIP反手冲突）
    score_strategy_enabled: bool = False  # 关闭评分策略（改用剥头皮策略）
    scalping_enabled: bool = True         # 【主策略】剥头皮网格策略

    # 剥头皮2.0参数
    scalping_take_profit_pct: float = 0.5    # 止盈 0.5%（固定止盈，动态止盈关闭时使用）
    scalping_stop_loss_pct: float = 0.3      # 止损 0.3%（快速止损）
    scalping_position_pct: float = 0.10      # 每次买入10%仓位
    scalping_max_position_pct: float = 0.30  # 单币最大30%仓位
    scalping_rsi_oversold: float = 35.0      # RSI超卖阈值（2.0去掉弱信号，只保留强信号）
    scalping_max_add: int = 3                # 最多补仓3次
    scalping_cooldown: int = 15 * 60         # 止损后冷却15分钟
    scalping_kline_interval: str = '5m'      # 剥头皮用5分钟K线（高频）
    # 2.0新增参数
    scalping_dynamic_tp: bool = True         # 启用动态止盈
    scalping_tp_wide: float = 0.8            # 宽幅行情止盈 0.8%
    scalping_tp_narrow: float = 0.35         # 震荡行情止盈 0.35%
    scalping_boll_wide_threshold: float = 3.0  # 布林带宽度>3%视为宽幅行情
    scalping_trend_filter: bool = True       # 启用1小时趋势过滤（防逆势入场）
    scalping_trend_kline: str = '1h'         # 趋势过滤K线周期
    scalping_trend_ema: int = 50             # 趋势过滤EMA周期

    # AI交易参数
    ai_trader_enabled: bool = True           # 启用AI自适应交易
    ai_scan_interval: int = 60              # AI扫描间隔（秒，每分钟）
    ai_review_interval: int = 3600          # AI复盘间隔（秒，每小时）
    ai_symbols: list = field(default_factory=lambda: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'])


class TradingEngine:
    """小牛量化交易引擎"""

    DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'data', 'trade_data.json')

    def __init__(self):
        self.config = EngineConfig()
        self.client = BinanceClientManager()
        self.analyzer = TechnicalAnalyzer()
        self.rule_engine = RuleEngine()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 状态数据
        self.positions: dict = {}      # {symbol: {qty, entry_price, entry_time}}
        self.trade_records: list = []  # 历史成交
        self.scan_results: dict = {}   # 最新扫描结果 {symbol: SignalScore}
        self.total_pnl: float = 0.0    # 累计盈亏
        self.daily_pnl: float = 0.0    # 今日盈亏
        self.last_scan_time: str = ""
        self.oco_orders: dict = {}     # {symbol: [orderIds]} 记录OCO订单ID

        # ========== 止损冷却期 ==========
        # 止损后30分钟内不再开同一币种，防止连续亏损
        self._cooldown_seconds: int = 30 * 60  # 30分钟
        self._last_stop_loss: dict = {}  # {symbol: timestamp} 记录止损时间

        # 策略实例
        self.grid_strategies: Dict[str, GridStrategy] = {}
        self.boll_strategies: Dict[str, BollStrategy] = {}
        self.scalping_strategies: Dict[str, ScalpingStrategy] = {}

        # AI交易引擎
        self.ai_trader: Optional[AITrader] = None
        self._ai_last_scan: float = 0.0
        self._ai_last_review: float = 0.0

        # 回调钩子
        self.on_log: Optional[Callable] = None          # 日志回调
        self.on_signal: Optional[Callable] = None       # 信号回调
        self.on_trade: Optional[Callable] = None        # 成交回调
        self.on_scan_done: Optional[Callable] = None    # 扫描完成回调
        self.on_scalping_status: Optional[Callable] = None  # 剥头皮状态回调 (symbol, price, status_dict)

        self._load_data()

    # ==================== 启动/停止 ====================

    def start(self):
        """启动引擎"""
        if self._running:
            self._log("引擎已在运行中")
            return
        if not self.client.connect():
            self._log("⚠️ 币安API连接失败，请检查配置", level='WARNING')
            # 仍然允许在模拟模式下运行
            if not self.config.paper_trading:
                return

        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

        # 初始化AI交易引擎
        if self.config.ai_trader_enabled:
            self.ai_trader = AITrader(self.client, log_func=self._log)
            self.ai_trader.on_trade = self._on_ai_trade
            self._log(f"[AI交易] 🤖 AI自适应交易引擎已启动 | 监控: {', '.join(self.config.ai_symbols)}")

        mode = "📋模拟交易" if self.config.paper_trading else "🔴实盘交易"
        self._log(f"🚀 小牛量化引擎启动 | {mode} | 监控: {', '.join(self.config.symbols)}")

    def stop(self):
        """停止引擎"""
        self._running = False
        self._log("⏹️ 引擎已停止")

    @property
    def is_running(self) -> bool:
        return self._running

    # ==================== 扫描循环 ====================

    def _scan_loop(self):
        """主扫描循环"""
        self._ai_last_scan = time.time()
        self._ai_last_review = time.time()
        while self._running:
            try:
                self._do_scan()

                # AI交易扫描（每60秒）
                if self.config.ai_trader_enabled and self.ai_trader:
                    elapsed = time.time() - self._ai_last_scan
                    if elapsed >= self.config.ai_scan_interval:
                        self._run_ai_trader_scan()
                        self._ai_last_scan = time.time()

                    # AI持仓检查（每次都检查）
                    self._run_ai_position_check()

                    # AI每小时复盘
                    review_elapsed = time.time() - self._ai_last_review
                    if review_elapsed >= self.config.ai_review_interval:
                        self._log("[AI复盘] ⏰ 触发每小时复盘")
                        self.ai_trader.hourly_review()
                        self._ai_last_review = time.time()

                # 等待下次扫描
                for _ in range(self.config.scan_interval):
                    if not self._running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"扫描循环异常: {e}", exc_info=True)
                self._log(f"❌ 扫描异常: {e}", level='ERROR')
                time.sleep(10)

    def _do_scan(self):
        """执行一轮扫描"""
        self.last_scan_time = datetime.now().strftime('%H:%M:%S')
        self._log(f"开始扫描 [{self.last_scan_time}] | 周期:{self.config.kline_interval}")

        for symbol in self.config.symbols:
            if not self._running:
                break
            try:
                klines = self.client.get_klines(
                    symbol, self.config.kline_interval, self.config.kline_limit
                )
                if not klines:
                    continue

                current_price = float(klines[-1][4])

                # 1. 评分策略
                if self.config.score_strategy_enabled:
                    self._run_score_strategy(symbol, klines)

                # 2. 网格抄底策略
                if self.config.grid_strategy_enabled:
                    self._run_grid_strategy(symbol, current_price, klines)

                # 3. 布林带策略
                if self.config.boll_strategy_enabled:
                    self._run_boll_strategy(symbol, klines)

                # 4. 剥头皮网格策略（独立5分钟K线）
                if self.config.scalping_enabled:
                    self._run_scalping_strategy(symbol)
                    # 触发剥头皮状态回调
                    if self.on_scalping_status and symbol in self.scalping_strategies:
                        status = self.scalping_strategies[symbol].get_status()
                        self.on_scalping_status(symbol, current_price, status)

            except Exception as e:
                logger.error(f"扫描 {symbol} 失败: {e}")
                self._log(f"  [错误] {symbol} 扫描失败: {e}", level='ERROR')

        if self.on_scan_done:
            self.on_scan_done(self.scan_results)

    def _run_score_strategy(self, symbol: str, klines: list):
        """运行评分策略"""
        score = self.analyzer.analyze(
            symbol, klines,
            buy_threshold=self.config.buy_threshold,
            sell_threshold=self.config.sell_threshold
        )

        with self._lock:
            self.scan_results[symbol] = score

        self._log(
            f"  {symbol}: {score.price:.4f} | "
            f"评分:{score.score_str} | 信号:{score.signal}"
        )

        if self.on_signal:
            self.on_signal(score)

        # 执行规则评估
        context = {
            'params': {**self.config.__dict__},
            'positions': self.positions,
            'balance': self._get_balance(),
        }
        decisions = self.rule_engine.evaluate(score, context)
        for decision in decisions:
            self._execute_decision(symbol, score, decision)

    def _run_grid_strategy(self, symbol: str, current_price: float, klines: list):
        """运行网格抄底策略"""
        if symbol not in self.grid_strategies:
            config = GridConfig(symbol=symbol, enabled=True)
            self.grid_strategies[symbol] = GridStrategy(config)

        grid = self.grid_strategies[symbol]
        
        # 更新价格并获取状态
        signal = grid.update_price(current_price)
        status = grid.get_status()
        
        # 输出网格状态日志
        if status['base_price']:
            drop_pct = (status['base_price'] - current_price) / status['base_price'] * 100
            grid_levels_filled = sum(1 for v in status['grid_levels'].values() if v)
            grid_levels_total = len(status['grid_levels'])
            self._log(f"  [网格] {symbol}: 基准{status['base_price']:.4f} 当前跌幅{drop_pct:.1f}% "
                     f"档位{grid_levels_filled}/{grid_levels_total} 持仓成本{status['avg_cost']:.4f}")
        else:
            self._log(f"  [网格] {symbol}: 初始化基准价格 {current_price:.4f}")

        # 检查买入信号
        if signal:
            self._log(f"  [网格信号] {symbol} {signal['reason']}")
            self._execute_strategy_signal(symbol, signal, current_price)

        # 检查卖出信号（止盈止损）
        sell_signal = grid.check_sell(current_price)
        if sell_signal:
            self._log(f"  [网格信号] {symbol} {sell_signal['reason']}")
            self._execute_strategy_signal(symbol, sell_signal, current_price)
            grid.reset()  # 重置网格

        # 检查极端行情
        extreme_signal = grid.check_extreme(current_price, klines)
        if extreme_signal:
            self._log(f"  [网格信号] {symbol} {extreme_signal['reason']}")
            self._execute_strategy_signal(symbol, extreme_signal, current_price)
            grid.reset()

    def _run_boll_strategy(self, symbol: str, klines: list):
        """运行布林带策略"""
        if symbol not in self.boll_strategies:
            config = BollConfig(symbol=symbol, enabled=True)
            self.boll_strategies[symbol] = BollStrategy(config)

        boll = self.boll_strategies[symbol]
        
        # 计算布林带数值
        prices = [float(k[4]) for k in klines]
        current_price = prices[-1]
        middle, upper, lower = boll.calculate_bollinger(prices)
        
        # 获取状态
        status = boll.get_status()
        
        # 输出布林带状态日志
        if middle and upper and lower:
            # 计算价格在布林带中的位置 (0-100%)
            if upper != lower:
                position_pct = (current_price - lower) / (upper - lower) * 100
            else:
                position_pct = 50
            
            position_str = status['position']
            entry_str = f" 入场{status['entry_price']:.4f}" if status['entry_price'] > 0 else ""
            
            self._log(f"  [布林带] {symbol}: 中轨{middle:.4f} 上轨{upper:.4f} 下轨{lower:.4f} "
                     f"位置{position_pct:.1f}% 持仓[{position_str}]{entry_str}")
        else:
            self._log(f"  [布林带] {symbol}: 计算中...")

        # 分析信号
        signal = boll.analyze(klines)
        if signal:
            self._log(f"  [布林带信号] {symbol} {signal['reason']}")
            self._execute_strategy_signal(symbol, signal, current_price)

    # ==================== AI交易引擎 ====================

    def _run_ai_trader_scan(self):
        """AI交易：多币种扫描并决策"""
        ai = self.ai_trader
        if not ai:
            return

        balance = self._get_balance()
        if balance < 15:
            self._log("[AI交易] ⚠️ 余额不足，跳过AI扫描")
            return

        scanned_count = 0
        for symbol in self.config.ai_symbols:
            try:
                klines_15m = self.client.get_klines(symbol, '15m', 200)
                klines_1h = self.client.get_klines(symbol, '1h', 100)
                if not klines_15m:
                    continue

                current_price = float(klines_15m[-1][4])
                results = ai.analyze_symbol(symbol, klines_15m, klines_1h)

                if results:
                    top_signal, weighted_score = results[0]
                    if ai.should_enter(symbol, top_signal, weighted_score, balance):
                        ai.open_position(symbol, top_signal, balance)
                        scanned_count += 1
                scanned_count += 1
            except Exception as e:
                self._log(f"  [AI交易] {symbol} 扫描失败: {e}", level='WARNING')

        if scanned_count > 0:
            status = ai.get_status()
            self._log(
                f"[AI交易] 扫描完成 | 活跃持仓:{status['active_positions']} "
                f"日盈亏:${status['daily_pnl']:.2f} "
                f"权重:{'/'.join(f'{k}={v}' for k,v in status['weights'].items())}"
            )

    def _run_ai_position_check(self):
        """AI交易：检查所有持仓是否触发止盈止损"""
        ai = self.ai_trader
        if not ai:
            return

        positions = ai.get_all_positions()
        for symbol in list(positions.keys()):
            try:
                klines = self.client.get_klines(symbol, '3m', 5)
                if not klines:
                    continue
                current_price = float(klines[-1][4])
                ai.check_and_close(symbol, current_price)
            except Exception as e:
                pass  # 忽略单个持仓检查失败

    def _on_ai_trade(self, record):
        """AI交易记录回调"""
        if record:
            self._log(
                f"[AI交易] 📋 记录: {record.symbol} "
                f"{record.action} {record.entry_price:.4f}→{record.exit_price:.4f} "
                f"策略:{record.strategy} PnL=${record.pnl:.2f}({record.pnl_pct:.2f}%) "
                f"{'止盈✓' if record.tp_reached else '止损✗' if record.sl_reached else ''}"
            )
            if self.on_trade:
                self.on_trade(record)

    def _run_scalping_strategy(self, symbol: str):
        """运行剥头皮网格策略"""
        # 获取5分钟K线（剥头皮专用高频周期）
        try:
            klines = self.client.get_klines(
                symbol, self.config.scalping_kline_interval, 200
            )
        except Exception as e:
            self._log(f"  [剥头皮] {symbol} 获取K线失败: {e}", level='WARNING')
            return

        if not klines:
            return

        current_price = float(klines[-1][4])

        # 初始化或更新策略实例
        if symbol not in self.scalping_strategies:
            cfg = ScalpingConfig(
                symbol=symbol,
                enabled=True,
                take_profit_pct=self.config.scalping_take_profit_pct,
                stop_loss_pct=self.config.scalping_stop_loss_pct,
                position_pct=self.config.scalping_position_pct,
                max_position_pct=self.config.scalping_max_position_pct,
                rsi_oversold=self.config.scalping_rsi_oversold,
                max_add_positions=self.config.scalping_max_add,
                cooldown_seconds=self.config.scalping_cooldown,
                kline_interval=self.config.scalping_kline_interval,
                # 2.0新增参数
                dynamic_tp_enabled=self.config.scalping_dynamic_tp,
                take_profit_wide_pct=self.config.scalping_tp_wide,
                take_profit_narrow_pct=self.config.scalping_tp_narrow,
                boll_wide_threshold=self.config.scalping_boll_wide_threshold,
                trend_filter_enabled=self.config.scalping_trend_filter,
                trend_kline_interval=self.config.scalping_trend_kline,
                trend_ema_period=self.config.scalping_trend_ema,
            )
            self.scalping_strategies[symbol] = ScalpingStrategy(cfg)
            self._log(
                f"  [剥头皮2.0] {symbol} 初始化策略 "
                f"止损{cfg.stop_loss_pct}% "
                f"动态止盈({cfg.take_profit_narrow_pct}%~{cfg.take_profit_wide_pct}%) "
                f"趋势过滤={'开' if cfg.trend_filter_enabled else '关'}"
            )

        scalper = self.scalping_strategies[symbol]
        scalper.update_klines(klines)

        # 获取1小时K线用于趋势过滤（剥头皮2.0新增）
        if self.config.scalping_trend_filter:
            try:
                klines_1h = self.client.get_klines(
                    symbol, self.config.scalping_trend_kline, 100
                )
                if klines_1h:
                    scalper.update_klines_1h(klines_1h)
            except Exception as e:
                self._log(f"  [剥头皮2.0] {symbol} 获取1小时K线失败: {e}", level='WARNING')

        status = scalper.get_status()

        # 日志输出当前状态
        if status['in_position']:
            pnl_pct = (current_price - status['avg_cost']) / status['avg_cost'] * 100
            self._log(
                f"  [剥头皮] {symbol}: 持仓均价{status['avg_cost']:.4f} "
                f"当前{current_price:.4f}({pnl_pct:+.2f}%) "
                f"止盈{status['take_profit_price']:.4f}/止损{status['stop_loss_price']:.4f} "
                f"补仓{status['add_count']}次"
            )
        elif status['in_cooldown']:
            mins = status['cooldown_remaining'] // 60
            secs = status['cooldown_remaining'] % 60
            self._log(
                f"  [剥头皮] {symbol}: 冷却中({mins}分{secs}秒) "
                f"连损{status['consecutive_losses']}次"
            )
        else:
            rsi = status.get('rsi', 0)
            trend_ok = status.get('trend_ok', True)
            boll_w = status.get('boll_width_pct', 0)
            tp_pct = status.get('dynamic_tp_pct', self.config.scalping_take_profit_pct)
            self._log(
                f"  [剥头皮2.0] {symbol}: 观望中 "
                f"RSI={rsi:.1f} 趋势={'✓' if trend_ok else '✗逆势'} "
                f"BB宽={boll_w:.1f}% 动态止盈={tp_pct}%"
            )

        # ========== 执行交易检查 ==========
        balance = self._get_balance()
        if balance <= 0:
            return

        # 检查卖出（止盈/止损触发）
        if status['in_position'] and scalper.should_sell():
            # 获取持仓信息
            state = scalper.state
            qty = state.total_qty
            avg_cost = state.avg_cost

            # 使用平均成本计算盈亏
            pnl = (current_price - avg_cost) * qty
            pnl_pct = pnl / (avg_cost * qty) * 100 if avg_cost > 0 else 0

            # 记录卖出
            reason = "剥头皮止盈" if pnl >= 0 else "剥头皮止损"
            self._log(
                f"  [剥头皮] {symbol} {reason}: "
                f"均价{avg_cost:.4f}→{current_price:.4f}({pnl_pct:+.2f}%) "
                f"Qty:{qty:.6f} PnL:{pnl:+.4f}U"
            )

            # 执行卖出（模拟）
            if self.config.paper_trading:
                order_id = f"SCALP_SELL_{int(time.time()*1000)}"
            else:
                order = self.client.spot_market_sell(symbol, qty)
                order_id = str(order.get('orderId', '')) if order else ''

            self._record_scalp_trade(symbol, 'SELL', current_price, qty, order_id, reason, pnl)

            # 止损后启动冷却期
            if pnl < 0:
                scalper.start_cooldown()

            scalper.on_trade()
            return

        # 检查买入信号
        if not status['in_position'] and not status['in_cooldown']:
            if scalper.should_buy():
                # 计算买入数量
                trade_amount = balance * self.config.scalping_position_pct
                MIN_ORDER_VALUE = 10.0
                if trade_amount < MIN_ORDER_VALUE:
                    trade_amount = MIN_ORDER_VALUE

                # 检查仓位上限
                pos_value = self.positions.get(symbol, {}).get('qty', 0) * current_price
                total_value = balance + sum(
                    v.get('qty', 0) * current_price
                    for v in self.positions.values()
                )
                if pos_value / (total_value + 1e-10) >= self.config.scalping_max_position_pct:
                    self._log(f"  [剥头皮] {symbol} 仓位已满({self.config.scalping_max_position_pct*100:.0f}%)，跳过")
                    return

                qty = trade_amount / current_price
                qty = self._round_quantity(symbol, qty)

                if qty <= 0:
                    return

                # 执行买入
                if self.config.paper_trading:
                    order_id = f"SCALP_BUY_{int(time.time()*1000)}"
                else:
                    order = self.client.spot_market_buy(symbol, qty)
                    order_id = str(order.get('orderId', '')) if order else ''

                # 更新剥头皮策略状态
                scalper.execute_buy(current_price, qty)
                scalper.on_trade()

                # 同步到主引擎持仓
                self._record_scalp_trade(symbol, 'BUY', current_price, qty, order_id,
                                        f"剥头皮2.0买入(RSI<{self.config.scalping_rsi_oversold}+趋势✓)", 0)

                new_status = scalper.get_status()
                self._log(
                    f"  [剥头皮2.0] ✅ {symbol} 买入成功: "
                    f"价格{current_price:.4f} 数量{qty:.6f} "
                    f"止盈{new_status['take_profit_price']:.4f}({new_status['dynamic_tp_pct']}%) "
                    f"止损{new_status['stop_loss_price']:.4f}"
                )
                return

        # 检查补仓信号（价格继续下跌）
        if status['in_position'] and scalper.should_add_position():
            trade_amount = balance * self.config.scalping_position_pct
            MIN_ORDER_VALUE = 10.0
            if trade_amount < MIN_ORDER_VALUE:
                trade_amount = MIN_ORDER_VALUE

            qty = trade_amount / current_price
            qty = self._round_quantity(symbol, qty)

            if qty <= 0:
                return

            if self.config.paper_trading:
                order_id = f"SCALP_ADD_{int(time.time()*1000)}"
            else:
                order = self.client.spot_market_buy(symbol, qty)
                order_id = str(order.get('orderId', '')) if order else ''

            scalper.execute_buy(current_price, qty)
            self._record_scalp_trade(symbol, 'BUY', current_price, qty, order_id,
                                    f"剥头皮补仓({scalper.state.add_count}次)", 0)

            new_status = scalper.get_status()
            self._log(
                f"  [剥头皮] 📍 {symbol} 补仓成功: "
                f"均价{new_status['avg_cost']:.4f} 数量{qty:.6f} "
                f"(累计{new_status['add_count']}次)"
            )

    def _record_scalp_trade(self, symbol: str, action: str, price: float,
                             qty: float, order_id: str, reason: str, pnl: float):
        """记录剥头皮交易（同步持仓到主引擎）"""
        amount = price * qty

        with self._lock:
            if action == "BUY":
                if symbol in self.positions:
                    # 补仓：更新均价
                    old = self.positions[symbol]
                    total_qty = old['qty'] + qty
                    new_avg = (old['entry_price'] * old['qty'] + price * qty) / total_qty
                    self.positions[symbol] = {
                        'qty': total_qty,
                        'entry_price': new_avg,
                        'entry_time': old['entry_time'],
                        'amount': old['amount'] + amount,
                    }
                else:
                    self.positions[symbol] = {
                        'qty': qty,
                        'entry_price': price,
                        'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'amount': amount,
                    }
            elif action == "SELL" and symbol in self.positions:
                pos = self.positions[symbol]
                self.total_pnl += pnl
                self.daily_pnl += pnl
                if qty >= pos['qty']:
                    del self.positions[symbol]
                else:
                    self.positions[symbol]['qty'] -= qty

            record = TradeRecord(
                id=f"S{len(self.trade_records)+1:05d}",
                symbol=symbol,
                action=action,
                trade_type='SPOT',
                price=price,
                quantity=qty,
                amount=amount,
                pnl=pnl,
                score=0,
                reason=reason,
                order_id=order_id,
            )
            self.trade_records.append(record)
            self._save_data()

        if self.on_trade:
            self.on_trade(record)

    def _execute_strategy_signal(self, symbol: str, signal: dict, price: float):
        """执行策略信号"""
        action = signal['action']
        quantity_pct = signal.get('quantity_pct', 0.1)
        reason = signal.get('reason', '')

        # ========== 修复FLIP反手Bug ==========
        # FLIP信号：只平仓，不反手开新仓
        # 反手逻辑在15分钟K线里会产生大量无意义交易
        if action in ('FLIP_SHORT', 'FLIP_LONG'):
            # 先检查是否有持仓需要平
            existing_pos = self.positions.get(symbol, {}).get('qty', 0)
            if existing_pos <= 0:
                self._log(f"  ⛔ {symbol} 无持仓，跳过平仓")
                return
            # 改为只平仓的SELL信号
            action = 'SELL'
            self._log(f"  🔄 {symbol} 布林带反手→改为仅平仓观望（不反手开仓）")
        # ========== FLIP修复 END ==========

        # 创建决策对象
        decision = TradeDecision(
            should_trade=True,
            action=action,
            quantity_pct=quantity_pct,
            score=0,
            reason=reason,
            trade_type='SPOT',
            leverage=1
        )

        # 创建临时的SignalScore对象
        from .analyzer import SignalScore
        score = SignalScore(symbol=symbol, price=price, total_score=0)

        self._execute_decision(symbol, score, decision)

    # ==================== 交易执行 ====================

    def _execute_decision(self, symbol: str, score: SignalScore, decision: TradeDecision):
        """执行交易决策"""
        balance = self._get_balance()
        price = score.price
        if price <= 0:
            return

        # ========== 修复重复下单Bug ==========
        # 在下单前检查该币种是否已有持仓（现货+合约都检查）
        existing_pos = self.positions.get(symbol, {}).get('qty', 0)
        if decision.action == "BUY" and existing_pos > 0:
            self._log(
                f"  ⛔ {symbol} 已有持仓({existing_pos:.6f})，跳过重复买入"
            )
            return

        # ========== 止损冷却期 ==========
        # 止损后30分钟内不再开同一币种
        if decision.action == "BUY" and symbol in self._last_stop_loss:
            elapsed = time.time() - self._last_stop_loss[symbol]
            if elapsed < self._cooldown_seconds:
                remaining = int(self._cooldown_seconds - elapsed)
                self._log(
                    f"  ⛔ {symbol} 刚止损({int(elapsed//60)}分钟前)，"
                    f"冷却中({remaining//60}分{remaining%60}秒后解锁)"
                )
                return
            else:
                # 冷却期已过，清除记录
                del self._last_stop_loss[symbol]
        # ========== 冷却期 END ==========

        # 计算数量
        trade_amount = balance * decision.quantity_pct

        # 检查最小订单金额 (币安要求至少 10 USDT)
        MIN_ORDER_VALUE = 10.0
        if trade_amount < MIN_ORDER_VALUE:
            # 低于最小限制时，按最小金额交易
            trade_amount = MIN_ORDER_VALUE
            self._log(f"  ℹ️ {symbol} 订单金额低于 {MIN_ORDER_VALUE}U，调整为最小金额 {trade_amount:.2f}U")

        quantity = trade_amount / price
        quantity = self._round_quantity(symbol, quantity)

        if quantity <= 0:
            self._log(f"  ⚠️ {symbol} 计算数量为0，跳过", level='WARNING')
            return

        # 检查仓位
        if decision.action == "BUY":
            pos_value = self.positions.get(symbol, {}).get('qty', 0) * price
            total_value = balance + sum(
                v.get('qty', 0) * score.price
                for v in self.positions.values()
            )
            if pos_value / (total_value + 1e-10) >= self.config.max_position_pct:
                self._log(f"  ⚠️ {symbol} 仓位已满({self.config.max_position_pct*100:.0f}%)，跳过买入")
                return

        self._log(
            f"  📊 决策触发: {decision.action} {symbol} | "
            f"数量:{quantity:.6f} | 金额:{trade_amount:.2f}U | "
            f"原因:{decision.reason}"
        )

        # 模拟模式 / 实盘
        if self.config.paper_trading:
            order_id = f"PAPER_{int(time.time()*1000)}"
            success = True
        else:
            order = self._place_order(symbol, decision, quantity)
            success = bool(order)
            order_id = str(order.get('orderId', '')) if order else ''

        if success:
            self._record_trade(symbol, decision, price, quantity, order_id)

    def _place_order(self, symbol: str, decision: TradeDecision, quantity: float) -> dict:
        """实盘下单"""
        try:
            if decision.trade_type == "SPOT":
                if decision.action == "BUY":
                    return self.client.spot_market_buy(symbol, quantity)
                else:
                    # 卖出前先取消OCO订单，避免冲突
                    self._cancel_oco_orders(symbol)
                    return self.client.spot_market_sell(symbol, quantity)
            elif decision.trade_type == "FUTURES":
                side = "BUY" if decision.action == "BUY" else "SELL"
                return self.client.futures_market_order(
                    symbol, side, quantity, decision.leverage
                )
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {}

    def _record_trade(self, symbol: str, decision: TradeDecision,
                       price: float, quantity: float, order_id: str):
        """记录成交"""
        amount = price * quantity
        pnl = 0.0

        with self._lock:
            if decision.action == "BUY":
                self.positions[symbol] = {
                    'qty': quantity,
                    'entry_price': price,
                    'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'amount': amount,
                }
                # 实盘模式下创建OCO止盈止损单
                if not self.config.paper_trading and decision.trade_type == "SPOT":
                    self._create_oco_order(symbol, price, quantity)

            elif decision.action == "SELL" and symbol in self.positions:
                pos = self.positions[symbol]
                pnl = (price - pos['entry_price']) * min(quantity, pos['qty'])
                self.total_pnl += pnl
                self.daily_pnl += pnl
                if quantity >= pos['qty']:
                    del self.positions[symbol]
                    # 清仓时取消OCO订单
                    if not self.config.paper_trading:
                        self._cancel_oco_orders(symbol)
                else:
                    self.positions[symbol]['qty'] -= quantity

            # 止损时记录冷却时间
            if decision.action == "SELL" and "止损" in decision.reason:
                self._last_stop_loss[symbol] = time.time()
                self._log(f"  🔒 {symbol} 止损，记录30分钟冷却期")

            record = TradeRecord(
                id=f"T{len(self.trade_records)+1:05d}",
                symbol=symbol,
                action=decision.action,
                trade_type=decision.trade_type,
                price=price,
                quantity=quantity,
                amount=amount,
                pnl=pnl,
                score=decision.score,
                reason=decision.reason,
                order_id=order_id,
            )
            self.trade_records.append(record)
            self._save_data()

        mode_tag = "[模拟]" if self.config.paper_trading else "[实盘]"
        pnl_str = f" | 盈亏:{pnl:+.2f}U" if decision.action == "SELL" else ""
        self._log(
            f"  ✅ {mode_tag} 成交: {decision.action} {symbol} "
            f"@{price:.4f} 数量:{quantity:.6f}{pnl_str}"
        )

        if self.on_trade:
            self.on_trade(record)

    def _create_oco_order(self, symbol: str, entry_price: float, quantity: float):
        """创建OCO止盈止损单"""
        try:
            # 计算止盈止损价格
            take_profit_price = entry_price * (1 + self.config.take_profit_pct / 100)
            stop_loss_price = entry_price * (1 - self.config.stop_loss_pct / 100)

            self._log(f"  🎯 {symbol} 创建OCO单: 止盈{take_profit_price:.4f} / 止损{stop_loss_price:.4f}")

            result = self.client.spot_oco_sell(
                symbol=symbol,
                quantity=quantity,
                stop_price=stop_loss_price,
                limit_price=take_profit_price
            )

            if result and 'orderListId' in result:
                self.oco_orders[symbol] = result['orderListId']
                self._log(f"  ✅ OCO订单创建成功: orderListId={result['orderListId']}")
            else:
                self._log(f"  ⚠️ OCO订单创建失败或返回异常: {result}", level='WARNING')

        except Exception as e:
            self._log(f"  ❌ OCO订单创建异常: {e}", level='ERROR')

    def _cancel_oco_orders(self, symbol: str):
        """取消OCO订单（评分卖出时调用）"""
        try:
            # 获取该币种的所有挂单并取消
            open_orders = self.client.get_open_orders(symbol)
            for order in open_orders:
                self.client.cancel_order(symbol, order['orderId'])
                self._log(f"  🔄 取消挂单: {symbol} orderId={order['orderId']}")
            if symbol in self.oco_orders:
                del self.oco_orders[symbol]
        except Exception as e:
            self._log(f"  ⚠️ 取消OCO订单异常: {e}", level='WARNING')

    # ==================== 辅助方法 ====================

    def _get_balance(self) -> float:
        """获取可用余额（模拟模式返回固定值，实盘返回所有账户总和）"""
        if self.config.paper_trading:
            return 10000.0  # 模拟资金
        balances = self.client.get_total_balance()
        return balances.get('total', 0.0)

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """根据币种精度取整"""
        precisions = {
            'BTCUSDT': 5, 'ETHUSDT': 4, 'SOLUSDT': 3,
            'BNBUSDT': 3
        }
        decimals = precisions.get(symbol, 4)
        return round(quantity, decimals)

    def _log(self, msg: str, level: str = 'INFO'):
        """内部日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_msg = f"[{timestamp}] {msg}"
        if level == 'ERROR':
            logger.error(msg)
        elif level == 'WARNING':
            logger.warning(msg)
        else:
            logger.info(msg)
        if self.on_log:
            self.on_log(full_msg, level)

    def get_stats(self) -> dict:
        """获取统计数据"""
        with self._lock:
            return {
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
                'total_trades': len(self.trade_records),
                'open_positions': len(self.positions),
                'target_profit': self.config.target_profit,
                'daily_target': self.config.daily_target,
                'is_running': self._running,
                'last_scan': self.last_scan_time,
                'paper_trading': self.config.paper_trading,
            }

    def update_config(self, new_config: dict):
        """更新配置"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        # 同步更新分析器参数
        self.analyzer.update_params({
            'buy_threshold': self.config.buy_threshold,
            'sell_threshold': self.config.sell_threshold,
        })
        self._log(f"⚙️ 配置已更新: {new_config}")
        self._save_data()

    def manual_scan(self):
        """手动触发一次扫描"""
        thread = threading.Thread(target=self._do_scan, daemon=True)
        thread.start()

    # ==================== 数据持久化 ====================

    def _save_data(self):
        """保存数据到文件"""
        try:
            data = {
                'config': {k: v for k, v in self.config.__dict__.items()},
                'positions': self.positions,
                'trade_records': [asdict(r) for r in self.trade_records[-500:]],  # 最近500条
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
            }
            os.makedirs(os.path.dirname(self.DATA_FILE), exist_ok=True)
            with open(self.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    def _load_data(self):
        """从文件加载数据"""
        if not os.path.exists(self.DATA_FILE):
            return
        try:
            with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 恢复配置
            for k, v in data.get('config', {}).items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)
            self.positions = data.get('positions', {})
            self.total_pnl = data.get('total_pnl', 0.0)
            self.daily_pnl = data.get('daily_pnl', 0.0)
            # 恢复成交记录
            for r in data.get('trade_records', []):
                try:
                    self.trade_records.append(TradeRecord(**r))
                except Exception:
                    pass
            logger.info(f"数据加载成功: {len(self.trade_records)} 条成交记录")
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
