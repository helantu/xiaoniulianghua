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
from typing import Optional, Callable
from .binance_client import BinanceClientManager
from .analyzer import TechnicalAnalyzer, SignalScore
from .rules import RuleEngine, TradeDecision

logger = logging.getLogger(__name__)

# 默认监控币种
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT']


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
    scan_interval: int = 60          # 扫描间隔（秒）
    kline_interval: str = '15m'      # K线周期
    kline_limit: int = 200           # K线数量

    # 交易参数
    buy_threshold: float = 6.0       # 买入评分阈值
    sell_threshold: float = 2.0      # 卖出评分阈值
    buy_quantity_pct: float = 0.1    # 买入仓位百分比
    max_position_pct: float = 0.3    # 单币最大仓位
    stop_loss_pct: float = 5.0       # 止损百分比
    take_profit_pct: float = 10.0    # 止盈百分比

    # 合约参数
    futures_enabled: bool = False
    futures_leverage: int = 3
    futures_buy_threshold: float = 7.0
    futures_qty_pct: float = 0.05

    # 目标营收
    target_profit: float = 1000.0    # 目标盈利（USDT）
    daily_target: float = 100.0      # 日目标

    # 模拟模式
    paper_trading: bool = True       # 模拟交易（默认开启）


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

        # 回调钩子
        self.on_log: Optional[Callable] = None          # 日志回调
        self.on_signal: Optional[Callable] = None       # 信号回调
        self.on_trade: Optional[Callable] = None        # 成交回调
        self.on_scan_done: Optional[Callable] = None    # 扫描完成回调

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
        while self._running:
            try:
                self._do_scan()
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
        self._log(f"🔍 开始扫描 [{self.last_scan_time}] | 周期:{self.config.kline_interval}")

        for symbol in self.config.symbols:
            if not self._running:
                break
            try:
                klines = self.client.get_klines(
                    symbol, self.config.kline_interval, self.config.kline_limit
                )
                score = self.analyzer.analyze(
                    symbol, klines,
                    buy_threshold=self.config.buy_threshold,
                    sell_threshold=self.config.sell_threshold
                )

                with self._lock:
                    self.scan_results[symbol] = score

                self._log(
                    f"  {symbol}: {score.price:.4f} | "
                    f"评分:{score.score_str} | 信号:{score.signal} | "
                    f"[MACD:{score.macd_score:.1f} BOLL:{score.boll_score:.1f} "
                    f"RSI:{score.rsi_score:.1f} KDJ:{score.kdj_score:.1f}]"
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

            except Exception as e:
                logger.error(f"扫描 {symbol} 失败: {e}")
                self._log(f"  ❌ {symbol} 扫描失败: {e}", level='ERROR')

        if self.on_scan_done:
            self.on_scan_done(self.scan_results)

    # ==================== 交易执行 ====================

    def _execute_decision(self, symbol: str, score: SignalScore, decision: TradeDecision):
        """执行交易决策"""
        balance = self._get_balance()
        price = score.price
        if price <= 0:
            return

        # 计算数量
        trade_amount = balance * decision.quantity_pct
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
            elif decision.action == "SELL" and symbol in self.positions:
                pos = self.positions[symbol]
                pnl = (price - pos['entry_price']) * min(quantity, pos['qty'])
                self.total_pnl += pnl
                self.daily_pnl += pnl
                if quantity >= pos['qty']:
                    del self.positions[symbol]
                else:
                    self.positions[symbol]['qty'] -= quantity

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

    # ==================== 辅助方法 ====================

    def _get_balance(self) -> float:
        """获取可用余额（模拟模式返回固定值）"""
        if self.config.paper_trading:
            return 10000.0  # 模拟资金
        return self.client.get_spot_balance('USDT')

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """根据币种精度取整"""
        precisions = {
            'BTCUSDT': 5, 'ETHUSDT': 4, 'SOLUSDT': 3,
            'DOGEUSDT': 0, 'BNBUSDT': 3
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
