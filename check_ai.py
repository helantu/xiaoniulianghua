import json

# 读取AI交易记录
with open('E:/xiaoniulianghua/data/ai_trades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
print(f'=== 总交易笔数: {len(trades)} ===')
print()

# 按时间排序
for t in sorted(trades, key=lambda x: x.get('entry_time', '')):
    status = "持仓中" if not t.get('exit_price') else f"已平仓"
    print(f"ID: {t['id']}")
    print(f"  动作: {t['action']}  币种: {t['symbol']}  策略: {t['strategy']}")
    print(f"  入场: {t['entry_price']}  数量: {t['quantity']}  入场时间: {t.get('entry_time', '?')}")
    if t.get('exit_price'):
        print(f"  出场: {t['exit_price']}  盈亏: ${t['pnl']:.2f}({t['pnl_pct']:.2f}%)  原因: {t.get('close_reason', '?')}")
    else:
        print(f"  状态: 【持仓中】")
    print()

# 读取AI统计
with open('E:/xiaoniulianghua/data/ai_stats.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)

print("=== AI统计 ===")
print(f"总交易次数: {stats.get('total_trades', 0)}")
print(f"胜率: {stats.get('win_rate', 0)*100:.1f}%")
print(f"总盈亏: ${stats.get('total_pnl', 0):.2f}")
print(f"今日盈亏: ${stats.get('daily_pnl', 0):.2f}")
print(f"最大连胜: {stats.get('max_consecutive_wins', 0)}")
print(f"最大连亏: {stats.get('max_consecutive_losses', 0)}")
print(f"平均盈利: ${stats.get('avg_win', 0):.2f}")
print(f"平均亏损: ${stats.get('avg_loss', 0):.2f}")
