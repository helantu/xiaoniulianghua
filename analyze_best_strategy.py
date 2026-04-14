"""
深入分析：尝试组合条件寻找高胜率策略
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

print("="*80)
print("深入分析：寻找最优策略")
print("="*80)

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
    
    # 计算评分和详细指标
    analyzer = TechnicalAnalyzer()
    scores = []
    for i, kline in enumerate(all_klines[200:]):
        history = all_klines[:200+i+1]
        score = analyzer.analyze(symbol, history, buy_threshold=5.0, sell_threshold=3.0)
        scores.append({
            'date': datetime.fromtimestamp(kline[0]/1000),
            'price': float(kline[4]),
            'total_score': score.total_score,
            'macd': score.macd_score,
            'boll': score.boll_score,
            'rsi': score.rsi_score,
            'kdj': score.kdj_score,
            'volume': score.volume_score,
            'trend': score.trend_score,
        })
    
    df = pd.DataFrame(scores)
    
    # 计算未来7天收益
    df['future_return_7d'] = df['price'].shift(-7) / df['price'] - 1
    
    print(f"\n【不同评分阈值下的7天收益统计】")
    print(f"{'评分条件':<20} {'信号次数':<10} {'胜率':<10} {'平均收益':<12} {'正收益次数':<10}")
    print("-"*70)
    
    # 测试各种条件
    conditions = [
        ("总分>=5.0", df['total_score'] >= 5.0),
        ("总分>=5.5", df['total_score'] >= 5.5),
        ("总分>=6.0", df['total_score'] >= 6.0),
        ("总分>=5.5 & MACD>=1.5", (df['total_score'] >= 5.5) & (df['macd'] >= 1.5)),
        ("总分>=5.5 & KDJ>=1.0", (df['total_score'] >= 5.5) & (df['kdj'] >= 1.0)),
        ("总分>=5.5 & RSI>=0.5", (df['total_score'] >= 5.5) & (df['rsi'] >= 0.5)),
        ("总分>=5.5 & TREND>=0.5", (df['total_score'] >= 5.5) & (df['trend'] >= 0.5)),
        ("MACD>=2 & KDJ>=1", (df['macd'] >= 2) & (df['kdj'] >= 1)),
        ("MACD>=1.5 & BOLL>=1 & KDJ>=0.5", (df['macd'] >= 1.5) & (df['boll'] >= 1) & (df['kdj'] >= 0.5)),
        ("总分>=5.0 & MACD>=1.5 & TREND>=0.5", (df['total_score'] >= 5.0) & (df['macd'] >= 1.5) & (df['trend'] >= 0.5)),
    ]
    
    for name, condition in conditions:
        filtered = df[condition & df['future_return_7d'].notna()]
        if len(filtered) >= 3:
            returns = filtered['future_return_7d'].values * 100
            win_rate = (returns > 0).mean() * 100
            avg_return = returns.mean()
            win_count = (returns > 0).sum()
            print(f"{name:<20} {len(filtered):<10} {win_rate:>8.1f}% {avg_return:>10.2f}% {win_count:>8}")

print("\n" + "="*80)
print("分析完成")
print("="*80)
