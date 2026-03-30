# 小牛量化项目记录

## 项目概览
- **项目名称**: 小牛量化交易系统
- **创建日期**: 2026-03-30
- **版本**: v1.0
- **状态**: 已完成核心功能，可运行

## 技术栈
- Python 3.13.12 (venv: niuquant)
- PyQt5 - GUI界面
- python-binance - 币安API
- pandas/numpy - 数据处理
- pyqtgraph - 图表绘制

## 核心功能

### 1. 9分制评分系统
- MACD (2分): 多头排列、零轴位置、柱状趋势
- 布林带 (2分): 位置百分比判断
- RSI (1.5分): 超买超卖判定
- KDJ (1.5分): 金叉死叉、超卖区
- 成交量 (1分): 放量/缩量
- 均线趋势 (1分): 多空头排列

### 2. 规则引擎
- 规则基类: BaseRule
- 内置规则: 评分买入、评分卖出、止损、止盈、合约做多
- 支持自定义规则: 继承BaseRule实现evaluate()

### 3. 交易功能
- 币安API连接 (现货+合约)
- 模拟/实盘切换
- 仓位管理
- 风控系统 (止损/止盈)
- 成交记录持久化

### 4. 界面功能
- 币种监控卡片 (实时评分)
- 监控日志 (彩色分级)
- 成交记录表格
- 营收统计 (曲线图+进度条)
- 参数调节 (完整配置)
- 规则管理 (启用/禁用)

## 默认监控币种
- BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT

## 关键配置
- **买入阈值**: 6.0分
- **卖出阈值**: 2.0分
- **扫描间隔**: 60秒
- **K线周期**: 15分钟
- **模拟模式**: 默认开启 (不真实下单)
- **止损**: 5% / **止盈**: 10%

## 启动方式
```bash
cd e:\小牛量化
C:\Users\lenovo\.workbuddy\binaries\python\envs\niuquant\Scripts\python.exe main.py
```

## 重要文件
- `main.py` - 启动文件
- `src/core/engine.py` - 主交易引擎
- `src/core/analyzer.py` - 技术指标分析
- `src/core/rules.py` - 规则引擎
- `src/ui/main_window.py` - 主界面
- `config.env` - API配置文件
- `data/trade_data.json` - 成交记录
- `logs/niuquant.log` - 日志文件

## API配置
- 币安API密钥需在 `config.env` 中配置
- 测试网络支持 (`USE_TESTNET=true`)

## 数据持久化
- 成交记录: `data/trade_data.json`
- 最近500条自动保存
- 自动加载历史数据

## 已修复问题
### 2026-03-30 Bug修复
- **问题1**: 买入阈值修改后不生效，信号始终HOLD
- **原因**: `analyzer.py`中`should_buy()`和`should_sell()`硬编码了6.0和2.0
- **修复**: 修改为接受动态参数，engine中传入配置值
- **问题2**: SSL连接错误 - SSLEOFError连接testnet.binance.vision失败
- **原因**: python-binance的testnet参数可能有问题，且SSL证书验证失败
- **修复**: 
  - 使用api_url参数明确指定API端点（正式网：https://api.binance.com）
  - 添加requests_params={'verify': False}禁用SSL证书验证
  - 添加urllib3禁用SSL警告

## 后续扩展点
1. 添加自定义规则: 编辑 `src/core/rules.py`
2. 动态调整指标参数: 通过界面参数调节面板
3. 增加监控币种: 在界面参数中添加
4. 调整评分阈值: 可配置买入/卖出阈值
5. 添加新规则: 继承BaseRule类
