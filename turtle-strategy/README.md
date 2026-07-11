# 海龟交易法策略分析与回测

本项目对五只标的（香农芯创、立讯精密、工业富联、积存金、通信 ETF）进行海龟交易法策略分析、可视化与回测。

## 策略参数

- **上轨**：过去 20 日最高价（唐奇安通道上轨）
- **下轨**：过去 10 日最低价（唐奇安通道下轨）
- **ATR**：14 日真实波幅平均
- **买入信号**：收盘价突破上轨
- **卖出信号**：收盘价跌破下轨

## 在线报告

配置 GitHub Pages 后，本项目的访问地址为：

```
https://<你的GitHub用户名>.github.io/<仓库名>/turtle-strategy/
```

例如：

```
https://soniawill.github.io/AI-Quant/turtle-strategy/
```

## 数据来源

本项目使用仓库根目录的 `shared-data/` 作为共用行情数据源。

## 本地运行

```bash
cd turtle-strategy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_turtle_strategy.py --html-output index.html
```

## 免责声明

本策略仅供学习研究，不构成任何投资建议。
