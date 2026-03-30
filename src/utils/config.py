"""
配置工具 - 管理应用配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.env')
load_dotenv(ENV_PATH)


class Config:
    """应用配置"""

    # 币安API
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    USE_TESTNET = os.getenv('USE_TESTNET', 'false').lower() == 'true'

    # 数据目录
    DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data'
    )
    LOG_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'logs'
    )

    # 默认币种
    DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT']

    @classmethod
    def ensure_dirs(cls):
        """确保目录存在"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)


Config.ensure_dirs()
