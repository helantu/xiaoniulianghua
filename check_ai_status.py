#!/usr/bin/env python3
import sys
import json
import os

sys.path.insert(0, 'E:/xiaoniulianghua/src')
from core.binance_client import BinanceClientManager

DATA_DIR = 'E:/xiaoniulianghua/data'
JOURNAL_FILE = os.path.join(DATA_DIR, 'ai_trades.json')

def main():
    client = BinanceClientManager()
    client.connect()

    print("=" * 55)
    print("AI交易状态检查报告")
    print("=" * 55)

    # 1. 账户余额
    usdt_bal = client.get_spot_balance('USDT')
    print(f"\nUSDT可用余额: {usdt_bal:.6f} U")

    account = client.get_spot_account()
    assets = {}
    for bal in account.get('balances', []):
        free = float(bal.get('free', 0))
        locked = float(bal.get('locked', 0))
        if free > 0.00001 or locked > 0.00001:
            assets[bal['asset']] = {'free': free, 'locked': locked}

    print("\n全部资产:")
    for asset, vals in sorted(assets.items()):
        print(f"  {asset}: 可用={vals['free']:.8f}  锁定={vals['locked']:.8f}")

    # 2. 历史记录
    with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
        journal = json.load(f)

    trades = journal.get('trades', [])
    open_trades = [t for t in trades if not t.get('exit_price')]
    closed_trades = [t for t in trades if t.get('exit_price')]

    print(f"\n历史交易记录: {len(trades)}笔")
    print(f"  持仓中: {len(open_trades)}笔")
    print(f"  已平仓: {len(closed_trades)}笔")

    if open_trades:
        print("\n持仓中详情:")
        for t in open_trades:
            order_id = t.get('order_id', '无订单号')
            print(f"  {t['symbol']} | 入场:{t['entry_price']} | 数量:{t['quantity']} | 订单号:{order_id} | 时间:{t.get('entry_time', '?')}")

    if closed_trades:
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        wins = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losses = [t for t in closed_trades if t.get('pnl', 0) < 0]
        print(f"\n已平仓统计: 胜{wins.__len__()}笔 负{losses.__len__()}笔 总盈亏${total_pnl:.2f}")

    # 3. 区分真假记录
    print("\n真假记录分析:")
    has_order = [t for t in trades if t.get('order_id') and str(t.get('order_id', '')).isdigit()]
    no_order = [t for t in trades if not t.get('order_id') or not str(t.get('order_id', '')).isdigit()]

    print(f"  有真实订单号: {len(has_order)}笔")
    for t in has_order:
        print(f"    {t['symbol']} 订单#{t['order_id']} 入场:{t['entry_price']} -> {t.get('exit_price', '持仓中')}")

    print(f"  无订单号(假记录): {len(no_order)}笔")
    for t in no_order:
        print(f"    {t['symbol']} 入场:{t['entry_price']} 时间:{t.get('entry_time', '?')}")

if __name__ == '__main__':
    main()
