"""
小牛量化 - 主界面
PyQt5 可视化界面，包含监控面板、日志、参数、成交记录、营收统计
"""
import sys
import os
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
        self.setFixedHeight(120)
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

        # 顶部：币名 + 信号
        top = QHBoxLayout()
        self.lbl_name = QLabel(symbol.replace('USDT', ''))
        self.lbl_name.setStyleSheet("font-size:16px; font-weight:bold; color:#00d4ff;")
        self.lbl_signal = QLabel("--")
        self.lbl_signal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_signal.setStyleSheet("font-size:13px; font-weight:bold; padding:2px 8px; border-radius:4px;")
        top.addWidget(self.lbl_name)
        top.addStretch()
        top.addWidget(self.lbl_signal)
        layout.addLayout(top)

        # 价格
        self.lbl_price = QLabel("$--")
        self.lbl_price.setStyleSheet("font-size:18px; font-weight:bold; color:#ffffff;")
        layout.addWidget(self.lbl_price)

        # 评分条
        score_row = QHBoxLayout()
        self.lbl_score = QLabel("评分: --/9")
        self.lbl_score.setStyleSheet("color:#a0a0c0; font-size:12px;")
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 90)
        self.score_bar.setValue(0)
        self.score_bar.setFixedHeight(10)
        self.score_bar.setTextVisible(False)
        score_row.addWidget(self.lbl_score)
        score_row.addWidget(self.score_bar)
        layout.addLayout(score_row)

        # 底部：各维度分数
        self.lbl_detail = QLabel("MACD:- BOLL:- RSI:- KDJ:-")
        self.lbl_detail.setStyleSheet("color:#606080; font-size:11px;")
        layout.addWidget(self.lbl_detail)

    def update_score(self, score: SignalScore):
        price_str = f"${score.price:,.4f}" if score.price < 1 else f"${score.price:,.2f}"
        self.lbl_price.setText(price_str)
        self.lbl_score.setText(f"评分: {score.total_score:.1f}/9")
        self.score_bar.setValue(int(score.total_score * 10))

        # 评分条颜色
        if score.total_score >= 6:
            bar_color = "#28a745"
        elif score.total_score >= 4:
            bar_color = "#ffc107"
        else:
            bar_color = "#dc3545"
        self.score_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {bar_color}; border-radius: 4px; }}"
        )

        # 信号标签
        signal_styles = {
            "BUY":  ("买入", "#1a472a", "#28a745"),
            "SELL": ("卖出", "#721c24", "#dc3545"),
            "HOLD": ("观望", "#333355", "#a0a0c0"),
        }
        text, bg, fg = signal_styles.get(score.signal, ("--", "#333355", "#a0a0c0"))
        self.lbl_signal.setText(text)
        self.lbl_signal.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{fg}; "
            f"background:{bg}; padding:2px 8px; border-radius:4px;"
        )

        self.lbl_detail.setText(
            f"MACD:{score.macd_score:.1f} "
            f"BOLL:{score.boll_score:.1f} "
            f"RSI:{score.rsi_score:.1f} "
            f"KDJ:{score.kdj_score:.1f} "
            f"VOL:{score.volume_score:.1f}"
        )

        # 高分时高亮边框
        if score.total_score >= 6:
            self.setStyleSheet("""
                QFrame {
                    background: #16213e;
                    border: 2px solid #28a745;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: #16213e;
                    border: 1px solid #2d2d4e;
                    border-radius: 10px;
                }
            """)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    signal_log = pyqtSignal(str, str)
    signal_score = pyqtSignal(object)
    signal_trade = pyqtSignal(object)
    signal_stats = pyqtSignal(dict)

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
        self.signal_log.connect(self._append_log)
        self.signal_score.connect(self._on_score_update)
        self.signal_trade.connect(self._on_trade)

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

        # 账户余额
        balance_box = QGroupBox("账户概览")
        bl = QGridLayout(balance_box)
        bl.setSpacing(6)

        self.lbl_bal_spot = QLabel("--")
        self.lbl_bal_spot.setStyleSheet("color:#28a745; font-weight:bold; font-size:14px;")
        self.lbl_pnl_total = QLabel("--")
        self.lbl_pnl_total.setStyleSheet("font-weight:bold; font-size:14px;")
        self.lbl_pnl_daily = QLabel("--")
        self.lbl_pnl_daily.setStyleSheet("font-weight:bold;")

        bl.addWidget(QLabel("可用余额:"), 0, 0)
        bl.addWidget(self.lbl_bal_spot, 0, 1)
        bl.addWidget(QLabel("累计盈亏:"), 1, 0)
        bl.addWidget(self.lbl_pnl_total, 1, 1)
        bl.addWidget(QLabel("今日盈亏:"), 2, 0)
        bl.addWidget(self.lbl_pnl_daily, 2, 1)
        layout.addWidget(balance_box)
        return w

    def _build_tab_panel(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_log_tab(), "📋 监控日志")
        tabs.addTab(self._build_trade_tab(), "💰 成交记录")
        tabs.addTab(self._build_profit_tab(), "📈 营收统计")
        tabs.addTab(self._build_params_tab(), "⚙️ 参数调节")
        tabs.addTab(self._build_rules_tab(), "📜 规则管理")
        return tabs

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
            card = self._make_stat_card(title, "--", color)
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

    def _make_stat_card(self, title: str, value: str, color: str):
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
        sl.addWidget(QLabel("监控币种:"), 1, 0)
        self.inp_symbols = QLineEdit()
        self.inp_symbols.setText(','.join(self.engine.config.symbols))
        self.inp_symbols.setPlaceholderText("BTCUSDT,ETHUSDT,SOLUSDT,DOGEUSDT")
        sl.addWidget(self.inp_symbols, 1, 1, 1, 3)
        layout.addWidget(scan_box)

        # 评分阈值
        score_box = QGroupBox("评分阈值")
        sbl = QGridLayout(score_box)
        sbl.setSpacing(8)
        sbl.addWidget(QLabel("买入评分阈值 (≥N分买入):"), 0, 0)
        self.spin_buy_th = QDoubleSpinBox()
        self.spin_buy_th.setRange(1.0, 9.0)
        self.spin_buy_th.setSingleStep(0.5)
        self.spin_buy_th.setValue(self.engine.config.buy_threshold)
        sbl.addWidget(self.spin_buy_th, 0, 1)
        sbl.addWidget(QLabel("卖出评分阈值 (≤N分卖出):"), 1, 0)
        self.spin_sell_th = QDoubleSpinBox()
        self.spin_sell_th.setRange(0.0, 5.0)
        self.spin_sell_th.setSingleStep(0.5)
        self.spin_sell_th.setValue(self.engine.config.sell_threshold)
        sbl.addWidget(self.spin_sell_th, 1, 1)
        layout.addWidget(score_box)

        # 仓位管理
        pos_box = QGroupBox("仓位与风控")
        pl = QGridLayout(pos_box)
        pl.setSpacing(8)
        params = [
            ("每次买入仓位(%):", "spin_buy_pct", self.engine.config.buy_quantity_pct * 100, 1, 100),
            ("单币最大仓位(%):", "spin_max_pos", self.engine.config.max_position_pct * 100, 1, 100),
            ("止损比例(%):", "spin_stop_loss", self.engine.config.stop_loss_pct, 0.5, 50),
            ("止盈比例(%):", "spin_take_profit", self.engine.config.take_profit_pct, 1, 200),
        ]
        for i, (label, attr, val, min_v, max_v) in enumerate(params):
            row, col = i // 2, (i % 2) * 2
            pl.addWidget(QLabel(label), row, col)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setSingleStep(0.5)
            spin.setValue(val)
            setattr(self, attr, spin)
            pl.addWidget(spin, row, col + 1)
        layout.addWidget(pos_box)

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
        symbols_str = self.inp_symbols.text().strip()
        symbols = [s.strip().upper() for s in symbols_str.split(',') if s.strip()]

        new_config = {
            'paper_trading': self.chk_paper.isChecked(),
            'futures_enabled': self.chk_futures.isChecked(),
            'scan_interval': self.spin_interval.value(),
            'kline_interval': self.combo_kline.currentText(),
            'symbols': symbols if symbols else self.engine.config.symbols,
            'buy_threshold': self.spin_buy_th.value(),
            'sell_threshold': self.spin_sell_th.value(),
            'buy_quantity_pct': self.spin_buy_pct.value() / 100,
            'max_position_pct': self.spin_max_pos.value() / 100,
            'stop_loss_pct': self.spin_stop_loss.value(),
            'take_profit_pct': self.spin_take_profit.value(),
            'futures_buy_threshold': self.spin_fut_th.value(),
            'futures_leverage': self.spin_leverage.value(),
            'target_profit': self.spin_target.value(),
            'daily_target': self.spin_daily_target.value(),
        }
        self.engine.update_config(new_config)

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

        # 同步更新监控卡片
        for sym in symbols:
            if sym not in self.symbol_cards:
                card = SymbolCard(sym)
                self.symbol_cards[sym] = card

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

        # 余额
        balance = self.engine._get_balance()
        self.lbl_bal_spot.setText(f"{balance:.2f} USDT")
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
        self.stat_timer.start(3000)  # 每3秒刷新统计

    def closeEvent(self, event):
        if self.engine.is_running:
            self.engine.stop()
        event.accept()
