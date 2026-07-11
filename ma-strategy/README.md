# MA5/MA15 交叉策略量化分析

本项目对五只标的（香农芯创、立讯精密、工业富联、积存金、通信 ETF）进行 MA5/MA15 均线交叉策略分析、可视化与回测，并输出可交互的 HTML 报告。

## 在线报告

配置 GitHub Pages 后，本项目的访问地址为：

```
https://<你的GitHub用户名>.github.io/<仓库名>/ma-strategy/
```

例如：

```
https://soniawill.github.io/AI-Quant/ma-strategy/
```

## 项目结构

```
ma-strategy/
├── run_ma_strategy.py          # 主程序：数据获取、信号计算、回测、图表生成
├── generate_html_report.py     # 生成交互式 HTML 报告
├── ma_cross_strategy_spec.json # 本次任务执行规范
├── requirements.txt            # Python 依赖
├── data/                       # 日线行情数据
├── signals/                    # 信号、权益曲线、交易记录
├── charts/                     # 可视化图表
├── index.html                  # 最终 HTML 报告
└── README.md                   # 本文件
```

> 注意：本项目的 GitHub Actions 工作流位于仓库根目录的 `.github/workflows/refresh-ma-strategy.yml`。

## 本地运行

### 1. 进入子目录并安装依赖

```bash
cd ma-strategy
python3 -m venv venv
source venv/bin/activate  # Windows 用 venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

**推荐方式（安全）：** 设置环境变量：

```bash
export TUSHARE_TOKEN="你的tushare token"
```

**本地开发方式：** 在当前目录保留 `mcp_config.json`（已加入根目录 `.gitignore`，不会提交到 GitHub）。

### 3. 运行分析

```bash
# 使用本地已有数据生成报告
python run_ma_strategy.py

# 重新拉取最新数据并生成报告
python run_ma_strategy.py --refresh-data

# 指定输出文件名
python run_ma_strategy.py --refresh-data --html-output index.html
```

## 数据来源

| 标的 | 代码 | 数据源 |
|---|---|---|
| 香农芯创 | 300475.SZ | Tushare `pro.daily` |
| 立讯精密 | 002475.SZ | Tushare `pro.daily` |
| 工业富联 | 601138.SH | Tushare `pro.daily` |
| 通信 ETF | 515880.SH | akshare `fund_etf_hist_sina` |
| 积存金 | AU9999.SGE | akshare `spot_hist_sge('Au99.99')` |

## 策略说明

- 短均线窗口：5 日
- 长均线窗口：15 日
- 买入信号：MA5 上穿 MA15（金叉）
- 卖出信号：MA5 下穿 MA15（死叉）
- 回测假设：初始资金 100,000 元，手续费 0.03%，滑点 0.1%，全仓买卖

## 免责声明

本策略仅供学习研究，不构成任何投资建议。历史回测收益不代表未来表现。
