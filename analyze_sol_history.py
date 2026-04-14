"""
分析 SOLUSDT 近3年历史数据，统计评分分布规律
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

# 获取近3年数据（币安限制单次1000条，需要分批获取）
print("正在获取 SOLUSDT 历史数据...")

symbol = 'SOLUSDT'
interval = '1d'  # 日线数据
all_klines = []

# 从3年前开始获取
end_time = int(datetime.now().timestamp() * 1000)
start_time = int((datetime.now() - timedelta(days=1095)).timestamp() * 1000)

# 分批获取数据
while start_time < end_time:
    klines = client.client.get_klines(
        symbol=symbol,
        interval=interval,
        startTime=start_time,
        limit=1000
    )
    if not klines:
        break
    all_klines.extend(klines)
    start_time = klines[-1][0] + 1  # 从最后一条的下一条开始
    print(f"已获取 {len(all_klines)} 条数据...")

print(f"\n总共获取 {len(all_klines)} 条日线数据")

# 分析评分
analyzer = TechnicalAnalyzer()
scores = []

print("\n正在分析评分...")
for i, kline in enumerate(all_klines[200:]):  # 跳过前200条（需要足够数据计算指标）
    # 使用到当前日期的数据
    history = all_klines[:200+i+1]
    score = analyzer.analyze(symbol, history, buy_threshold=6.0, sell_threshold=2.0)
    scores.append({
        'date': datetime.fromtimestamp(kline[0]/1000).strftime('%Y-%m-%d'),
        'price': float(kline[4]),
        'total_score': score.total_score,
        'signal': score.signal,
        'macd': score.macd_score,
        'boll': score.boll_score,
        'rsi': score.rsi_score,
        'kdj': score.kdj_score,
    })
    if (i + 1) % 100 == 0:
        print(f"已分析 {i+1}/{len(all_klines)-200} 条...")

# 统计分析
df = pd.DataFrame(scores)
print("\n" + "="*60)
print("SOLUSDT 近3年评分统计分析")
print("="*60)
print(f"\n数据时间范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
print(f"总样本数: {len(df)}")

print(f"\n【评分分布】")
print(f"最低分: {df['total_score'].min():.2f}")
print(f"最高分: {df['total_score'].max():.2f}")
print(f"平均分: {df['total_score'].mean():.2f}")
print(f"中位数: {df['total_score'].median():.2f}")
print(f"标准差: {df['total_score'].std():.2f}")

print(f"\n【分数段分布】")
bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
labels = ['0-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10']
df['score_range'] = pd.cut(df['total_score'], bins=bins, labels=labels, right=False)
print(df['score_range'].value_counts().sort_index())

print(f"\n【信号分布】")
print(df['signal'].value_counts())

print(f"\n【高分日统计】(>=6分)")
high_scores = df[df['total_score'] >= 6]
if len(high_scores) > 0:
    print(f"出现次数: {len(high_scores)}")
    print(f"占比: {len(high_scores)/len(df)*100:.2f}%")
    print(f"平均分: {high_scores['total_score'].mean():.2f}")
    print("\n高分日期示例:")
    print(high_scores[['date', 'price', 'total_score']].head(10).to_string(index=False))
else:
    print("没有出现 >=6分的情况")

print(f"\n【低分日统计】(<=2分)")
low_scores = df[df['total_score'] <= 2]
if len(low_scores) > 0:
    print(f"出现次数: {len(low_scores)}")
    print(f"占比: {len(low_scores)/len(df)*100:.2f}%")
    print(f"平均分: {low_scores['total_score'].mean():.2f}")
    print("\n低分日期示例:")
    print(low_scores[['date', 'price', 'total_score']].head(10).to_string(index=False))

# 保存结果
df.to_csv('E:\\xiaoniulianghua\\sol_analysis.csv', index=False)
print(f"\n详细数据已保存到 sol_analysis.csv")
