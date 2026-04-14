"""
分析不同评分阈值下的胜率和收益，寻找90%+胜率的点位
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.insert(0, 'E:\\xiaoniulianghua')

from src.core.binance_client import BinanceClientManager
from src.core.analyzer import TechnicalAnalyzer

# 初始化客户端
client = BinanceClientManager()
client.connect()

symbols = ['SOLUSDT', 'DOGEUSDT', 'BTCUSDT', 'ETHUSDT']
interval = '1d'

# 测试不同的评分阈值
score_thresholds = [5.0, 5.2, 5.5, 5.8, 6.0, 6.2, 6.5]
hold_days_list = [1, 3, 5, 7, 14]

print("="*80)
print("寻找高胜率评分点位分析")
print("="*80)

all_results = []

for symbol in symbols:
    print(f"\n{'='*60}")
    print(f"分析 {symbol}")
    print('='*60)
    
    # 获取历史数据
    all_klines = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=1460)).timestamp() * 1000)
    
    while start_time < end_time:
        klines = client.client.get_klines(
            symbol=symbol, interval=interval, startTime=start_time, limit=1000
        )
        if not klines:
            break
        all_klines.extend(klines)
        start_time = klines[-1][0] + 1
    
    # 计算评分
    analyzer = TechnicalAnalyzer()
    scores = []
    for i, kline in enumerate(all_klines[200:]):
        history = all_klines[:200+i+1]
        score = analyzer.analyze(symbol, history, buy_threshold=5.0, sell_threshold=3.0)
        scores.append({
            'date': datetime.fromtimestamp(kline[0]/1000),
            'price': float(kline[4]),
            'total_score': score.total_score,
        })
    
    df = pd.DataFrame(scores)
    
    # 测试不同阈值
    for threshold in score_thresholds:
        buy_signals = df[df['total_score'] >= threshold]
        
        if len(buy_signals) < 5:  # 样本太少跳过
            continue
        
        for hold_days in hold_days_list:
            profits = []
            for idx, row in buy_signals.iterrows():
                buy_idx = df[df['date'] == row['date']].index[0]
                sell_idx = buy_idx + hold_days
                if sell_idx < len(df):
                    profit_pct = (df.iloc[sell_idx]['price'] - row['price']) / row['price'] * 100
                    profits.append(profit_pct)
            
            if len(profits) > 0:
                win_rate = (np.array(profits) > 0).mean() * 100
                avg_profit = np.mean(profits)
                all_results.append({
                    'symbol': symbol,
                    'threshold': threshold,
                    'hold_days': hold_days,
                    'count': len(profits),
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'max_profit': max(profits),
                    'max_loss': min(profits),
                })

# 显示结果
results_df = pd.DataFrame(all_results)

print("\n" + "="*80)
print("【所有组合结果】按胜率排序")
print("="*80)
print(f"{'币种':<12} {'评分阈值':<10} {'持有天数':<10} {'信号次数':<10} {'胜率':<10} {'平均收益':<12}")
print("-"*80)

# 按胜率排序
sorted_results = results_df.sort_values('win_rate', ascending=False)
for _, row in sorted_results.head(30).iterrows():
    print(f"{row['symbol']:<12} {row['threshold']:<10.1f} {row['hold_days']:<10} {row['count']:<10} {row['win_rate']:>8.1f}% {row['avg_profit']:>10.2f}%")

# 找出胜率>=90%的组合
print("\n" + "="*80)
print("【胜率 >= 90% 的组合】")
print("="*80)
high_win = results_df[results_df['win_rate'] >= 90]
if len(high_win) > 0:
    print(f"{'币种':<12} {'评分阈值':<10} {'持有天数':<10} {'信号次数':<10} {'胜率':<10} {'平均收益':<12}")
    print("-"*80)
    for _, row in high_win.iterrows():
        print(f"{row['symbol']:<12} {row['threshold']:<10.1f} {row['hold_days']:<10} {row['count']:<10} {row['win_rate']:>8.1f}% {row['avg_profit']:>10.2f}%")
else:
    print("没有找到胜率>=90%的组合")
    
# 找出胜率>=80%的组合
print("\n" + "="*80)
print("【胜率 >= 80% 的组合】")
print("="*80)
good_win = results_df[results_df['win_rate'] >= 80]
if len(good_win) > 0:
    print(f"{'币种':<12} {'评分阈值':<10} {'持有天数':<10} {'信号次数':<10} {'胜率':<10} {'平均收益':<12}")
    print("-"*80)
    for _, row in good_win.iterrows():
        print(f"{row['symbol']:<12} {row['threshold']:<10.1f} {row['hold_days']:<10} {row['count']:<10} {row['win_rate']:>8.1f}% {row['avg_profit']:>10.2f}%")

# 保存结果
results_df.to_csv('E:\\xiaoniulianghua\\high_score_analysis.csv', index=False)
print(f"\n详细结果已保存到 high_score_analysis.csv")
