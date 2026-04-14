import sys
sys.path.insert(0, 'E:/xiaoniulianghua/src')
from core.binance_client import BinanceClientManager

client = BinanceClientManager()
client.connect()

print("=== 目标金额法精度测试 ===")
print()

# 模拟各币种以约15%仓位下单（假设账户100U -> 15U每笔）
test_amounts = [15.0, 20.0, 10.0]
for amt in test_amounts:
    print(f"目标金额: ${amt}")
    for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
        price = client.get_ticker_price(sym)
        qty = client.round_quantity(sym, 0, target_usdt=amt)
        notional = qty * price
        print(f"  {sym}: {qty} x {price:.2f} = ${notional:.2f}")
    print()
