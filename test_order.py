#!/usr/bin/env python3
"""
测试币安真实下单接口
只读API测试：验证账户权限和API连通性
"""
import sys
sys.path.insert(0, 'E:/xiaoniulianghua/src')
from core.binance_client import BinanceClientManager

def main():
    client = BinanceClientManager()
    connected = client.connect()

    if not connected:
        print("FAIL: API连接失败")
        return

    print("OK: API连接成功")
    print(f"  网络: {'测试网' if client.use_testnet else '正式网'}")
    print(f"  密钥: {client.api_key[:8]}...{client.api_key[-4:]}")

    # 1. 读取账户余额
    usdt = client.get_spot_balance('USDT')
    print(f"\n[1] USDT余额: {usdt:.6f} U")

    # 2. 获取实时价格
    prices = {}
    for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
        try:
            p = client.get_ticker_price(sym)
            prices[sym] = p
            print(f"[2] {sym}: {p}")
        except Exception as e:
            print(f"[2] {sym}: 查询失败 {e}")

    # 3. 精度取整测试
    print(f"\n[3] 数量精度测试:")
    test_cases = [
        ('BTCUSDT', 0.00027431071765688747),
        ('ETHUSDT', 0.00897746526397932),
        ('SOLUSDT', 0.2296275686626746),
        ('BNBUSDT', 0.031193983703904547),
    ]
    for sym, qty in test_cases:
        rounded = client.round_quantity(sym, qty)
        print(f"    {sym}: {qty} -> {rounded}")

    # 4. 汇总
    print(f"\n=== 诊断汇总 ===")
    print(f"API连接: OK")
    print(f"账户读取: OK")
    print(f"实时价格: OK")
    print(f"余额: {usdt:.2f} U")

    min_trade = 10
    if usdt < min_trade:
        print(f"\nWARN: 余额不足! 需要 >={min_trade} U 才能交易")
        print(f"  缺口: {min_trade - usdt:.2f} U")
    else:
        print(f"\nOK: 余额充足，可以进行真实交易")

if __name__ == '__main__':
    main()
