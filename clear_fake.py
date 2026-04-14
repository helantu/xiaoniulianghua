import json
import os
from datetime import datetime

JOURNAL_FILE = 'E:/xiaoniulianghua/data/ai_trades.json'
STATS_FILE = 'E:/xiaoniulianghua/data/ai_stats.json'

with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
    journal = json.load(f)

trades = journal.get('trades', [])
closed_count = 0
for t in trades:
    if not t.get('exit_price') or t.get('exit_price') == 0:
        t['exit_price'] = t['entry_price']
        t['pnl'] = 0.0
        t['pnl_pct'] = 0.0
        t['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        t['close_reason'] = 'FAKE_RECORD_CLEARED'
        closed_count += 1

journal['trades'] = trades
journal['daily_pnl'] = 0.0

with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
    json.dump(journal, f, indent=2, ensure_ascii=False)

print(f'已清理 {closed_count} 笔假记录，标记为已平仓（0盈亏）')

# 重置统计文件
stats = {'consecutive_losses': 0, 'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
with open(STATS_FILE, 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2)
print('已重置 ai_stats.json')
print('需要重启 bot 使修复代码生效！')
