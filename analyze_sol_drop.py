"""
分析SOL在2026-03-30 06:45的急跌事件
并寻找历史上类似的模式用于抄底策略
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.binance_client import BinanceClientManager
from core.analyzer import TechnicalAnalyzer
from datetime import datetime, timedelta
import json


def get_klines_at_time(client, symbol, interval, start_time, limit=100):
    """获取指定时间前后的K线数据"""
    # 转换为毫秒时间戳
    start_ms = int(start_time.timestamp() * 1000)
    
    try:
        # 使用Binance API获取历史K线
        klines = client.client.get_klines(
            symbol=symbol,
            interval=interval,
            startTime=start_ms - (limit * get_interval_ms(interval)),
            endTime=start_ms + (50 * get_interval_ms(interval)),
            limit=limit + 50
        )
        return klines
    except Exception as e:
        print(f"获取K线失败: {e}")
        return []


def get_interval_ms(interval):
    """将interval转换为毫秒"""
    mapping = {
        '1m': 60 * 1000,
        '3m': 3 * 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '2h': 2 * 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '6h': 6 * 60 * 60 * 1000,
        '8h': 8 * 60 * 60 * 1000,
        '12h': 12 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
    }
    return mapping.get(interval, 15 * 60 * 1000)


def analyze_drop_pattern(klines, target_time_str):
    """分析急跌模式"""
    target_time = datetime.strptime(target_time_str, '%Y-%m-%d %H:%M')
    target_ms = int(target_time.timestamp() * 1000)
    
    # 找到目标时间对应的K线索引
    target_idx = None
    for i, k in enumerate(klines):
        k_time = datetime.fromtimestamp(k[0] / 1000)
        if abs(k[0] - target_ms) < 60000:  # 1分钟内
            target_idx = i
            break
    
    if target_idx is None:
        print(f"未找到目标时间 {target_time_str} 的K线数据")
        return None
    
    print(f"\n{'='*60}")
    print(f"SOL急跌分析 - {target_time_str}")
    print(f"{'='*60}")
    
    # 分析前后各10根K线
    start_idx = max(0, target_idx - 10)
    end_idx = min(len(klines), target_idx + 11)
    
    context_klines = klines[start_idx:end_idx]
    
    # 计算关键指标
    prices = [float(k[4]) for k in context_klines]  # 收盘价
    highs = [float(k[2]) for k in context_klines]
    lows = [float(k[3]) for k in context_klines]
    volumes = [float(k[5]) for k in context_klines]
    
    # 找出急跌起点和终点
    drop_start_idx = 0
    max_price = max(prices[:target_idx - start_idx + 1]) if target_idx > start_idx else prices[0]
    min_price = min(prices[target_idx - start_idx:]) if target_idx < end_idx else prices[-1]
    
    # 计算跌幅
    drop_pct = (max_price - min_price) / max_price * 100 if max_price > 0 else 0
    
    print(f"\n[急跌特征]")
    print(f"   高点: {max_price:.4f} USDT")
    print(f"   低点: {min_price:.4f} USDT")
    print(f"   跌幅: {drop_pct:.2f}%")
    print(f"   急跌K线时间: {datetime.fromtimestamp(klines[target_idx][0]/1000)}")
    
    # 分析急跌K线特征
    drop_kline = klines[target_idx]
    open_p = float(drop_kline[1])
    high_p = float(drop_kline[2])
    low_p = float(drop_kline[3])
    close_p = float(drop_kline[4])
    volume = float(drop_kline[5])
    
    body_pct = abs(close_p - open_p) / open_p * 100
    upper_shadow = (high_p - max(open_p, close_p)) / open_p * 100
    lower_shadow = (min(open_p, close_p) - low_p) / open_p * 100
    
    print(f"\n[急跌K线详细数据]")
    print(f"   开盘: {open_p:.4f}")
    print(f"   最高: {high_p:.4f}")
    print(f"   最低: {low_p:.4f}")
    print(f"   收盘: {close_p:.4f}")
    print(f"   成交量: {volume:.2f} SOL")
    print(f"   实体幅度: {body_pct:.2f}%")
    print(f"   上影线: {upper_shadow:.2f}%")
    print(f"   下影线: {lower_shadow:.2f}%")
    
    # 使用分析器计算指标 - 需要至少100根K线才能计算
    analyzer = TechnicalAnalyzer()
    # 获取更多历史数据用于计算指标
    score = analyzer.analyze('SOLUSDT', klines[:target_idx+1])
    
    print(f"\n[技术指标评分 (急跌前)]")
    print(f"   总分: {score.total_score:.1f}")
    print(f"   MACD: {score.macd_score:.1f}")
    print(f"   BOLL: {score.boll_score:.1f}")
    print(f"   RSI: {score.rsi_score:.1f}")
    print(f"   KDJ: {score.kdj_score:.1f}")
    print(f"   VOL: {score.volume_score:.1f}")
    print(f"   TREND: {score.trend_score:.1f}")
    
    # 定义急跌模式特征
    pattern = {
        'drop_pct': drop_pct,
        'body_pct': body_pct,
        'lower_shadow': lower_shadow,
        'volume_spike': volume / (sum(volumes[:target_idx-start_idx]) / max(1, target_idx-start_idx)) if target_idx > start_idx else 1,
        'pre_score': score.total_score,
        'pre_macd': score.macd_score,
        'pre_rsi': score.rsi_score,
    }
    
    return pattern, target_idx


def find_similar_patterns(client, symbol, pattern, start_year=2021, end_year=2026):
    """寻找历史上类似的急跌模式"""
    print(f"\n{'='*60}")
    print(f"寻找历史上类似的急跌模式 ({start_year}-{end_year})")
    print(f"{'='*60}")
    
    similar_events = []
    
    # 获取3年历史数据（按季度分段获取）
    analyzer = TechnicalAnalyzer()
    
    for year in range(start_year, end_year + 1):
        for month in [1, 4, 7, 10]:
            try:
                start_time = datetime(year, month, 1)
                end_time = datetime(year + (month+3)//12, (month+3)%12 or 12, 1)
                
                start_ms = int(start_time.timestamp() * 1000)
                end_ms = int(end_time.timestamp() * 1000)
                
                # 获取更多数据用于计算指标（需要至少100根K线）
                klines_start = start_ms - (120 * 15 * 60 * 1000)  # 提前120根15分钟K线
                
                klines = client.client.get_klines(
                    symbol=symbol,
                    interval='15m',
                    startTime=klines_start,
                    endTime=end_ms,
                    limit=1000
                )
                
                if len(klines) < 150:  # 需要足够的数据计算指标
                    continue
                
                # 扫描急跌模式
                for i in range(120, len(klines) - 20):  # 从第120根开始，确保有足够历史数据
                    # 计算当前K线跌幅
                    prev_close = float(klines[i-1][4])
                    curr_open = float(klines[i][1])
                    curr_low = float(klines[i][3])
                    curr_close = float(klines[i][4])
                    curr_volume = float(klines[i][5])
                    
                    # 急跌条件：单根K线跌幅超过3%
                    drop_pct = (prev_close - curr_close) / prev_close * 100
                    
                    if drop_pct >= 3.0:  # 急跌超过3%
                        # 计算后续反弹
                        future_prices = [float(k[4]) for k in klines[i:i+20]]
                        min_future = min(future_prices) if future_prices else curr_close
                        max_future = max(future_prices) if future_prices else curr_close
                        
                        # 计算反弹幅度
                        rebound_pct = (max_future - curr_close) / curr_close * 100
                        
                        # 获取当时的指标评分（使用到当前K线为止的所有数据）
                        context = klines[:i+1]
                        score = analyzer.analyze(symbol, context)
                        
                        event = {
                            'time': datetime.fromtimestamp(klines[i][0]/1000).strftime('%Y-%m-%d %H:%M'),
                            'drop_pct': drop_pct,
                            'rebound_pct': rebound_pct,
                            'price': curr_close,
                            'score': score.total_score,
                            'macd': score.macd_score,
                            'rsi': score.rsi_score,
                            'kdj': score.kdj_score,
                            'boll': score.boll_score,
                            'vol': score.volume_score,
                            'trend': score.trend_score,
                        }
                        similar_events.append(event)
                        
            except Exception as e:
                continue
    
    # 按反弹幅度排序
    similar_events.sort(key=lambda x: x['rebound_pct'], reverse=True)
    
    print(f"\n找到 {len(similar_events)} 次急跌事件")
    print(f"\n反弹最强劲的前10次:")
    print("-" * 100)
    print(f"{'时间':<20} {'跌幅':<8} {'反弹':<8} {'价格':<10} {'总分':<6} {'MACD':<5} {'RSI':<5} {'KDJ':<5} {'BOLL':<5} {'VOL':<5}")
    print("-" * 100)
    
    for e in similar_events[:10]:
        print(f"{e['time']:<20} {e['drop_pct']:>5.1f}% {e['rebound_pct']:>5.1f}% {e['price']:>9.2f} "
              f"{e['score']:>5.1f} {e['macd']:>4.1f} {e['rsi']:>4.1f} {e['kdj']:>4.1f} {e['boll']:>4.1f} {e['vol']:>4.1f}")
    
    # 分析成功抄底的指标特征
    successful = [e for e in similar_events if e['rebound_pct'] > 5]  # 反弹超过5%算成功
    failed = [e for e in similar_events if e['rebound_pct'] < 2]  # 反弹小于2%算失败
    
    if successful:
        avg_score = sum(e['score'] for e in successful) / len(successful)
        avg_macd = sum(e['macd'] for e in successful) / len(successful)
        avg_rsi = sum(e['rsi'] for e in successful) / len(successful)
        avg_kdj = sum(e['kdj'] for e in successful) / len(successful)
        avg_boll = sum(e['boll'] for e in successful) / len(successful)
        avg_vol = sum(e['vol'] for e in successful) / len(successful)
        
        print(f"\n成功抄底特征分析 (反弹>5%, 共{len(successful)}次):")
        print(f"   平均总分: {avg_score:.2f}")
        print(f"   平均MACD: {avg_macd:.2f}")
        print(f"   平均RSI: {avg_rsi:.2f}")
        print(f"   平均KDJ: {avg_kdj:.2f}")
        print(f"   平均BOLL: {avg_boll:.2f}")
        print(f"   平均VOL: {avg_vol:.2f}")
    
    if failed:
        avg_score_f = sum(e['score'] for e in failed) / len(failed)
        print(f"\n失败抄底特征分析 (反弹<2%, 共{len(failed)}次):")
        print(f"   平均总分: {avg_score_f:.2f}")
    
    return similar_events


def main():
    client = BinanceClientManager()
    if not client.connect():
        print("❌ 连接币安API失败")
        return
    
    # 分析2026-03-30 06:45的急跌
    target_time = datetime(2026, 3, 30, 6, 45)
    
    # 获取15分钟K线
    klines_15m = get_klines_at_time(client, 'SOLUSDT', '15m', target_time, 100)
    
    if klines_15m:
        pattern, idx = analyze_drop_pattern(klines_15m, '2026-03-30 06:45')
        
        # 寻找历史上类似的模式
        similar = find_similar_patterns(client, 'SOLUSDT', pattern, 2021, 2026)
        
        # 保存结果
        result = {
            'target_event': {
                'time': '2026-03-30 06:45',
                'pattern': pattern
            },
            'similar_events': similar[:20]
        }
        
        with open('sol_drop_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析结果已保存到 sol_drop_analysis.json")


if __name__ == '__main__':
    main()
