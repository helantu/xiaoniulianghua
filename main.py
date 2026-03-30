"""
小牛量化交易系统 - 主入口
"""
import sys
import os
import logging

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from src.ui.main_window import MainWindow

# 配置日志
log_format = '[%(asctime)s] %(levelname)-8s %(name)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler('logs/niuquant.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


def main():
    # 确保必要的目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setAttribute(Qt.AA_EnableHighDpiScaling)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 运行
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
