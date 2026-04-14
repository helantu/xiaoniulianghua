import sys
sys.path.insert(0, 'E:/xiaoniulianghua/src')

from core.binance_client import BinanceClientManager

client = BinanceClientManager()
client.connect()

# 逐个查，看哪个环节返回了0
spot = client.get_spot_balance('USDT')
print(f"现货余额: {spot}")

try:
    futures_acc = client.client.futures_account()
    assets = futures_acc.get('assets', [])
    print(f"合约assets: {assets}")
    for a in assets:
        if a['asset'] == 'USDT':
            print(f"合约USDT availableBalance: {a['availableBalance']}")
except Exception as e:
    print(f"合约账户查询失败: {e}")

funding = client.get_funding_balance('USDT')
print(f"资金账户: {funding}")

total = spot + futures_acc.get('assets', [{'availableBalance': 0}])[0].get('availableBalance', 0) + funding
print(f"粗估总和: {total}")
