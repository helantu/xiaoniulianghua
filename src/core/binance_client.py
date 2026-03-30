"""
币安API客户端 - 支持现货和合约交易
"""
import os
import logging
import ssl
import urllib3
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from dotenv import load_dotenv

# 禁用SSL警告（仅用于调试，生产环境应使用有效的证书）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.env'))

logger = logging.getLogger(__name__)


class BinanceClientManager:
    """币安客户端管理器，统一管理现货和合约连接"""

    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY', '')
        self.api_secret = os.getenv('BINANCE_API_SECRET', '')
        self.use_testnet = os.getenv('USE_TESTNET', 'false').lower() == 'true'
        self.client = None
        self._connected = False

    def connect(self) -> bool:
        """建立连接"""
        try:
            if not self.api_key or self.api_key == 'your_api_key_here':
                logger.warning("API密钥未配置，以只读模式运行（无法下单）")
                self.client = Client('', '')
                self._connected = True
                return True

            # 根据环境设置正确的API端点
            api_url = None
            if self.use_testnet:
                api_url = 'https://testnet.binance.vision'
            else:
                api_url = 'https://www.bmwweb.solutions'  # 使用未被屏蔽的币安代理
            
            logger.info(f"连接到币安{'测试网' if self.use_testnet else '正式网'}: {api_url}")
            
            # 创建SSL上下文（解决SSL连接问题）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.client = Client(
                self.api_key,
                self.api_secret,
                api_url=api_url,
                requests_params={'verify': False}
            )
            # 验证连接
            self.client.ping()
            self._connected = True
            logger.info(f"币安API连接成功 ({'测试网' if self.use_testnet else '正式网'})")
            return True

        except BinanceAPIException as e:
            logger.error(f"币安API连接失败: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"连接异常: {e}")
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.client is not None

    def get_server_time(self) -> dict:
        """获取服务器时间"""
        if not self.is_connected:
            return {}
        try:
            return self.client.get_server_time()
        except Exception as e:
            logger.error(f"获取服务器时间失败: {e}")
            return {}

    # ==================== 行情数据 ====================

    def get_klines(self, symbol: str, interval: str = '15m', limit: int = 200) -> list:
        """获取K线数据"""
        if not self.is_connected:
            return []
        try:
            return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return []

    def get_ticker_price(self, symbol: str) -> float:
        """获取当前价格"""
        if not self.is_connected:
            return 0.0
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"获取价格失败 {symbol}: {e}")
            return 0.0

    def get_24h_ticker(self, symbol: str) -> dict:
        """获取24h行情"""
        if not self.is_connected:
            return {}
        try:
            return self.client.get_ticker(symbol=symbol)
        except Exception as e:
            logger.error(f"获取24h行情失败 {symbol}: {e}")
            return {}

    # ==================== 账户信息 ====================

    def get_spot_account(self) -> dict:
        """获取现货账户信息"""
        if not self.is_connected:
            return {}
        try:
            return self.client.get_account()
        except Exception as e:
            logger.error(f"获取现货账户失败: {e}")
            return {}

    def get_spot_balance(self, asset: str = 'USDT') -> float:
        """获取现货余额"""
        account = self.get_spot_account()
        if not account:
            return 0.0
        for balance in account.get('balances', []):
            if balance['asset'] == asset:
                return float(balance['free'])
        return 0.0

    def get_futures_account(self) -> dict:
        """获取合约账户信息"""
        if not self.is_connected:
            return {}
        try:
            return self.client.futures_account()
        except Exception as e:
            logger.error(f"获取合约账户失败: {e}")
            return {}

    def get_futures_balance(self) -> float:
        """获取合约账户USDT余额"""
        account = self.get_futures_account()
        if not account:
            return 0.0
        for asset in account.get('assets', []):
            if asset['asset'] == 'USDT':
                return float(asset['availableBalance'])
        return 0.0

    # ==================== 现货交易 ====================

    def spot_market_buy(self, symbol: str, quantity: float) -> dict:
        """现货市价买入"""
        if not self.is_connected:
            return {}
        try:
            order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            logger.info(f"现货买入成功: {symbol} 数量:{quantity} 订单:{order['orderId']}")
            return order
        except BinanceOrderException as e:
            logger.error(f"现货买入失败: {e}")
            return {}

    def spot_market_sell(self, symbol: str, quantity: float) -> dict:
        """现货市价卖出"""
        if not self.is_connected:
            return {}
        try:
            order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
            logger.info(f"现货卖出成功: {symbol} 数量:{quantity} 订单:{order['orderId']}")
            return order
        except BinanceOrderException as e:
            logger.error(f"现货卖出失败: {e}")
            return {}

    def spot_limit_buy(self, symbol: str, quantity: float, price: float) -> dict:
        """现货限价买入"""
        if not self.is_connected:
            return {}
        try:
            order = self.client.order_limit_buy(
                symbol=symbol,
                quantity=quantity,
                price=str(price)
            )
            logger.info(f"现货限价买入: {symbol} 数量:{quantity} 价格:{price}")
            return order
        except BinanceOrderException as e:
            logger.error(f"现货限价买入失败: {e}")
            return {}

    # ==================== 合约交易 ====================

    def futures_market_order(self, symbol: str, side: str, quantity: float,
                              leverage: int = 1) -> dict:
        """合约市价下单 side: BUY/SELL"""
        if not self.is_connected:
            return {}
        try:
            # 设置杠杆
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logger.info(f"合约下单成功: {symbol} {side} 数量:{quantity} 杠杆:{leverage}x")
            return order
        except BinanceOrderException as e:
            logger.error(f"合约下单失败: {e}")
            return {}

    def futures_close_position(self, symbol: str, side: str, quantity: float) -> dict:
        """平仓 side: BUY(平空)/SELL(平多)"""
        if not self.is_connected:
            return {}
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly=True
            )
            logger.info(f"平仓成功: {symbol} {side} 数量:{quantity}")
            return order
        except BinanceOrderException as e:
            logger.error(f"平仓失败: {e}")
            return {}

    def get_futures_positions(self) -> list:
        """获取当前持仓"""
        if not self.is_connected:
            return []
        try:
            positions = self.client.futures_position_information()
            return [p for p in positions if float(p['positionAmt']) != 0]
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []

    def cancel_order(self, symbol: str, order_id: int, is_futures: bool = False) -> dict:
        """撤销订单"""
        if not self.is_connected:
            return {}
        try:
            if is_futures:
                return self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            else:
                return self.client.cancel_order(symbol=symbol, orderId=order_id)
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return {}

    def get_open_orders(self, symbol: str = None, is_futures: bool = False) -> list:
        """获取挂单"""
        if not self.is_connected:
            return []
        try:
            if is_futures:
                return self.client.futures_get_open_orders(symbol=symbol) if symbol else self.client.futures_get_open_orders()
            else:
                return self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()
        except Exception as e:
            logger.error(f"获取挂单失败: {e}")
            return []
