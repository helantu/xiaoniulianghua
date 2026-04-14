import json

prices = {'BTCUSDT': 69702.26, 'ETHUSDT': 2149.56}

with open('E:/xiaoniulianghua/data/ai_trades.json') as f:
    data = json.load(f)

closed = [t for t in data['trades'] if t.get('exit_price')]
realized_pnl = sum(t['pnl'] for t in closed)
print(f"=== 已平仓交易 ({len(closed)}笔) ===")
for t in closed:
    tag = " [幽灵已清]" if t.get("note") else ""
    print(f"  {t['symbol']}: PnL={t['pnl']:+.4f}U{tag}")
print(f"已实现总盈亏: {realized_pnl:+.4f}U")

open_trades = [t for t in data['trades'] if not t.get('exit_price')]
open_pnl = 0
print(f"\n=== 未平仓记录 ({len(open_trades)}笔) ===")
for t in open_trades:
    sym = t['symbol']
    entry = t['entry_price']
    qty = t['quantity']
    current = prices.get(sym, 0)
    pnl = (current - entry) * qty
    open_pnl += pnl
    print(f"  {sym}: 入场{entry} 数量{qty} 当前{current} 浮盈{pnl:+.4f}U")
print(f"未平仓浮盈: {open_pnl:+.4f}U")
print(f"\n=== 总盈亏 (已实现+浮盈): {realized_pnl + open_pnl:+.4f}U ===")
