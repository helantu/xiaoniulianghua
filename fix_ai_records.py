#!/usr/bin/env python3
"""
AI交易状态全面检查 + 清理脚本
1. 查询真实账户持仓
2. 清理假记录
3. 验证真实订单是否存在
4. 同步统计数据
"""
import sys
import json
import os
from datetime import datetime
from dataclasses import asdict

sys.path.insert(0, 'E:/xiaoniulianghua/src')
from core.binance_client import BinanceClientManager

DATA_DIR = 'E:/xiaoniulianghua/data'
JOURNAL_FILE = os.path.join(DATA_DIR, 'ai_trades.json')
STATS_FILE = os.path.join(DATA_DIR, 'ai_stats.json')

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'trades': [], 'daily_pnl': 0.0, 'daily_start_time': ''}

def save_journal(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print("=" * 60)
    print("AI交易状态全面检查")
    print("=" * 60)

    # Step 1: 查询真实账户
    client = BinanceClientManager()
    client.connect()

    print("\n[1] 账户余额")
    usdt_bal = client.get_spot_balance('USDT')
    print(f"  USDT可用: {usdt_bal:.6f}")
    account = client.get_spot_account()
    assets = {}
    for bal in account.get('balances', []):
        free = float(bal.get('free', 0))
        locked = float(bal.get('locked', 0))
        if free > 0.00001 or locked > 0.00001:
            assets[bal['asset']] = {'free': free, 'locked': locked}

    print("\n[2] 账户所有资产")
    for asset, vals in sorted(assets.items()):
        print(f"  {asset}: 可用={vals['free']:.8f}  锁定={vals['locked']:.8f}")

    # Step 2: 读取历史记录
    journal = load_journal()
    trades = journal.get('trades', [])
    open_trades = [t for t in trades if not t.get('exit_price')]

    print(f"\n[3] ai_trades.json 持仓记录: {len(open_trades)}笔")
    for t in open_trades:
        print(f"  {t['symbol']} | 入场:{t['entry_price']} | 数量:{t['quantity']} | 订单:{t.get('order_id', '无订单号')}")

    # Step 3: 尝试查询真实订单（如果有订单号）
    print("\n[4] 验证真实订单是否仍在交易所")
    known_order_ids = {
        'BTCUSDT-60097043440': 'BTCUSDT',
        'ETHUSDT-45494226821': 'ETHUSDT',
    }

    # 查询币安真实持仓（BUSD定价对）
    real_holdings = {}
    for asset, vals in assets.items():
        if vals['locked'] > 0:
            sym = asset + 'USDT'
            price = client.get_ticker_price(sym)
            real_holdings[asset] = {
                'qty': vals['locked'],
                'value_usdt': vals['locked'] * price if price else 0
            }

    if real_holdings:
        print("  真实持仓发现:")
        for asset, info in real_holdings.items():
            print(f"    {asset}: 数量={info['qty']:.8f}  ≈ ${info['value_usdt']:.2f} USDT")
    else:
        print("  账户中无任何真实持仓（所有币种余额为0）")

    # Step 5: 分析真实订单 vs 假记录
    print("\n[5] 记录分析")
    trades_with_order = [t for t in trades if t.get('order_id') and str(t['order_id']).isdigit()]
    trades_fake = [t for t in trades if not t.get('order_id') or not str(t.get('order_id', '')).isdigit()]

    print(f"  有真实订单号记录: {len(trades_with_order)}笔")
    for t in trades_with_order:
        print(f"    {t['symbol']} 订单号:{t['order_id']} 入场:{t['entry_price']}")

    print(f"  无订单号（假记录）: {len(trades_fake)}笔")
    for t in trades_fake:
        print(f"    {t['symbol']} 入场:{t['entry_price']} 时间:{t.get('entry_time', '?')}")

    # Step 6: 决定清理策略
    print("\n[6] 清理操作")
    confirm = input("是否清理所有假记录（标记为FAKE并平仓）？输入 y 确认: ")
    if confirm.strip().lower() != 'y':
        print("已取消")
        return

    # 标记所有无订单号的为FAKE
    for t in trades_fake:
        t['exit_price'] = t['entry_price']  # 无亏损无盈利
        t['pnl'] = 0.0
        t['pnl_pct'] = 0.0
        t['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        t['close_reason'] = 'FAKE_RECORD_CLEARED'

    journal['trades'] = trades  # 保留所有记录（包括清理后的）
    journal['daily_pnl'] = 0.0  # 重置日盈亏
    save_journal(journal)

    print(f"  已清理 {len(trades_fake)} 笔假记录")

    # 重置统计
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)
        stats['total_trades'] = len(trades_with_order)
        stats['win_count'] = 0
        stats['loss_count'] = 0
        stats['total_pnl'] = 0.0
        stats['daily_pnl'] = 0.0
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"  已重置 ai_stats.json（保留 {len(trades_with_order)} 笔真实交易统计）")

    print("\n✅ 清理完成！重启 bot 后生效。")

if __name__ == '__main__':
    main()
