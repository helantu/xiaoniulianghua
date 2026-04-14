"""
分析评分>=5分后的走势，计算收益率
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

symbols = ['SOLUSDT', 'DOGEUSDT']
interval = '1d'

for symbol in symbols:
    print(f"\n{'='*60}")
    print(f"分析 {symbol} 评分>=5分后的收益情况")
    print('='*60)
    
    # 获取历史数据
    print(f"\n获取 {symbol} 数据...")
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
    
    print(f"共 {len(all_klines)} 条数据")
    
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
            'signal': score.signal,
        })
    
    df = pd.DataFrame(scores)
    
    # 找出所有>=5分的买入点
    buy_signals = df[df['total_score'] >= 5.0].copy()
    print(f"\n共 {len(buy_signals)} 次评分>=5分")
    
    if len(buy_signals) == 0:
        print("没有买入信号")
        continue
    
    # 计算不同持有期的收益
    results = []
    for idx, row in buy_signals.iterrows():
        buy_price = row['price']
        buy_date = row['date']
        buy_score = row['total_score']
        
        # 找到买入点在df中的位置
        buy_idx = df[df['date'] == buy_date].index[0]
        
        # 计算不同持有期的收益
        for days in [1, 3, 5, 7, 14, 30]:
            sell_idx = buy_idx + days
            if sell_idx < len(df):
                sell_price = df.iloc[sell_idx]['price']
                profit_pct = (sell_price - buy_price) / buy_price * 100
                results.append({
                    'symbol': symbol,
                    'buy_date': buy_date.strftime('%Y-%m-%d'),
                    'buy_price': buy_price,
                    'buy_score': buy_score,
                    'hold_days': days,
                    'sell_price': sell_price,
                    'profit_pct': profit_pct,
                })
    
    results_df = pd.DataFrame(results)
    
    # 统计各持有期的收益
    print(f"\n【各持有期收益统计】")
    print(f"{'持有天数':<10} {'交易次数':<10} {'平均收益':<12} {'胜率':<10} {'最大盈利':<12} {'最大亏损':<12}")
    print("-" * 80)
    
    for days in [1, 3, 5, 7, 14, 30]:
        day_results = results_df[results_df['hold_days'] == days]
        if len(day_results) > 0:
            avg_profit = day_results['profit_pct'].mean()
            win_rate = (day_results['profit_pct'] > 0).mean() * 100
            max_profit = day_results['profit_pct'].max()
            max_loss = day_results['profit_pct'].min()
            print(f"{days:<10} {len(day_results):<10} {avg_profit:>10.2f}% {win_rate:>9.1f}% {max_profit:>11.2f}% {max_loss:>11.2f}%")
    
    # 详细列出每次买入
    print(f"\n【详细买入记录】(持有7天收益)")
    hold7 = results_df[results_df['hold_days'] == 7][['buy_date', 'buy_price', 'buy_score', 'sell_price', 'profit_pct']]
    if len(hold7) > 0:
        print(hold7.to_string(index=False))
    
    # 保存结果
    results_df.to_csv(f'E:\\xiaoniulianghua\\{symbol}_profit_analysis.csv', index=False)
    print(f"\n详细结果已保存到 {symbol}_profit_analysis.csv")

print("\n" + "="*60)
print("分析完成")
print("="*60)
