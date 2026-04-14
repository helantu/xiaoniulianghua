"""
小牛量化 - 主界面
PyQt5 可视化界面，包含监控面板、日志、参数、成交记录、营收统计
"""
import sys
import os
from typing import Dict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit, QTableWidget,
    QTableWidgetItem, QGroupBox, QGridLayout, QDoubleSpinBox,
    QSpinBox, QCheckBox, QComboBox, QHeaderView, QSplitter,
    QFrame, QProgressBar, QLineEdit, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QColor, QFont, QPalette, QTextCursor, QIcon
import pyqtgraph as pg
import numpy as np
from datetime import datetime

from src.core.engine import TradingEngine, TradeRecord
from src.core.analyzer import SignalScore
from src.core.strategy_config import get_default_symbol_config, Strategy, SymbolConfig
from dotenv import load_dotenv


# ============================================================
# 样式主题
# ============================================================
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #2d2d4e;
    background: #1a1a2e;
}
QTabBar::tab {
    background: #16213e;
    color: #a0a0c0;
    padding: 8px 20px;
    border: 1px solid #2d2d4e;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #0f3460;
    color: #00d4ff;
    border-color: #00d4ff;
}
QTabBar::tab:hover { background: #0f3460; color: #e0e0e0; }

QPushButton {
    background: #0f3460;
    color: #e0e0e0;
    border: 1px solid #00d4ff;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover { background: #00d4ff; color: #1a1a2e; }
QPushButton:pressed { background: #007acc; }
QPushButton#btn_start { background: #155724; border-color: #28a745; color: #28a745; }
QPushButton#btn_start:hover { background: #28a745; color: white; }
QPushButton#btn_stop { background: #721c24; border-color: #dc3545; color: #dc3545; }
QPushButton#btn_stop:hover { background: #dc3545; color: white; }
QPushButton#btn_scan { background: #0c4a6e; border-color: #0ea5e9; color: #0ea5e9; }
QPushButton#btn_scan:hover { background: #0ea5e9; color: white; }

QGroupBox {
    border: 1px solid #2d2d4e;
    border-radius: 8px;
    margin-top: 12px;
    padding: 8px;
    color: #00d4ff;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #00d4ff;
}

QTableWidget {
    background: #16213e;
    color: #e0e0e0;
    gridline-color: #2d2d4e;
    border: 1px solid #2d2d4e;
    border-radius: 4px;
    selection-background-color: #0f3460;
}
QTableWidget::item:selected { background: #0f3460; }
QHeaderView::section {
    background: #0f3460;
    color: #00d4ff;
    padding: 6px;
    border: 1px solid #2d2d4e;
    font-weight: bold;
}

QTextEdit {
    background: #0d0d1a;
    color: #00ff88;
    border: 1px solid #2d2d4e;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background: #16213e;
    color: #e0e0e0;
    border: 1px solid #2d2d4e;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #0f3460;
}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #00d4ff;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background: #16213e;
    color: #e0e0e0;
    selection-background-color: #0f3460;
}

QCheckBox { color: #e0e0e0; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #2d2d4e;
    border-radius: 3px;
    background: #16213e;
}
QCheckBox::indicator:checked { background: #00d4ff; border-color: #00d4ff; }

QScrollBar:vertical {
    background: #16213e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2d2d4e;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background: #00d4ff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QLabel#label_title {
    color: #00d4ff;
    font-size: 22px;
    font-weight: bold;
}
QLabel#label_subtitle { color: #a0a0c0; font-size: 12px; }
QProgressBar {
    border: 1px solid #2d2d4e;
    border-radius: 6px;
    background: #16213e;
    text-align: center;
    color: white;
    height: 18px;
}
QProgressBar::chunk { background: #00d4ff; border-radius: 5px; }
QFrame#sep { background: #2d2d4e; }
"""


# ============================================================
# 币种监控卡片
# ============================================================
class SymbolCard(QFrame):
    def __init__(self, symbol: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setFixedHeight(130)
        self.setStyleSheet("""
            QFrame {
                background: #16213e;
                border: 1px solid #2d2d4e;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 顶部：币名 + 状态
        top = QHBoxLayout()
        self.lbl_name = QLabel(symbol.replace('USDT', ''))
        self.lbl_name.setStyleSheet("font-size:16px; font-weight:bold; color:#00d4ff;")
        self.lbl_status = QLabel("⚪ 等待")
        self.lbl_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_status.setStyleSheet("font-size:12px; font-weight:bold; padding:2px 8px; border-radius:4px; color:#a0a0c0; background:#333355;")
        top.addWidget(self.lbl_name)
        top.addStretch()
        top.addWidget(self.lbl_status)
        layout.addLayout(top)

        # 价格
        self.lbl_price = QLabel("$--")
        self.lbl_price.setStyleSheet("font-size:18px; font-weight:bold; color:#ffffff;")
        layout.addWidget(self.lbl_price)

        # RSI 条
        rsi_row = QHBoxLayout()
        self.lbl_rsi = QLabel("RSI: --")
        self.lbl_rsi.setStyleSheet("color:#a0a0c0; font-size:12px;")
        self.rsi_bar = QProgressBar()
        self.rsi_bar.setRange(0, 100)
        self.rsi_bar.setValue(0)
        self.rsi_bar.setFixedHeight(10)
        self.rsi_bar.setTextVisible(False)
        rsi_row.addWidget(self.lbl_rsi)
        rsi_row.addWidget(self.rsi_bar)
        layout.addLayout(rsi_row)

        # 持仓信息
        self.lbl_position = QLabel("持仓: 无 | 均价: --")
        self.lbl_position.setStyleSheet("color:#606080; font-size:11px;")
        layout.addWidget(self.lbl_position)

        # 止盈止损
        self.lbl_tp_sl = QLabel("止盈: -- | 止损: --")
        self.lbl_tp_sl.setStyleSheet("color:#606080; font-size:11px;")
        layout.addWidget(self.lbl_tp_sl)

    def update_scalping(self, price: float, status: dict):
        """更新剥头皮策略数据"""
        # 价格
        price_str = f"${price:,.4f}" if price < 1 else f"${price:,.2f}"
        self.lbl_price.setText(price_str)

        # RSI
        rsi = status.get('rsi', 0)
        self.lbl_rsi.setText(f"RSI: {rsi:.1f}")
        self.rsi_bar.setValue(int(rsi))

        # RSI 颜色
        if rsi < 35:
            rsi_color = "#28a745"  # 超卖，绿色
        elif rsi > 65:
            rsi_color = "#dc3545"  # 超买，红色
        else:
            rsi_color = "#ffc107"  # 中性，黄色
        self.rsi_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {rsi_color}; border-radius: 4px; }}"
        )

        # 状态
        in_position = status.get('in_position', False)
        in_cooldown = status.get('in_cooldown', False)
        consecutive_losses = status.get('consecutive_losses', 0)
        cooldown_remaining = status.get('cooldown_remaining', 0)

        if in_position:
            self.lbl_status.setText("🟢 持仓中")
            self.lbl_status.setStyleSheet("font-size:12px; font-weight:bold; padding:2px 8px; border-radius:4px; color:#28a745; background:#1a472a;")
        elif in_cooldown:
            mins = cooldown_remaining // 60
            secs = cooldown_remaining % 60
            self.lbl_status.setText(f"⏳ 冷却 {mins}:{secs:02d}")
            self.lbl_status.setStyleSheet("font-size:12px; font-weight:bold; padding:2px 8px; border-radius:4px; color:#f59e0b; background:#332200;")
        elif consecutive_losses >= 2:
            self.lbl_status.setText(f"⚠️ 连损{consecutive_losses}")
            self.lbl_status.setStyleSheet("font-size:12px; font-weight:bold; padding:2px 8px; border-radius:4px; color:#dc3545; background:#330000;")
        else:
            self.lbl_status.setText("⚪ 等待")
            self.lbl_status.setStyleSheet("font-size:12px; font-weight:bold; padding:2px 8px; border-radius:4px; color:#a0a0c0; background:#333355;")

        # 持仓信息
        if in_position:
            avg_cost = status.get('avg_cost', 0)
            add_count = status.get('add_count', 0)
            self.lbl_position.setText(f"均价: ${avg_cost:,.4f} | 加仓: {add_count}次")
            self.lbl_position.setStyleSheet("color:#28a745; font-size:11px;")
        else:
            self.lbl_position.setText("持仓: 无")
            self.lbl_position.setStyleSheet("color:#606080; font-size:11px;")

        # 止盈止损
        if in_position:
            tp = status.get('take_profit_price', 0)
            sl = status.get('stop_loss_price', 0)
            self.lbl_tp_sl.setText(f"止盈: ${tp:,.4f} | 止损: ${sl:,.4f}")
            self.lbl_tp_sl.setStyleSheet("color:#28a745; font-size:11px;")
        else:
            self.lbl_tp_sl.setText("止盈: -- | 止损: --")
            self.lbl_tp_sl.setStyleSheet("color:#606080; font-size:11px;")


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    signal_log = pyqtSignal(str, str)
    signal_score = pyqtSignal(object)
    signal_trade = pyqtSignal(object)
    signal_stats = pyqtSignal(dict)
    signal_scalping_status = pyqtSignal(str, float, dict)  # symbol, price, status

    def __init__(self):
        super().__init__()
        self.engine = TradingEngine()
        self._setup_engine_callbacks()
        self._init_ui()
        self._start_stat_timer()

    # ==================== 引擎回调绑定 ====================
    def _setup_engine_callbacks(self):
        self.engine.on_log = lambda msg, lvl: self.signal_log.emit(msg, lvl)
        self.engine.on_signal = lambda score: self.signal_score.emit(score)
        self.engine.on_trade = lambda rec: self.signal_trade.emit(rec)
        self.engine.on_scalping_status = lambda sym, price, st: self.signal_scalping_status.emit(sym, price, st)
        self.signal_log.connect(self._append_log)
        self.signal_score.connect(self._on_score_update)
        self.signal_trade.connect(self._on_trade)
        self.signal_scalping_status.connect(self._on_scalping_status)

    # ==================== UI 初始化 ====================
    def _init_ui(self):
        self.setWindowTitle("🐂 小牛量化交易系统 v1.0")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # 顶部标题栏
        main_layout.addWidget(self._build_header())

        # 主内容区
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：币种卡片
        splitter.addWidget(self._build_symbol_panel())

        # 右侧：Tab面板
        splitter.addWidget(self._build_tab_panel())

        splitter.setSizes([320, 1000])
        main_layout.addWidget(splitter)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(64)
        w.setStyleSheet("background: #0f3460; border-radius: 10px;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("🐂 小牛量化交易系统")
        title.setObjectName("label_title")
        layout.addWidget(title)

        layout.addStretch()

        # 状态指示
        self.lbl_status = QLabel("⏸ 未运行")
        self.lbl_status.setStyleSheet("color:#a0a0c0; font-size:13px; font-weight:bold;")
        layout.addWidget(self.lbl_status)

        self.lbl_mode = QLabel("📋 模拟模式")
        self.lbl_mode.setStyleSheet(
            "color:#ffc107; background:#332200; padding:4px 10px; "
            "border-radius:4px; font-weight:bold; margin-left:8px;"
        )
        layout.addWidget(self.lbl_mode)

        layout.addSpacing(16)

        # 控制按钮
        self.btn_start = QPushButton("▶ 启动引擎")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedWidth(110)
        self.btn_start.clicked.connect(self._start_engine)

        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.clicked.connect(self._stop_engine)
        self.btn_stop.setEnabled(False)

        self.btn_scan = QPushButton("🔍 立即扫描")
        self.btn_scan.setObjectName("btn_scan")
        self.btn_scan.setFixedWidth(110)
        self.btn_scan.clicked.connect(self._manual_scan)

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_scan)
        return w

    def _build_symbol_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(310)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(8)

        lbl = QLabel("📊 监控币种")
        lbl.setStyleSheet("color:#00d4ff; font-weight:bold; font-size:14px; padding: 4px 0;")
        layout.addWidget(lbl)

        # 创建币种卡片
        self.symbol_cards: dict[str, SymbolCard] = {}
        for sym in self.engine.config.symbols:
            card = SymbolCard(sym)
            self.symbol_cards[sym] = card
            layout.addWidget(card)

        layout.addStretch()

        # ---- AI实时持仓区块 ----
        ai_header = QLabel("🤖 AI实时持仓")
        ai_header.setStyleSheet("color:#00d4ff; font-weight:bold; font-size:14px; padding: 4px 0;")
        layout.addWidget(ai_header)

        self.ai_panel_container = QWidget()
        self.ai_panel_layout = QVBoxLayout(self.ai_panel_container)
        self.ai_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.ai_panel_layout.setSpacing(4)
        self.ai_panel_labels = {}  # symbol -> {entry, cur, pnl, strat}
        layout.addWidget(self.ai_panel_container)

        # 账户余额
        balance_box = QGroupBox("账户概览")
        bl = QGridLayout(balance_box)
        bl.setSpacing(6)

        # 各账户余额
        self.lbl_bal_spot = QLabel("--")
        self.lbl_bal_spot.setStyleSheet("color:#28a745; font-weight:bold;")
        self.lbl_bal_futures = QLabel("--")
        self.lbl_bal_futures.setStyleSheet("color:#0ea5e9; font-weight:bold;")
        self.lbl_bal_funding = QLabel("--")
        self.lbl_bal_funding.setStyleSheet("color:#f59e0b; font-weight:bold;")
        self.lbl_bal_total = QLabel("--")
        self.lbl_bal_total.setStyleSheet("color:#00d4ff; font-weight:bold; font-size:14px;")
        
        # 盈亏
        self.lbl_pnl_total = QLabel("--")
        self.lbl_pnl_total.setStyleSheet("font-weight:bold; font-size:14px;")
        self.lbl_pnl_daily = QLabel("--")
        self.lbl_pnl_daily.setStyleSheet("font-weight:bold;")

        bl.addWidget(QLabel("现货:"), 0, 0)
        bl.addWidget(self.lbl_bal_spot, 0, 1)
        bl.addWidget(QLabel("合约:"), 0, 2)
        bl.addWidget(self.lbl_bal_futures, 0, 3)
        bl.addWidget(QLabel("资金:"), 1, 0)
        bl.addWidget(self.lbl_bal_funding, 1, 1)
        bl.addWidget(QLabel("总计:"), 1, 2)
        bl.addWidget(self.lbl_bal_total, 1, 3)
        bl.addWidget(QLabel("累计盈亏:"), 2, 0)
        bl.addWidget(self.lbl_pnl_total, 2, 1)
        bl.addWidget(QLabel("今日盈亏:"), 2, 2)
        bl.addWidget(self.lbl_pnl_daily, 2, 3)
        layout.addWidget(balance_box)
        return w

    def _build_tab_panel(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_log_tab(), "📋 监控日志")
        tabs.addTab(self._build_scalping_tab(), "⚡ 剥头皮2.0")
        tabs.addTab(self._build_ai_tab(), "🤖 AI交易")
        tabs.addTab(self._build_trade_tab(), "💰 成交记录")
        tabs.addTab(self._build_profit_tab(), "📈 营收统计")
        tabs.addTab(self._build_params_tab(), "⚙️ 参数调节")
        tabs.addTab(self._build_rules_tab(), "📜 规则管理")
        return tabs

    # ==================== 剥头皮策略 Tab ====================
    def _build_scalping_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ---- 策略说明 ----
        intro = QLabel(
            "⚡ 剥头皮2.0网格策略 | 三重共振入场(BB下轨+RSI<35+1H趋势) | "
            "动态止盈(0.35%~0.8%) | 止损0.3% | 每30秒扫描5分钟K线"
        )
        intro.setStyleSheet("color:#ffd60a; font-size:12px; padding:4px;")
        layout.addWidget(intro)

        # ---- 统计卡片行 ----
        cards_row = QHBoxLayout()

        # 今日交易次数
        card_trades = self._scalping_make_card("今日交易", "0", "#ffd60a", "次")
        self.scalp_cards = {'daily_trades': card_trades['value']}
        cards_row.addWidget(card_trades['widget'])

        # 今日胜率
        card_win = self._scalping_make_card("今日胜率", "0%", "#ffd60a", "")
        self.scalp_cards['win_rate'] = card_win['value']
        cards_row.addWidget(card_win['widget'])

        # 今日剥头皮盈亏
        card_pnl = self._scalping_make_card("今日剥头皮盈亏", "+0.00", "#28a745", "U")
        self.scalp_cards['daily_pnl'] = card_pnl['value']
        cards_row.addWidget(card_pnl['widget'])

        # 累计剥头皮盈亏
        card_total = self._scalping_make_card("累计剥头皮盈亏", "+0.00", "#28a745", "U")
        self.scalp_cards['total_pnl'] = card_total['value']
        cards_row.addWidget(card_total['widget'])

        layout.addLayout(cards_row)

        # ---- 币种状态卡片 ----
        self.scalp_coin_cards = {}
        coin_container = QWidget()
        coin_layout = QHBoxLayout(coin_container)
        coin_layout.setContentsMargins(0, 0, 0, 0)

        for symbol in self.engine.config.symbols:
            card = self._build_scalp_coin_card(symbol)
            self.scalp_coin_cards[symbol] = card
            coin_layout.addWidget(card)

        layout.addWidget(coin_container)

        # ---- 剥头皮交易记录 ----
        trade_box = QGroupBox("📋 剥头皮2.0交易记录（仅显示S开头的剥头皮单）")
        trade_box.setStyleSheet("QGroupBox { color:#a0a0c0; font-weight:bold; }")
        trade_layout = QVBoxLayout(trade_box)

        self.scalp_trade_table = QTableWidget(0, 7)
        self.scalp_trade_table.setHorizontalHeaderLabels([
            "时间", "币种", "操作", "价格", "数量", "盈亏", "原因"
        ])
        self.scalp_trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scalp_trade_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scalp_trade_table.setMaximumHeight(220)
        self.scalp_trade_table.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section {
                background: #161b22;
                color: #8b949e;
                border: none;
                border-bottom: 1px solid #30363d;
                padding: 6px;
            }
        """)
        trade_layout.addWidget(self.scalp_trade_table)

        bar = QHBoxLayout()
        btn_refresh_s = QPushButton("🔄 刷新")
        btn_refresh_s.setFixedWidth(70)
        btn_refresh_s.clicked.connect(self._refresh_scalping)
        bar.addWidget(btn_refresh_s)
        bar.addStretch()

        # 策略参数显示（2.0版本）
        cfg = self.engine.config
        params_lbl = QLabel(
            f"剥头皮2.0参数：止损{cfg.scalping_stop_loss_pct}% | "
            f"动态止盈{cfg.scalping_tp_narrow}%~{cfg.scalping_tp_wide}%(BB宽>{cfg.scalping_boll_wide_threshold}%切换) | "
            f"RSI<{cfg.scalping_rsi_oversold:.0f}(仅强信号) | "
            f"1H趋势过滤={'开' if cfg.scalping_trend_filter else '关'} | "
            f"最多加仓{cfg.scalping_max_add}次 | 冷却{cfg.scalping_cooldown//60}分钟"
        )
        params_lbl.setStyleSheet("color:#606080; font-size:11px;")
        bar.addWidget(params_lbl)
        trade_layout.addLayout(bar)

        layout.addWidget(trade_box)
        layout.addStretch()

        return scroll

    def _scalping_make_card(self, title: str, init_val: str, color: str, unit: str) -> dict:
        """创建统计小卡片"""
        card = QGroupBox()
        card.setStyleSheet(f"""
            QGroupBox {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                min-width: 120px;
            }}
            QGroupBox::title {{
                color: #606080;
                font-size: 11px;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)

        val_lbl = QLabel(init_val)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")
        layout.addWidget(val_lbl)

        unit_lbl = QLabel(unit)
        unit_lbl.setAlignment(Qt.AlignCenter)
        unit_lbl.setStyleSheet("color:#606080; font-size:11px;")
        layout.addWidget(unit_lbl)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color:#8b949e; font-size:11px; padding-top:4px;")
        layout.addWidget(title_lbl)

        return {'widget': card, 'value': val_lbl}

    def _build_scalp_coin_card(self, symbol: str) -> QWidget:
        """创建单个币种的剥头皮状态卡片"""
        colors = {
            'BTCUSDT': '#f7931a',
            'ETHUSDT': '#627eea',
            'SOLUSDT': '#14f195',
        }
        c = colors.get(symbol, '#ffd60a')

        card = QGroupBox(symbol.replace('USDT', ''))
        card.setStyleSheet(f"""
            QGroupBox {{
                background: #0d1117;
                border: 2px solid {c}55;
                border-radius: 10px;
                min-width: 200px;
            }}
            QGroupBox::title {{
                color: {c};
                font-size: 14px;
                font-weight: bold;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(6)

        # 状态行
        status_row = QHBoxLayout()
        lbl_status = QLabel("🔍 观望中")
        lbl_status.setObjectName(f"scalp_status_{symbol}")
        lbl_status.setStyleSheet(f"color:#8b949e; font-size:13px; font-weight:bold;")
        status_row.addWidget(lbl_status)
        status_row.addStretch()
        layout.addLayout(status_row)

        # 价格行
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel(f"<font color='#606080'>当前价</font>"))
        lbl_price = QLabel("--")
        lbl_price.setObjectName(f"scalp_price_{symbol}")
        lbl_price.setStyleSheet("color:#e0e0e0; font-size:13px; font-weight:bold;")
        price_row.addWidget(lbl_price)
        price_row.addStretch()
        layout.addLayout(price_row)

        # 持仓/均价行
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("<font color='#606080'>持仓均价</font>"))
        lbl_avg = QLabel("--")
        lbl_avg.setObjectName(f"scalp_avg_{symbol}")
        lbl_avg.setStyleSheet("color:#ffd60a; font-size:12px;")
        pos_row.addWidget(lbl_avg)
        pos_row.addStretch()
        layout.addLayout(pos_row)

        # 盈亏行
        pnl_row = QHBoxLayout()
        pnl_row.addWidget(QLabel("<font color='#606080'>持仓盈亏</font>"))
        lbl_pnl = QLabel("--")
        lbl_pnl.setObjectName(f"scalp_pnl_{symbol}")
        lbl_pnl.setStyleSheet("color:#8b949e; font-size:12px;")
        pnl_row.addWidget(lbl_pnl)
        pnl_row.addStretch()
        layout.addLayout(pnl_row)

        # 止盈止损行
        tp_row = QHBoxLayout()
        tp_row.addWidget(QLabel("<font color='#606080'>止盈</font>"))
        lbl_tp = QLabel("--")
        lbl_tp.setObjectName(f"scalp_tp_{symbol}")
        lbl_tp.setStyleSheet("color:#28a745; font-size:11px;")
        tp_row.addWidget(lbl_tp)
        tp_row.addSpacing(12)
        tp_row.addWidget(QLabel("<font color='#606080'>止损</font>"))
        lbl_sl = QLabel("--")
        lbl_sl.setObjectName(f"scalp_sl_{symbol}")
        lbl_sl.setStyleSheet("color:#dc3545; font-size:11px;")
        tp_row.addWidget(lbl_sl)
        tp_row.addStretch()
        layout.addLayout(tp_row)

        # 加仓/冷却行
        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("<font color='#606080'>加仓</font>"))
        lbl_add = QLabel("0/3")
        lbl_add.setObjectName(f"scalp_add_{symbol}")
        lbl_add.setStyleSheet("color:#ffd60a; font-size:11px;")
        meta_row.addWidget(lbl_add)
        meta_row.addSpacing(12)
        meta_row.addWidget(QLabel("<font color='#606080'>连损</font>"))
        lbl_loss = QLabel("0")
        lbl_loss.setObjectName(f"scalp_loss_{symbol}")
        lbl_loss.setStyleSheet("color:#dc3545; font-size:11px;")
        meta_row.addWidget(lbl_loss)
        meta_row.addStretch()
        layout.addLayout(meta_row)

        # 冷却行
        cool_row = QHBoxLayout()
        cool_row.addWidget(QLabel("<font color='#606080'>冷却</font>"))
        lbl_cool = QLabel("--")
        lbl_cool.setObjectName(f"scalp_cool_{symbol}")
        lbl_cool.setStyleSheet("color:#ffc107; font-size:11px;")
        cool_row.addWidget(lbl_cool)
        cool_row.addStretch()
        layout.addLayout(cool_row)

        return card

    def _refresh_scalping(self):
        """刷新剥头皮Tab数据（每秒更新）"""
        # 过滤剥头皮交易记录（S开头）
        scalp_trades = [r for r in self.engine.trade_records if r.id.startswith('S')]
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [r for r in scalp_trades if r.timestamp.startswith(today)]
        sells = [r for r in today_trades if r.action == 'SELL']

        # 统计
        total_today = len(today_trades)
        wins = sum(1 for r in sells if r.pnl > 0)
        win_rate = (wins / len(sells) * 100) if sells else 0
        daily_pnl = sum(r.pnl for r in today_trades if r.action == 'SELL')
        total_pnl = sum(r.pnl for r in scalp_trades if r.action == 'SELL')

        # 更新卡片
        self.scalp_cards['daily_trades'].setText(str(total_today))
        self.scalp_cards['win_rate'].setText(f"{win_rate:.0f}%" if sells else "0%")
        self.scalp_cards['win_rate'].setStyleSheet(
            f"color:{'#28a745' if win_rate >= 50 else '#dc3545'}; font-size:18px; font-weight:bold;"
        )
        self.scalp_cards['daily_pnl'].setText(f"{daily_pnl:+.2f}")
        self.scalp_cards['daily_pnl'].setStyleSheet(
            f"color:{'#28a745' if daily_pnl >= 0 else '#dc3545'}; font-size:18px; font-weight:bold;"
        )
        self.scalp_cards['total_pnl'].setText(f"{total_pnl:+.2f}")
        self.scalp_cards['total_pnl'].setStyleSheet(
            f"color:{'#28a745' if total_pnl >= 0 else '#dc3545'}; font-size:18px; font-weight:bold;"
        )

        # 更新每个币种的状态卡片
        for symbol in self.engine.config.symbols:
            self._update_scalp_coin_card(symbol)

        # 更新交易记录表
        self._refresh_scalp_trades(scalp_trades)

    def _update_scalp_coin_card(self, symbol: str):
        """更新单个币种的剥头皮卡片"""
        scalper = self.engine.scalping_strategies.get(symbol)
        status_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_status_{symbol}")
        price_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_price_{symbol}")
        avg_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_avg_{symbol}")
        pnl_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_pnl_{symbol}")
        tp_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_tp_{symbol}")
        sl_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_sl_{symbol}")
        add_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_add_{symbol}")
        loss_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_loss_{symbol}")
        cool_lbl: QLabel = self.scalp_coin_cards[symbol].findChild(QLabel, f"scalp_cool_{symbol}")

        if scalper is None:
            status_lbl.setText("🔍 初始化中...")
            price_lbl.setText("--")
            avg_lbl.setText("--")
            pnl_lbl.setText("--")
            tp_lbl.setText("--")
            sl_lbl.setText("--")
            add_lbl.setText("0/3")
            loss_lbl.setText("0")
            cool_lbl.setText("--")
            return

        status = scalper.get_status()

        # 获取当前价格
        current_price = 0.0
        try:
            klines = self.engine.client.get_klines(symbol, '5m', 1)
            if klines:
                current_price = float(klines[-1][4])
        except Exception:
            pass

        if status['in_position']:
            pnl_pct = (current_price - status['avg_cost']) / status['avg_cost'] * 100 if status['avg_cost'] > 0 else 0
            status_lbl.setText("📊 持仓中")
            status_lbl.setStyleSheet("color:#ffd60a; font-size:13px; font-weight:bold;")
            price_lbl.setText(f"{current_price:.4f}" if current_price else "--")
            avg_lbl.setText(f"{status['avg_cost']:.4f}")
            pnl_lbl.setText(f"{pnl_pct:+.2f}%")
            pnl_lbl.setStyleSheet(
                f"color:{'#28a745' if pnl_pct >= 0 else '#dc3545'}; font-size:12px;"
            )
            tp_lbl.setText(f"{status['take_profit_price']:.4f}")
            sl_lbl.setText(f"{status['stop_loss_price']:.4f}")
            add_lbl.setText(f"{status['add_count']}/{self.engine.config.scalping_max_add}")
            loss_lbl.setText(str(status['consecutive_losses']))
            cool_lbl.setText("--")
        elif status['in_cooldown']:
            status_lbl.setText("⏳ 冷却中")
            status_lbl.setStyleSheet("color:#ffc107; font-size:13px; font-weight:bold;")
            cool_sec = status['cooldown_remaining']
            cool_lbl.setText(f"{cool_sec // 60}m{cool_sec % 60}s")
            price_lbl.setText(f"{current_price:.4f}" if current_price else "--")
            avg_lbl.setText("--")
            pnl_lbl.setText("--")
            pnl_lbl.setStyleSheet("color:#8b949e; font-size:12px;")
            tp_lbl.setText("--")
            sl_lbl.setText("--")
            add_lbl.setText("0/3")
            loss_lbl.setText(str(status['consecutive_losses']))
        else:
            status_lbl.setText("🔍 观望中")
            status_lbl.setStyleSheet("color:#8b949e; font-size:13px; font-weight:bold;")
            price_lbl.setText(f"{current_price:.4f}" if current_price else "--")
            avg_lbl.setText("--")
            pnl_lbl.setText("--")
            pnl_lbl.setStyleSheet("color:#8b949e; font-size:12px;")
            tp_lbl.setText("--")
            sl_lbl.setText("--")
            add_lbl.setText("0/3")
            loss_lbl.setText(str(status['consecutive_losses']))
            cool_lbl.setText("--")

    def _refresh_scalp_trades(self, scalp_trades: list):
        """刷新剥头皮交易记录表"""
        self.scalp_trade_table.setRowCount(0)
        for record in reversed(scalp_trades[-50:]):
            self._add_scalp_trade_row(record)

    def _add_scalp_trade_row(self, record):
        row = self.scalp_trade_table.rowCount()
        self.scalp_trade_table.insertRow(row)
        cells = [
            record.timestamp[11:],  # 只显示时间部分
            record.symbol,
            record.action,
            f"{record.price:.4f}",
            f"{record.quantity:.6f}",
            f"{record.pnl:+.2f}" if record.action == "SELL" else "--",
            record.reason,
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 2:
                item.setForeground(QColor("#28a745") if record.action == "BUY" else QColor("#dc3545"))
            if col == 5 and record.action == "SELL":
                item.setForeground(QColor("#28a745") if record.pnl >= 0 else QColor("#dc3545"))
            self.scalp_trade_table.setItem(row, col, item)

    # ==================== AI交易 Tab ====================
    def _build_ai_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ---- 策略说明 ----
        intro = QLabel(
            "🤖 AI自适应多策略 | 4策略并行评分+动态权重 | "
            "每小时复盘调参 | 风控日亏上限$20 | 每分钟扫描15分钟K线"
        )
        intro.setStyleSheet("color:#00d4ff; font-size:12px; padding:4px;")
        layout.addWidget(intro)

        # ---- 状态卡片行 ----
        cards = QHBoxLayout()

        self.ai_cards = {}
        ai_target = 10.0
        if self.engine.ai_trader:
            ai_target = self.engine.ai_trader.config.account.daily_target

        # 日盈亏
        card_pnl = self._make_stat_card("日盈亏", "$0.00", "#28a745", "")
        self.ai_cards['daily_pnl'] = card_pnl['value']
        cards.addWidget(card_pnl['widget'])

        # 日目标
        card_target = self._make_stat_card(f"日目标", f"${ai_target}", "#ffd60a", "")
        self.ai_cards['daily_target'] = card_target['value']
        cards.addWidget(card_target['widget'])

        # 活跃持仓
        card_pos = self._make_stat_card("活跃持仓", "0", "#00d4ff", "个")
        self.ai_cards['active_positions'] = card_pos['value']
        cards.addWidget(card_pos['widget'])

        # 连损次数
        card_loss = self._make_stat_card("连损次数", "0", "#dc3545", "次")
        self.ai_cards['consecutive_losses'] = card_loss['value']
        cards.addWidget(card_loss['widget'])

        # 总交易笔数
        card_total = self._make_stat_card("AI总交易", "0", "#a0a0c0", "笔")
        self.ai_cards['total_trades'] = card_total['value']
        cards.addWidget(card_total['widget'])

        layout.addLayout(cards)

        # ---- 策略权重 ----
        weight_box = QGroupBox("📊 策略权重（每小时自动调整）")
        weight_layout = QHBoxLayout(weight_box)
        self.ai_weight_labels = {}

        strategy_names = ['Momentum', 'MeanReversion', 'Breakout', 'VolumeConfirm']
        strategy_colors = ['#00d4ff', '#28a745', '#ffd60a', '#dc3545']
        strategy_icons = ['📈', '🔄', '💥', '📊']

        for name, color, icon in zip(strategy_names, strategy_colors, strategy_icons):
            col = QVBoxLayout()
            lbl_icon = QLabel(icon)
            lbl_icon.setAlignment(Qt.AlignCenter)
            lbl_icon.setStyleSheet("font-size:20px;")
            lbl_name = QLabel(name)
            lbl_name.setAlignment(Qt.AlignCenter)
            lbl_name.setStyleSheet(f"color:{color}; font-weight:bold; font-size:12px;")
            lbl_weight = QLabel("权重: 1.0")
            lbl_weight.setAlignment(Qt.AlignCenter)
            lbl_weight.setStyleSheet("color:#e0e0e0; font-size:11px;")
            lbl_wr = QLabel("胜率: --")
            lbl_wr.setAlignment(Qt.AlignCenter)
            lbl_wr.setStyleSheet("color:#a0a0c0; font-size:10px;")

            col.addWidget(lbl_icon)
            col.addWidget(lbl_name)
            col.addWidget(lbl_weight)
            col.addWidget(lbl_wr)
            col.addStretch()

            weight_layout.addLayout(col)
            self.ai_weight_labels[name] = {'weight': lbl_weight, 'wr': lbl_wr}

        layout.addWidget(weight_box)

        # ---- 持仓卡片 ----
        pos_box = QGroupBox("💼 当前持仓")
        pos_layout = QVBoxLayout(pos_box)
        self.ai_position_widgets: Dict[str, QWidget] = {}
        self.ai_position_labels: Dict[str, Dict] = {}
        layout.addWidget(pos_box)

        # ---- AI交易记录 ----
        trade_box = QGroupBox("📋 AI交易记录")
        trade_layout = QVBoxLayout(trade_box)

        self.ai_trade_table = QTableWidget()
        self.ai_trade_table.setColumnCount(8)
        self.ai_trade_table.setHorizontalHeaderLabels(
            ["时间", "币种", "策略", "入场价", "出场价", "PnL", "胜率%", "出局原因"]
        )
        self.ai_trade_table.setMaximumHeight(250)
        self.ai_trade_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ai_trade_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.ai_trade_table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        trade_layout.addWidget(self.ai_trade_table)
        layout.addWidget(trade_box)

        # ---- 策略参数 ----
        param_box = QGroupBox("🔧 当前策略参数（可被AI自动调整）")
        param_layout = QVBoxLayout(param_box)

        param_text = QLabel(
            "Momentum: 止损0.8% 止盈动态(1.5~3x) | "
            "MeanReversion: RSI<35+布林带下轨 止损1% | "
            "Breakout: 突破+量能放大 止损1.2% | "
            "VolumeConfirm: 量价确认 止损0.8%"
        )
        param_text.setStyleSheet("color:#a0a0c0; font-size:11px; line-height:1.6;")
        param_layout.addWidget(param_text)
        layout.addWidget(param_box)

        layout.addStretch()

        # 持仓box引用（用于动态添加持仓卡片）
        self.ai_pos_box = pos_box
        self.ai_pos_layout = pos_layout

        # 刷新定时器
        self.ai_refresh_timer = QTimer()
        self.ai_refresh_timer.timeout.connect(self._refresh_ai_tab)
        self.ai_refresh_timer.start(3000)

        return scroll

    def _refresh_ai_tab(self):
        """刷新AI交易Tab"""
        if not self.engine.ai_trader:
            return

        try:
            status = self.engine.ai_trader.get_status()

            # 更新卡片
            pnl = status['daily_pnl']
            pnl_color = "#28a745" if pnl >= 0 else "#dc3545"
            pnl_text = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            self._update_stat_card_value(self.ai_cards['daily_pnl'], pnl_text, pnl_color)
            self._update_stat_card_value(self.ai_cards['active_positions'], str(status['active_positions']))
            self._update_stat_card_value(self.ai_cards['consecutive_losses'], str(status['consecutive_losses']))
            self._update_stat_card_value(self.ai_cards['total_trades'], str(status['total_trades']))

            # 更新策略权重
            for name, data in status['strategies'].items():
                if name in self.ai_weight_labels:
                    self.ai_weight_labels[name]['weight'].setText(f"权重: {data['weight']:.2f}")
                    wr_text = f"{data['win_rate']*100:.0f}%" if data['win_rate'] > 0 else "--"
                    self.ai_weight_labels[name]['wr'].setText(f"胜率: {wr_text}  ${data['total_pnl']:.2f}")

            # 更新持仓显示
            positions = self.engine.ai_trader.get_all_positions()
            self._refresh_ai_positions(positions)

            # 更新左侧面板AI持仓
            self._refresh_ai_panel_positions()

            # 更新交易记录
            self._refresh_ai_trades()

        except Exception:
            pass  # 忽略刷新错误

    def _refresh_ai_positions(self, positions: Dict):
        """刷新AI持仓显示"""
        # 清理不存在的持仓
        for sym in list(self.ai_position_widgets.keys()):
            if sym not in positions:
                w = self.ai_position_widgets.pop(sym, None)
                if w and w.parent():
                    w.setParent(None)

        # 添加/更新持仓
        for sym, pos in positions.items():
            if sym not in self.ai_position_widgets:
                w = self._create_ai_position_card(sym)
                self.ai_position_widgets[sym] = w
                self.ai_pos_layout.addWidget(w)

            # 更新数据
            self._update_ai_position_card(sym, pos)

    def _create_ai_position_card(self, symbol: str) -> QWidget:
        """创建单个AI持仓卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: #16213e;
                border: 1px solid #0f3460;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)

        lbl_sym = QLabel(symbol.replace('USDT', '/USDT'))
        lbl_sym.setStyleSheet("color:#00d4ff; font-weight:bold; font-size:14px;")
        layout.addWidget(lbl_sym)

        lbl_price = QLabel("入场: --")
        lbl_price.setStyleSheet("color:#e0e0e0; font-size:12px;")
        layout.addWidget(lbl_price)

        lbl_cur = QLabel("现价: --")
        lbl_cur.setStyleSheet("color:#e0e0e0; font-size:12px;")
        layout.addWidget(lbl_cur)

        lbl_pnl = QLabel("PnL: --")
        lbl_pnl.setStyleSheet("color:#e0e0e0; font-size:12px;")
        layout.addWidget(lbl_pnl)

        lbl_strat = QLabel("策略: --")
        lbl_strat.setStyleSheet("color:#a0a0c0; font-size:11px;")
        layout.addWidget(lbl_strat)

        layout.addStretch()

        self.ai_position_labels[symbol] = {
            'price': lbl_price, 'cur': lbl_cur,
            'pnl': lbl_pnl, 'strat': lbl_strat
        }
        return card

    def _update_ai_position_card(self, symbol: str, pos: Dict):
        """更新AI持仓卡片数据"""
        if symbol not in self.ai_position_labels:
            return
        lbls = self.ai_position_labels[symbol]
        lbls['price'].setText(f"入场: {pos['entry_price']:.4f}")
        lbls['strat'].setText(f"策略: {pos['signal'].strategy_name}")

    def _refresh_ai_panel_positions(self):
        """刷新左侧面板AI实时持仓区块"""
        if not self.engine.ai_trader:
            return

        positions = self.engine.ai_trader.get_all_positions()
        current_symbols = set(positions.keys())

        # 清理已平仓的卡片
        for sym in list(self.ai_panel_labels.keys()):
            if sym not in current_symbols:
                w = self.ai_panel_labels[sym].get('_widget')
                if w:
                    w.setParent(None)
                del self.ai_panel_labels[sym]

        # 清除旧布局里的所有widget（重新构建）
        while self.ai_panel_layout.count():
            child = self.ai_panel_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)

        if not positions:
            empty = QLabel("  暂无AI持仓")
            empty.setStyleSheet("color:#555; font-size:12px; padding:4px;")
            self.ai_panel_layout.addWidget(empty)
            return

        # 构建持仓卡片
        for sym, pos in positions.items():
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: #1a1a2e;
                    border: 1px solid #2d2d44;
                    border-radius: 6px;
                    padding: 6px 8px;
                }
            """)
            row = QHBoxLayout(card)
            row.setContentsMargins(8, 4, 8, 4)

            # 币种名
            sym_lbl = QLabel(sym.replace('USDT', ''))
            sym_lbl.setStyleSheet("color:#00d4ff; font-weight:bold; font-size:13px; min-width:40px;")
            row.addWidget(sym_lbl)

            # 入场价
            entry_lbl = QLabel(f"入:{pos['entry_price']:.2f}")
            entry_lbl.setStyleSheet("color:#e0e0e0; font-size:11px;")
            row.addWidget(entry_lbl)

            # 策略名
            strat_lbl = QLabel(pos['signal'].strategy_name[:8])
            strat_lbl.setStyleSheet("color:#a0a0c0; font-size:10px;")
            row.addWidget(strat_lbl)

            row.addStretch()

            # 盈亏%（等下次刷新时更新，这里先用0）
            self.ai_panel_labels[sym] = {'card': card}

            self.ai_panel_layout.addWidget(card)

        # 更新各卡片的实时盈亏
        for sym, pos in positions.items():
            if sym not in self.ai_panel_labels:
                continue
            card = self.ai_panel_labels[sym].get('card')
            if not card:
                continue

            # 尝试从engine获取当前价
            try:
                cur_price = self.engine.client.get_ticker_price(sym)
                if cur_price:
                    pnl_pct = (cur_price - pos['entry_price']) / pos['entry_price'] * 100
                    pnl_color = "#28a745" if pnl_pct >= 0 else "#dc3545"
                    pnl_text = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
                else:
                    pnl_text = "--"
                    pnl_color = "#e0e0e0"
            except Exception:
                pnl_text = "--"
                pnl_color = "#e0e0e0"

            pnl_lbl = QLabel(pnl_text)
            pnl_lbl.setStyleSheet(f"color:{pnl_color}; font-weight:bold; font-size:12px; min-width:55px;")
            pnl_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 找到card里的最后一个位置插入（替换掉stretch后的内容）
            layout = card.layout()
            # 移除旧pnl标签（如果有）
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget() and hasattr(item.widget(), 'objectName') and item.widget().objectName() == 'pnl_lbl':
                    item.widget().setParent(None)
            layout.addWidget(pnl_lbl)

    def _refresh_ai_trades(self):
        """刷新AI交易记录表"""
        if not self.engine.ai_trader:
            return
        records = self.engine.ai_trader.get_recent_trades(20)
        self.ai_trade_table.setRowCount(0)
        for rec in records:
            row = self.ai_trade_table.rowCount()
            self.ai_trade_table.insertRow(row)
            vals = [
                rec.get('entry_time', '')[:16],
                rec.get('symbol', ''),
                rec.get('strategy', ''),
                f"{rec.get('entry_price', 0):.4f}",
                f"{rec.get('exit_price', 0):.4f}",
                f"${rec.get('pnl', 0):.2f}({rec.get('pnl_pct', 0):.2f}%)",
                f"{rec.get('confidence', 0)*100:.0f}%",
                '止盈' if rec.get('tp_reached') else '止损' if rec.get('sl_reached') else '手动',
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 5:
                    pnl = rec.get('pnl', 0)
                    item.setForeground(QColor("#28a745") if pnl >= 0 else QColor("#dc3545"))
                self.ai_trade_table.setItem(row, col, item)

    def _make_stat_card(self, title: str, value: str, color: str, unit: str) -> Dict:
        """创建统计卡片"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: #16213e;
                border: 1px solid #2d2d4e;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color:#a0a0c0; font-size:11px;")

        lbl_value = QLabel(value)
        lbl_value.setAlignment(Qt.AlignCenter)
        lbl_value.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

        lbl_unit = QLabel(unit)
        lbl_unit.setAlignment(Qt.AlignCenter)
        lbl_unit.setStyleSheet("color:#a0a0c0; font-size:10px;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addWidget(lbl_unit)

        return {'widget': widget, 'value': lbl_value}

    def _update_stat_card_value(self, label: QLabel, text: str, color: str = ""):
        """更新统计卡片值"""
        label.setText(text)
        if color:
            label.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    # ==================== 监控日志 Tab ====================
    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # 工具栏
        bar = QHBoxLayout()
        self.lbl_last_scan = QLabel("上次扫描: --")
        self.lbl_last_scan.setStyleSheet("color:#a0a0c0;")
        bar.addWidget(self.lbl_last_scan)
        bar.addStretch()

        # 打开日志文件按钮
        btn_open_log = QPushButton("📂 打开日志文件")
        btn_open_log.setFixedWidth(110)
        btn_open_log.setStyleSheet("""
            QPushButton {
                background: #0c4a6e;
                color: #0ea5e9;
                border: 1px solid #0ea5e9;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0ea5e9; color: white; }
        """)
        btn_open_log.clicked.connect(self._open_log_file)
        bar.addWidget(btn_open_log)

        btn_clear = QPushButton("清空日志")
        btn_clear.setFixedWidth(80)
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        bar.addWidget(btn_clear)
        layout.addLayout(bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(400)
        layout.addWidget(self.log_view)
        return w

    # ==================== 成交记录 Tab ====================
    def _build_trade_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("最近成交记录"))
        bar.addStretch()
        btn_refresh = QPushButton("刷新")
        btn_refresh.setFixedWidth(60)
        btn_refresh.clicked.connect(self._refresh_trades)
        bar.addWidget(btn_refresh)
        layout.addLayout(bar)

        self.trade_table = QTableWidget(0, 9)
        self.trade_table.setHorizontalHeaderLabels(
            ["时间", "币种", "操作", "类型", "价格", "数量", "金额(U)", "盈亏(U)", "评分"]
        )
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trade_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trade_table.setAlternatingRowColors(True)
        self.trade_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1e2a4a; }"
        )
        layout.addWidget(self.trade_table)
        return w

    # ==================== 营收统计 Tab ====================
    def _build_profit_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # 统计卡片行
        cards_layout = QHBoxLayout()
        self.stat_cards = {}
        stats = [
            ("累计盈亏", "total_pnl", "#28a745"),
            ("今日盈亏", "daily_pnl", "#17a2b8"),
            ("总交易次数", "total_trades", "#6f42c1"),
            ("当前持仓", "open_positions", "#fd7e14"),
        ]
        for title, key, color in stats:
            card = self._make_stat_card_simple(title, "--", color)
            self.stat_cards[key] = card[1]
            cards_layout.addWidget(card[0])
        layout.addLayout(cards_layout)

        # 目标进度
        target_box = QGroupBox("营收目标")
        tl = QVBoxLayout(target_box)

        # 总目标
        tl.addWidget(QLabel("累计目标进度"))
        self.progress_total = QProgressBar()
        self.progress_total.setRange(0, 100)
        self.lbl_target_total = QLabel("0 / 1000 USDT")
        self.lbl_target_total.setAlignment(Qt.AlignRight)
        tl.addWidget(self.progress_total)
        tl.addWidget(self.lbl_target_total)

        # 日目标
        tl.addWidget(QLabel("今日目标进度"))
        self.progress_daily = QProgressBar()
        self.progress_daily.setRange(0, 100)
        self.progress_daily.setStyleSheet(
            "QProgressBar::chunk { background: #17a2b8; border-radius: 5px; }"
        )
        self.lbl_target_daily = QLabel("0 / 100 USDT")
        self.lbl_target_daily.setAlignment(Qt.AlignRight)
        tl.addWidget(self.progress_daily)
        tl.addWidget(self.lbl_target_daily)
        layout.addWidget(target_box)

        # 盈亏曲线图
        chart_box = QGroupBox("盈亏曲线")
        cl = QVBoxLayout(chart_box)
        self.pnl_chart = pg.PlotWidget()
        self.pnl_chart.setBackground('#0d0d1a')
        self.pnl_chart.showGrid(x=True, y=True, alpha=0.2)
        self.pnl_chart.setLabel('left', '盈亏 (USDT)', color='#a0a0c0')
        self.pnl_chart.setLabel('bottom', '交易次数', color='#a0a0c0')
        self._pnl_curve = self.pnl_chart.plot(pen=pg.mkPen('#00d4ff', width=2))
        cl.addWidget(self.pnl_chart)
        layout.addWidget(chart_box)
        return w

    def _make_stat_card_simple(self, title: str, value: str, color: str):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: #16213e;
                border: 1px solid {color};
                border-radius: 8px;
            }}
        """)
        l = QVBoxLayout(frame)
        l.setContentsMargins(12, 10, 12, 10)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color:#a0a0c0; font-size:12px;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color:{color}; font-size:22px; font-weight:bold;")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return frame, lbl_v

    # ==================== 参数调节 Tab ====================
    def _build_params_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 交易模式
        mode_box = QGroupBox("交易模式")
        ml = QHBoxLayout(mode_box)
        self.chk_paper = QCheckBox("模拟交易（不真实下单）")
        self.chk_paper.setChecked(self.engine.config.paper_trading)
        self.chk_futures = QCheckBox("开启合约交易")
        self.chk_futures.setChecked(self.engine.config.futures_enabled)
        self.chk_futures.setStyleSheet("color:#ffc107;")
        ml.addWidget(self.chk_paper)
        ml.addSpacing(20)
        ml.addWidget(self.chk_futures)
        ml.addStretch()
        layout.addWidget(mode_box)

        # API配置
        api_box = QGroupBox("API 配置")
        al = QGridLayout(api_box)
        al.setSpacing(8)
        al.addWidget(QLabel("API Key:"), 0, 0)
        self.inp_api_key = QLineEdit()
        self.inp_api_key.setEchoMode(QLineEdit.Password)
        self.inp_api_key.setPlaceholderText("填入币安 API Key")
        al.addWidget(self.inp_api_key, 0, 1)
        al.addWidget(QLabel("API Secret:"), 1, 0)
        self.inp_api_secret = QLineEdit()
        self.inp_api_secret.setEchoMode(QLineEdit.Password)
        self.inp_api_secret.setPlaceholderText("填入币安 API Secret")
        al.addWidget(self.inp_api_secret, 1, 1)
        
        # 从 config.env 加载已保存的API配置
        self._load_api_from_env()
        btn_save_api = QPushButton("保存并测试连接")
        btn_save_api.clicked.connect(self._save_api)
        al.addWidget(btn_save_api, 2, 1)
        layout.addWidget(api_box)

        # 扫描参数
        scan_box = QGroupBox("扫描参数")
        sl = QGridLayout(scan_box)
        sl.setSpacing(8)
        sl.addWidget(QLabel("扫描间隔(秒):"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 3600)
        self.spin_interval.setValue(self.engine.config.scan_interval)
        sl.addWidget(self.spin_interval, 0, 1)
        sl.addWidget(QLabel("K线周期:"), 0, 2)
        self.combo_kline = QComboBox()
        self.combo_kline.addItems(['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'])
        self.combo_kline.setCurrentText(self.engine.config.kline_interval)
        sl.addWidget(self.combo_kline, 0, 3)
        layout.addWidget(scan_box)

        # 现货交易参数
        spot_box = QGroupBox("现货交易参数")
        spot_box.setStyleSheet("QGroupBox { color: #28a745; }")
        spot_layout = QGridLayout(spot_box)
        spot_layout.setSpacing(8)
        
        spot_layout.addWidget(QLabel("买入阈值(分):"), 0, 0)
        self.spin_buy_threshold = QDoubleSpinBox()
        self.spin_buy_threshold.setRange(1.0, 9.0)
        self.spin_buy_threshold.setSingleStep(0.5)
        self.spin_buy_threshold.setDecimals(1)
        self.spin_buy_threshold.setValue(self.engine.config.buy_threshold)
        spot_layout.addWidget(self.spin_buy_threshold, 0, 1)
        
        spot_layout.addWidget(QLabel("卖出阈值(分):"), 0, 2)
        self.spin_sell_threshold = QDoubleSpinBox()
        self.spin_sell_threshold.setRange(0.0, 5.0)
        self.spin_sell_threshold.setSingleStep(0.5)
        self.spin_sell_threshold.setDecimals(1)
        self.spin_sell_threshold.setValue(self.engine.config.sell_threshold)
        spot_layout.addWidget(self.spin_sell_threshold, 0, 3)
        
        spot_layout.addWidget(QLabel("买入仓位(%):"), 1, 0)
        self.spin_buy_qty_pct = QDoubleSpinBox()
        self.spin_buy_qty_pct.setRange(1.0, 100.0)
        self.spin_buy_qty_pct.setSingleStep(5.0)
        self.spin_buy_qty_pct.setDecimals(0)
        self.spin_buy_qty_pct.setValue(self.engine.config.buy_quantity_pct * 100)
        spot_layout.addWidget(self.spin_buy_qty_pct, 1, 1)
        
        spot_layout.addWidget(QLabel("最大仓位(%):"), 1, 2)
        self.spin_max_position = QDoubleSpinBox()
        self.spin_max_position.setRange(10.0, 100.0)
        self.spin_max_position.setSingleStep(10.0)
        self.spin_max_position.setDecimals(0)
        self.spin_max_position.setValue(self.engine.config.max_position_pct * 100)
        spot_layout.addWidget(self.spin_max_position, 1, 3)
        
        layout.addWidget(spot_box)

        # ===== 币种策略配置 =====
        self.symbol_configs = {}
        self.strategy_widgets = {}
        
        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
            config = get_default_symbol_config(symbol)
            self.symbol_configs[symbol] = config
            
            # 币种主框
            sym_box = QGroupBox(f"📊 {symbol} 策略配置")
            sym_box.setStyleSheet(f"""
                QGroupBox {{ 
                    background: #0d1117; 
                    border: 2px solid {'#f7931a' if 'BTC' in symbol else '#627eea' if 'ETH' in symbol else '#14f195'}; 
                    border-radius: 8px; 
                    margin-top: 10px;
                    font-weight: bold;
                }}
                QGroupBox::title {{ 
                    subcontrol-origin: margin; 
                    left: 10px; 
                    padding: 0 5px;
                    color: {'#f7931a' if 'BTC' in symbol else '#627eea' if 'ETH' in symbol else '#14f195'};
                }}
            """)
            sym_layout = QVBoxLayout(sym_box)
            
            # 启用复选框
            chk_enabled = QCheckBox(f"启用 {symbol}")
            chk_enabled.setChecked(config.enabled)
            chk_enabled.setStyleSheet("font-size: 13px; font-weight: bold;")
            sym_layout.addWidget(chk_enabled)
            self.strategy_widgets[f"{symbol}_enabled"] = chk_enabled
            
            # 为每个策略创建配置面板
            for idx, strategy in enumerate(config.strategies):
                strat_box = QGroupBox(f"策略{idx+1}: {strategy.name}")
                strat_box.setStyleSheet("""
                    QGroupBox { 
                        background: #161b22; 
                        border: 1px solid #30363d; 
                        border-radius: 6px; 
                        margin-top: 8px;
                    }
                    QGroupBox::title { 
                        subcontrol-origin: margin; 
                        left: 8px; 
                        padding: 0 4px;
                        color: #8b949e;
                        font-size: 11px;
                    }
                """)
                strat_layout = QGridLayout(strat_box)
                strat_layout.setSpacing(6)
                
                # 启用复选框
                chk_strat = QCheckBox("启用此策略")
                chk_strat.setChecked(strategy.enabled)
                strat_layout.addWidget(chk_strat, 0, 0, 1, 4)
                self.strategy_widgets[f"{symbol}_{idx}_enabled"] = chk_strat
                
                # 策略描述
                lbl_desc = QLabel(f"📈 {strategy.description}")
                lbl_desc.setStyleSheet("color: #58a6ff; font-size: 10px;")
                lbl_desc.setWordWrap(True)
                strat_layout.addWidget(lbl_desc, 1, 0, 1, 4)
                
                # 买入条件参数
                row = 2
                params = [
                    ("总分≥", "min_total_score", strategy.min_total_score, 0.0, 9.0),
                    ("MACD≥", "min_macd", strategy.min_macd, 0.0, 3.0),
                    ("BOLL≥", "min_boll", strategy.min_boll, 0.0, 3.0),
                    ("RSI≥", "min_rsi", strategy.min_rsi, 0.0, 3.0),
                    ("KDJ≥", "min_kdj", strategy.min_kdj, 0.0, 3.0),
                    ("VOL≥", "min_volume", strategy.min_volume, 0.0, 3.0),
                    ("TREND≥", "min_trend", strategy.min_trend, 0.0, 3.0),
                ]
                
                for i, (label, attr, val, min_v, max_v) in enumerate(params):
                    r = row + (i // 4)
                    c = (i % 4) * 2
                    strat_layout.addWidget(QLabel(label), r, c)
                    spin = QDoubleSpinBox()
                    spin.setRange(min_v, max_v)
                    spin.setSingleStep(0.1)
                    spin.setDecimals(1)
                    spin.setValue(val)
                    spin.setFixedWidth(60)
                    strat_layout.addWidget(spin, r, c + 1)
                    self.strategy_widgets[f"{symbol}_{idx}_{attr}"] = spin
                
                # 风控参数
                row = 4
                risk_params = [
                    ("卖出阈值≤", "sell_threshold", strategy.sell_threshold, 0.0, 5.0),
                    ("仓位(%)", "position_pct", strategy.position_pct * 100, 1, 100),
                    ("止损(%)", "stop_loss", strategy.stop_loss_pct, 0.5, 50),
                    ("止盈(%)", "take_profit", strategy.take_profit_pct, 1, 200),
                ]
                
                for i, (label, attr, val, min_v, max_v) in enumerate(risk_params):
                    strat_layout.addWidget(QLabel(label), row, i * 2)
                    spin = QDoubleSpinBox()
                    spin.setRange(min_v, max_v)
                    spin.setSingleStep(0.5)
                    spin.setDecimals(1 if attr != "position_pct" else 0)
                    spin.setValue(val)
                    spin.setFixedWidth(60)
                    strat_layout.addWidget(spin, row, i * 2 + 1)
                    self.strategy_widgets[f"{symbol}_{idx}_{attr}"] = spin
                
                sym_layout.addWidget(strat_box)
            
            layout.addWidget(sym_box)

        # 合约参数
        fut_box = QGroupBox("合约参数（谨慎使用）")
        fut_box.setStyleSheet("QGroupBox { color: #ffc107; }")
        fl = QGridLayout(fut_box)
        fl.setSpacing(8)
        fl.addWidget(QLabel("合约买入阈值:"), 0, 0)
        self.spin_fut_th = QDoubleSpinBox()
        self.spin_fut_th.setRange(1.0, 9.0)
        self.spin_fut_th.setSingleStep(0.5)
        self.spin_fut_th.setValue(self.engine.config.futures_buy_threshold)
        fl.addWidget(self.spin_fut_th, 0, 1)
        fl.addWidget(QLabel("合约杠杆倍数:"), 0, 2)
        self.spin_leverage = QSpinBox()
        self.spin_leverage.setRange(1, 20)
        self.spin_leverage.setValue(self.engine.config.futures_leverage)
        fl.addWidget(self.spin_leverage, 0, 3)
        layout.addWidget(fut_box)

        # ===== 网格策略配置 =====
        grid_box = QGroupBox("📊 网格抄底策略配置")
        grid_box.setStyleSheet("""
            QGroupBox { 
                background: #0d1117; 
                border: 2px solid #00d4ff; 
                border-radius: 8px; 
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
                color: #00d4ff;
            }
        """)
        grid_layout = QGridLayout(grid_box)
        grid_layout.setSpacing(8)
        
        # 启用网格策略
        self.chk_grid_enabled = QCheckBox("启用网格抄底策略")
        self.chk_grid_enabled.setChecked(self.engine.config.grid_strategy_enabled)
        self.chk_grid_enabled.setStyleSheet("font-size: 13px; font-weight: bold;")
        grid_layout.addWidget(self.chk_grid_enabled, 0, 0, 1, 4)
        
        # 网格参数
        grid_params = [
            ("首次触发跌幅(%):", "grid_drop_trigger", 10.0, 1.0, 50.0),
            ("每档跌幅间隔(%):", "grid_drop_step", 10.0, 1.0, 30.0),
            ("首次抄底仓位(%):", "grid_initial_pct", 50.0, 10.0, 100.0),
            ("每档加仓(%):", "grid_add_pct", 20.0, 5.0, 50.0),
            ("最大总仓位(%):", "grid_max_pct", 90.0, 50.0, 100.0),
            ("网格止盈(%):", "grid_take_profit", 15.0, 5.0, 50.0),
            ("网格止损(%):", "grid_stop_loss", 60.0, 10.0, 80.0),
        ]
        
        for i, (label, attr, val, min_v, max_v) in enumerate(grid_params):
            row = 1 + i // 4
            col = (i % 4) * 2
            grid_layout.addWidget(QLabel(label), row, col)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setSingleStep(1.0)
            spin.setDecimals(0)
            spin.setValue(val)
            spin.setFixedWidth(70)
            grid_layout.addWidget(spin, row, col + 1)
            setattr(self, f"spin_{attr}", spin)
        
        layout.addWidget(grid_box)
        
        # ===== 布林带策略配置 =====
        boll_box = QGroupBox("📈 布林带策略配置")
        boll_box.setStyleSheet("""
            QGroupBox { 
                background: #0d1117; 
                border: 2px solid #ff6b6b; 
                border-radius: 8px; 
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
                color: #ff6b6b;
            }
        """)
        boll_layout = QGridLayout(boll_box)
        boll_layout.setSpacing(8)
        
        # 启用布林带策略
        self.chk_boll_enabled = QCheckBox("启用布林带策略")
        self.chk_boll_enabled.setChecked(self.engine.config.boll_strategy_enabled)
        self.chk_boll_enabled.setStyleSheet("font-size: 13px; font-weight: bold;")
        boll_layout.addWidget(self.chk_boll_enabled, 0, 0, 1, 4)
        
        # 允许做空
        self.chk_boll_short = QCheckBox("允许反手做空")
        self.chk_boll_short.setChecked(True)
        boll_layout.addWidget(self.chk_boll_short, 0, 4, 1, 2)
        
        # 布林带参数
        boll_params = [
            ("布林带周期:", "boll_period", 20, 10, 50),
            ("标准差倍数:", "boll_std", 2.0, 1.0, 4.0),
            ("交易仓位(%):", "boll_position_pct", 30.0, 10.0, 100.0),
            ("止盈(%):", "boll_take_profit", 8.0, 1.0, 50.0),
            ("止损(%):", "boll_stop_loss", 5.0, 1.0, 30.0),
            ("极端行情阈值(%):", "boll_extreme", 10.0, 5.0, 30.0),
        ]
        
        for i, (label, attr, val, min_v, max_v) in enumerate(boll_params):
            row = 1 + i // 3
            col = (i % 3) * 2
            boll_layout.addWidget(QLabel(label), row, col)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            if attr == "boll_period":
                spin.setSingleStep(1)
                spin.setDecimals(0)
            else:
                spin.setSingleStep(0.5)
                spin.setDecimals(1)
            spin.setValue(val)
            spin.setFixedWidth(70)
            boll_layout.addWidget(spin, row, col + 1)
            setattr(self, f"spin_{attr}", spin)
        
        layout.addWidget(boll_box)

        # 目标营收
        tgt_box = QGroupBox("营收目标")
        tl = QGridLayout(tgt_box)
        tl.setSpacing(8)
        tl.addWidget(QLabel("总目标盈利(USDT):"), 0, 0)
        self.spin_target = QDoubleSpinBox()
        self.spin_target.setRange(0, 1000000)
        self.spin_target.setDecimals(0)
        self.spin_target.setValue(self.engine.config.target_profit)
        tl.addWidget(self.spin_target, 0, 1)
        tl.addWidget(QLabel("每日目标盈利(USDT):"), 0, 2)
        self.spin_daily_target = QDoubleSpinBox()
        self.spin_daily_target.setRange(0, 100000)
        self.spin_daily_target.setDecimals(0)
        self.spin_daily_target.setValue(self.engine.config.daily_target)
        tl.addWidget(self.spin_daily_target, 0, 3)
        layout.addWidget(tgt_box)

        # 保存按钮
        btn_save = QPushButton("✅ 保存所有参数")
        btn_save.setFixedHeight(40)
        btn_save.setStyleSheet(
            "QPushButton { background: #155724; border: 1px solid #28a745; "
            "color: #28a745; font-size: 14px; font-weight: bold; border-radius: 6px; }"
            "QPushButton:hover { background: #28a745; color: white; }"
        )
        btn_save.clicked.connect(self._save_params)
        layout.addWidget(btn_save)
        layout.addStretch()
        return scroll

    # ==================== 规则管理 Tab ====================
    def _build_rules_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel("📜 量化规则管理 — 控制各规则的启用状态")
        lbl.setStyleSheet("color:#a0a0c0; padding: 4px;")
        layout.addWidget(lbl)

        self.rules_table = QTableWidget(0, 4)
        self.rules_table.setHorizontalHeaderLabels(["规则名称", "描述", "类型", "状态"])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.rules_table)

        bar = QHBoxLayout()
        btn_refresh_rules = QPushButton("刷新规则列表")
        btn_refresh_rules.clicked.connect(self._refresh_rules)
        btn_toggle = QPushButton("切换选中规则 启用/禁用")
        btn_toggle.clicked.connect(self._toggle_rule)
        bar.addWidget(btn_refresh_rules)
        bar.addWidget(btn_toggle)
        bar.addStretch()
        layout.addLayout(bar)

        # 自定义规则提示
        hint_box = QGroupBox("💡 添加自定义规则（开发者模式）")
        hl = QVBoxLayout(hint_box)
        hint = QLabel(
            "在 src/core/rules.py 中继承 BaseRule 类，实现 evaluate() 方法，\n"
            "然后在 RuleEngine._load_default_rules() 中添加实例即可生效。\n\n"
            "示例规则已内置：评分买入、评分卖出、止损、止盈、合约做多"
        )
        hint.setStyleSheet("color:#606080; font-size:12px; line-height:1.8;")
        hl.addWidget(hint)
        layout.addWidget(hint_box)

        self._refresh_rules()
        return w

    # ==================== 操作方法 ====================
    def _start_engine(self):
        self.engine.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("🟢 运行中")
        self.lbl_status.setStyleSheet("color:#28a745; font-size:13px; font-weight:bold;")

    def _stop_engine(self):
        self.engine.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("⏸ 已停止")
        self.lbl_status.setStyleSheet("color:#a0a0c0; font-size:13px; font-weight:bold;")

    def _manual_scan(self):
        self._append_log("[手动] 手动触发扫描...", 'INFO')
        self.engine.manual_scan()

    def _open_log_file(self):
        """用系统默认文本编辑器打开日志文件"""
        import subprocess
        log_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'logs', 'niuquant.log'
        )
        if os.path.exists(log_path):
            subprocess.Popen(['notepad.exe', log_path])
            self._append_log(f"📂 已用记事本打开日志文件: {log_path}", 'INFO')
        else:
            QMessageBox.warning(self, "文件不存在", f"日志文件不存在:\n{log_path}")

    def _load_api_from_env(self):
        """从 config.env 加载API配置到界面"""
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config.env'
        )
        if os.path.exists(env_path):
            load_dotenv(env_path)
            api_key = os.getenv('BINANCE_API_KEY', '')
            api_secret = os.getenv('BINANCE_API_SECRET', '')
            # 排除占位符
            if api_key and api_key != 'your_api_key_here':
                self.inp_api_key.setText(api_key)
            if api_secret and api_secret != 'your_api_secret_here':
                self.inp_api_secret.setText(api_secret)

    def _save_api(self):
        api_key = self.inp_api_key.text().strip()
        api_secret = self.inp_api_secret.text().strip()
        if api_key and api_secret:
            # 写入config.env
            env_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'config.env'
            )
            content = (
                f"BINANCE_API_KEY={api_key}\n"
                f"BINANCE_API_SECRET={api_secret}\n"
                f"USE_TESTNET={'true' if self.engine.config.paper_trading else 'false'}\n"
            )
            with open(env_path, 'w') as f:
                f.write(content)
            self.engine.client.api_key = api_key
            self.engine.client.api_secret = api_secret
            ok = self.engine.client.connect()
            if ok:
                QMessageBox.information(self, "成功", "API连接测试成功！")
                self._append_log("✅ API配置已保存，连接成功", 'INFO')
            else:
                QMessageBox.warning(self, "失败", "API连接失败，请检查密钥是否正确")
        else:
            QMessageBox.warning(self, "提示", "请填入API Key和Secret")

    def _save_params(self):
        # 收集策略配置
        new_config = {
            'paper_trading': self.chk_paper.isChecked(),
            'futures_enabled': self.chk_futures.isChecked(),
            'scan_interval': self.spin_interval.value(),
            'kline_interval': self.combo_kline.currentText(),
            # 现货参数
            'buy_threshold': self.spin_buy_threshold.value(),
            'sell_threshold': self.spin_sell_threshold.value(),
            'buy_quantity_pct': self.spin_buy_qty_pct.value() / 100,
            'max_position_pct': self.spin_max_position.value() / 100,
            # 合约参数
            'futures_buy_threshold': self.spin_fut_th.value(),
            'futures_leverage': self.spin_leverage.value(),
            # 目标
            'target_profit': self.spin_target.value(),
            'daily_target': self.spin_daily_target.value(),
            # 策略开关
            'grid_strategy_enabled': self.chk_grid_enabled.isChecked(),
            'boll_strategy_enabled': self.chk_boll_enabled.isChecked(),
        }
        
        # 更新引擎配置
        self.engine.update_config(new_config)
        
        # 更新网格策略配置
        for symbol in self.engine.config.symbols:
            if symbol in self.engine.grid_strategies:
                grid = self.engine.grid_strategies[symbol]
                grid.config.drop_pct_trigger = self.spin_grid_drop_trigger.value()
                grid.config.drop_pct_step = self.spin_grid_drop_step.value()
                grid.config.initial_position_pct = self.spin_grid_initial_pct.value() / 100
                grid.config.add_position_pct = self.spin_grid_add_pct.value() / 100
                grid.config.max_position_pct = self.spin_grid_max_pct.value() / 100
                grid.config.take_profit_pct = self.spin_grid_take_profit.value()
                grid.config.stop_loss_pct = self.spin_grid_stop_loss.value()
        
        # 更新布林带策略配置
        for symbol in self.engine.config.symbols:
            if symbol in self.engine.boll_strategies:
                boll = self.engine.boll_strategies[symbol]
                boll.config.period = int(self.spin_boll_period.value())
                boll.config.std_dev = self.spin_boll_std.value()
                boll.config.position_pct = self.spin_boll_position_pct.value() / 100
                boll.config.take_profit_pct = self.spin_boll_take_profit.value()
                boll.config.stop_loss_pct = self.spin_boll_stop_loss.value()
                boll.config.extreme_change_pct = self.spin_boll_extreme.value()
                boll.config.short_enabled = self.chk_boll_short.isChecked()

        # 更新模式标签
        if new_config['paper_trading']:
            self.lbl_mode.setText("📋 模拟模式")
            self.lbl_mode.setStyleSheet(
                "color:#ffc107; background:#332200; padding:4px 10px; "
                "border-radius:4px; font-weight:bold; margin-left:8px;"
            )
        else:
            self.lbl_mode.setText("🔴 实盘模式")
            self.lbl_mode.setStyleSheet(
                "color:#dc3545; background:#330000; padding:4px 10px; "
                "border-radius:4px; font-weight:bold; margin-left:8px;"
            )

        QMessageBox.information(self, "已保存", "参数已保存并生效！")
        self._append_log("⚙️ 参数已更新", 'INFO')

    # ==================== 数据刷新 ====================
    def _append_log(self, msg: str, level: str = 'INFO'):
        color_map = {
            'ERROR': '#ff6b6b',
            'WARNING': '#ffc107',
            'INFO': '#00ff88',
        }
        color = color_map.get(level, '#00ff88')
        html = f'<span style="color:{color};">{msg}</span>'
        self.log_view.append(html)
        # 自动滚到底部
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_view.setTextCursor(cursor)

    def _on_score_update(self, score: SignalScore):
        if score.symbol in self.symbol_cards:
            self.symbol_cards[score.symbol].update_score(score)
        if hasattr(self, 'lbl_last_scan'):
            self.lbl_last_scan.setText(f"上次扫描: {self.engine.last_scan_time}")

    def _on_scalping_status(self, symbol: str, price: float, status: dict):
        """剥头皮状态更新回调"""
        if symbol in self.symbol_cards:
            self.symbol_cards[symbol].update_scalping(price, status)

    def _on_trade(self, record: TradeRecord):
        self._add_trade_row(record)
        self._refresh_stats()

    def _add_trade_row(self, record: TradeRecord):
        row = 0
        self.trade_table.insertRow(row)
        cells = [
            record.timestamp,
            record.symbol,
            record.action,
            record.trade_type,
            f"{record.price:.4f}",
            f"{record.quantity:.6f}",
            f"{record.amount:.2f}",
            f"{record.pnl:+.2f}" if record.action == "SELL" else "--",
            f"{record.score:.1f}",
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 2:  # 操作列着色
                if text == "BUY":
                    item.setForeground(QColor("#28a745"))
                elif text == "SELL":
                    item.setForeground(QColor("#dc3545"))
            if col == 7 and record.action == "SELL":  # 盈亏着色
                pnl = record.pnl
                item.setForeground(QColor("#28a745") if pnl >= 0 else QColor("#dc3545"))
            self.trade_table.setItem(row, col, item)

    def _refresh_trades(self):
        self.trade_table.setRowCount(0)
        for record in reversed(self.engine.trade_records[-200:]):
            self._add_trade_row(record)

    def _refresh_stats(self):
        stats = self.engine.get_stats()

        # 更新统计卡片
        pnl = stats['total_pnl']
        self.stat_cards['total_pnl'].setText(f"{pnl:+.2f} U")
        self.stat_cards['total_pnl'].setStyleSheet(
            f"color:{'#28a745' if pnl >= 0 else '#dc3545'}; font-size:22px; font-weight:bold;"
        )
        dpnl = stats['daily_pnl']
        self.stat_cards['daily_pnl'].setText(f"{dpnl:+.2f} U")
        self.stat_cards['daily_pnl'].setStyleSheet(
            f"color:{'#28a745' if dpnl >= 0 else '#dc3545'}; font-size:22px; font-weight:bold;"
        )
        self.stat_cards['total_trades'].setText(str(stats['total_trades']))
        self.stat_cards['open_positions'].setText(str(stats['open_positions']))

        # 目标进度
        target = max(1, stats['target_profit'])
        pct_total = min(100, int(pnl / target * 100)) if pnl > 0 else 0
        self.progress_total.setValue(pct_total)
        self.lbl_target_total.setText(f"{pnl:.2f} / {stats['target_profit']:.0f} USDT ({pct_total}%)")

        daily_target = max(1, stats['daily_target'])
        pct_daily = min(100, int(dpnl / daily_target * 100)) if dpnl > 0 else 0
        self.progress_daily.setValue(pct_daily)
        self.lbl_target_daily.setText(f"{dpnl:.2f} / {stats['daily_target']:.0f} USDT ({pct_daily}%)")

        # 余额 - 显示各账户明细
        if self.engine.config.paper_trading:
            # 模拟模式只显示总余额
            self.lbl_bal_spot.setText("10000.00")
            self.lbl_bal_futures.setText("--")
            self.lbl_bal_funding.setText("--")
            self.lbl_bal_total.setText("10000.00 USDT")
        else:
            # 实盘模式获取各账户余额
            try:
                balances = self.engine.client.get_total_balance()
                self.lbl_bal_spot.setText(f"{balances.get('spot', 0):.2f}")
                self.lbl_bal_futures.setText(f"{balances.get('futures', 0):.2f}")
                self.lbl_bal_funding.setText(f"{balances.get('funding', 0):.2f}")
                self.lbl_bal_total.setText(f"{balances.get('total', 0):.2f} USDT")
            except Exception as e:
                # 如果获取失败，显示总余额
                balance = self.engine._get_balance()
                self.lbl_bal_spot.setText(f"{balance:.2f}")
                self.lbl_bal_futures.setText("--")
                self.lbl_bal_funding.setText("--")
                self.lbl_bal_total.setText(f"{balance:.2f} USDT")
        
        # 盈亏
        self.lbl_pnl_total.setText(f"{pnl:+.2f} USDT")
        self.lbl_pnl_total.setStyleSheet(
            f"color:{'#28a745' if pnl >= 0 else '#dc3545'}; font-weight:bold; font-size:14px;"
        )
        self.lbl_pnl_daily.setText(f"{dpnl:+.2f} USDT")
        self.lbl_pnl_daily.setStyleSheet(
            f"color:{'#28a745' if dpnl >= 0 else '#dc3545'}; font-weight:bold;"
        )

        # 更新盈亏曲线
        pnl_history = [
            r.pnl for r in self.engine.trade_records if r.action == "SELL"
        ]
        if pnl_history:
            cumulative = list(np.cumsum(pnl_history))
            self._pnl_curve.setData(cumulative)
            # 颜色
            pen_color = '#28a745' if cumulative[-1] >= 0 else '#dc3545'
            self._pnl_curve.setPen(pg.mkPen(pen_color, width=2))

    def _refresh_rules(self):
        self.rules_table.setRowCount(0)
        rules = self.engine.rule_engine.get_rules_info()
        for rule in rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            items = [
                QTableWidgetItem(rule['name']),
                QTableWidgetItem(rule['description']),
                QTableWidgetItem(rule['type']),
                QTableWidgetItem("✅ 启用" if rule['enabled'] else "⏸ 禁用"),
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                if col == 3:
                    item.setForeground(
                        QColor("#28a745") if rule['enabled'] else QColor("#dc3545")
                    )
                self.rules_table.setItem(row, col, item)

    def _toggle_rule(self):
        row = self.rules_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一条规则")
            return
        rule_name = self.rules_table.item(row, 0).text()
        current_status = self.rules_table.item(row, 3).text()
        new_enabled = "禁用" in current_status  # 当前禁用则切换为启用
        self.engine.rule_engine.toggle_rule(rule_name, new_enabled)
        self._refresh_rules()
        self._append_log(f"规则 '{rule_name}' 已{'启用' if new_enabled else '禁用'}", 'INFO')

    def _start_stat_timer(self):
        self.stat_timer = QTimer()
        self.stat_timer.timeout.connect(self._refresh_stats)
        self.stat_timer.timeout.connect(self._refresh_scalping)
        self.stat_timer.start(3000)  # 每3秒刷新统计 + 剥头皮Tab

    def closeEvent(self, event):
        if self.engine.is_running:
            self.engine.stop()
        event.accept()
