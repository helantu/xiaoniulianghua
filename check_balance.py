import sys
sys.path.insert(0, 'E:/xiaoniulianghua/src')

from core.binance_client import BinanceClientManager
import json

client = BinanceClientManager()
client.connect()

print("=== 账户现货余额 ===")
usdt_bal = client.get_spot_balance('USDT')
print(f"  USDT可用: {usdt_bal}")

# 获取完整账户信息
account = client.get_spot_account()
for bal in account.get('balances', []):
    free = float(bal.get('free', 0))
    locked = float(bal.get('locked', 0))
    if free > 0.001 or locked > 0.001:
        print(f"  {bal['asset']}: 可用={free}  锁定={locked}")

print()
print("=== 当前真实持仓 ===")
# 获取完整现货账户（含持仓）
for bal in account.get('balances', []):
    locked = float(bal.get('locked', 0))
    if locked > 0:
        print(f"  {bal['asset']}: 锁定数量={locked} (真实持仓)")

print()
print("=== 当前各币种价格 ===")
for sym in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']:
    price = client.get_ticker_price(sym)
    print(f"  {sym}: {price}")

print()
print("=== AI持仓记录 vs 真实持仓 ===")
with open('E:/xiaoniulianghua/data/ai_trades.json', 'r') as f:
    data = json.load(f)
trades = data.get('trades', [])
open_trades = [t for t in trades if not t.get('exit_price')]
print(f"ai_trades.json记录中持仓中: {len(open_trades)}笔")
for t in open_trades:
    print(f"  {t['symbol']}: 入场{t['entry_price']} 数量{t['quantity']}")
