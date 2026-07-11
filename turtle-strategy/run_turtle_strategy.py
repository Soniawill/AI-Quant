#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海龟交易法策略分析与回测
- 标的：香农芯创、立讯精密、工业富联、积存金(AU9999.SGE)、通信ETF(515880.SH)
- 上轨：20日最高价；下轨：10日最低价
- ATR：14日
- 突破上轨买入，跌破下轨卖出
- 输出：turtle_signals CSV、回测指标 JSON、可视化图表、HTML报告
"""
import os
import json
import glob
import base64
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 中文显示
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'PingFang SC', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

ENTRY_PERIOD = 20
EXIT_PERIOD = 10
ATR_PERIOD = 14
INITIAL_CAPITAL = 100000.0
COMMISSION = 0.0003
SLIPPAGE = 0.001
TRADING_DAYS_PER_YEAR = 252


def load_data(data_dir='data'):
    """加载所有已存储的日线数据，优先从 shared-data 读取"""
    candidate_dirs = [data_dir, '../shared-data', 'shared-data']
    files = []
    for d in candidate_dirs:
        if os.path.isdir(d):
            files = sorted(glob.glob(os.path.join(d, '*_daily.csv')))
            if files:
                break
    assets = []
    for f in files:
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        name = df['name'].iloc[0] if 'name' in df.columns else os.path.basename(f).replace('_daily.csv', '')
        ticker = df['ticker'].iloc[0] if 'ticker' in df.columns else None
        assets.append({
            'name': name,
            'ticker': ticker,
            'df': df
        })
    return assets


def calculate_signals(df):
    """计算唐奇安通道、ATR 和买卖信号"""
    df = df.copy()

    # 唐奇安通道
    df['upper_channel'] = df['high'].rolling(window=ENTRY_PERIOD, min_periods=ENTRY_PERIOD).max()
    df['lower_channel'] = df['low'].rolling(window=EXIT_PERIOD, min_periods=EXIT_PERIOD).min()

    # 真实波幅 TR
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

    # ATR
    df['atr'] = df['tr'].rolling(window=ATR_PERIOD, min_periods=ATR_PERIOD).mean()

    # 信号：突破上轨买入（1），跌破下轨卖出（-1）
    df['signal'] = 0
    long_signal = (df['close'] > df['upper_channel'].shift(1)) & (df['close'].shift(1) <= df['upper_channel'].shift(2))
    short_signal = (df['close'] < df['lower_channel'].shift(1)) & (df['close'].shift(1) >= df['lower_channel'].shift(2))

    df.loc[long_signal, 'signal'] = 1
    df.loc[short_signal, 'signal'] = -1

    df['buy_signal'] = np.where(long_signal, df['close'], np.nan)
    df['sell_signal'] = np.where(short_signal, df['close'], np.nan)

    # 持仓状态
    df['position'] = 0
    position = 0
    positions = []
    for _, row in df.iterrows():
        if row['signal'] == 1:
            position = 1
        elif row['signal'] == -1:
            position = 0
        positions.append(position)
    df['position'] = positions

    return df


def backtest(df, name, ticker):
    """根据海龟信号进行模拟交易回测"""
    capital = INITIAL_CAPITAL
    position = 0
    shares = 0
    trades = []
    equity_curve = []
    buy_price = None

    for _, row in df.iterrows():
        price = row['close']
        date = row['date']

        if row['signal'] == 1 and position == 0:
            # 买入
            exec_price = price * (1 + SLIPPAGE)
            shares = int(capital * (1 - COMMISSION) / exec_price)
            cost = shares * exec_price
            capital -= cost * (1 + COMMISSION)
            position = 1
            buy_price = exec_price
            trades.append({
                'date': date,
                'type': 'buy',
                'price': exec_price,
                'shares': shares,
                'capital_after': capital + shares * exec_price
            })
        elif row['signal'] == -1 and position == 1:
            # 卖出
            exec_price = price * (1 - SLIPPAGE)
            proceeds = shares * exec_price
            capital += proceeds * (1 - COMMISSION)
            pnl = proceeds - (shares * buy_price)
            trades.append({
                'date': date,
                'type': 'sell',
                'price': exec_price,
                'shares': shares,
                'pnl': pnl,
                'capital_after': capital
            })
            position = 0
            shares = 0
            buy_price = None

        market_value = shares * price if position == 1 else 0
        equity = capital + market_value
        equity_curve.append({'date': date, 'equity': equity})

    # 最后一天若仍持仓，按收盘价清仓
    if position == 1:
        last_row = df.iloc[-1]
        exec_price = last_row['close'] * (1 - SLIPPAGE)
        proceeds = shares * exec_price
        capital += proceeds * (1 - COMMISSION)
        pnl = proceeds - (shares * buy_price)
        trades.append({
            'date': last_row['date'],
            'type': 'sell',
            'price': exec_price,
            'shares': shares,
            'pnl': pnl,
            'capital_after': capital
        })
        equity_curve[-1]['equity'] = capital

    equity_df = pd.DataFrame(equity_curve)
    equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)

    # 买入持有基准
    df_copy = df.copy().reset_index(drop=True)
    benchmark_equity = INITIAL_CAPITAL * (df_copy['close'] / df_copy['close'].iloc[0])
    benchmark_returns = benchmark_equity.pct_change().fillna(0)

    # 指标计算
    total_return = (equity_df['equity'].iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL
    n_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
    years = max(n_days / 365.0, 1e-6)
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    cummax = equity_df['equity'].cummax()
    drawdown = (equity_df['equity'] - cummax) / cummax
    max_drawdown = drawdown.min()

    daily_returns = equity_df['returns']
    sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_returns.std() > 0 else 0

    sell_trades = [t for t in trades if t['type'] == 'sell']
    n_trades = len(sell_trades)
    win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
    loss_trades = [t for t in sell_trades if t.get('pnl', 0) <= 0]
    win_rate = len(win_trades) / n_trades if n_trades > 0 else 0
    avg_win = np.mean([t['pnl'] for t in win_trades]) if win_trades else 0
    avg_loss = abs(np.mean([t['pnl'] for t in loss_trades])) if loss_trades else 1e-9
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    benchmark_total_return = (benchmark_equity.iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL
    benchmark_annual = (1 + benchmark_total_return) ** (1 / years) - 1 if years > 0 else 0
    benchmark_cummax = benchmark_equity.cummax()
    benchmark_drawdown = (benchmark_equity - benchmark_cummax) / benchmark_cummax
    benchmark_max_drawdown = benchmark_drawdown.min()
    benchmark_sharpe = (benchmark_returns.mean() / benchmark_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if benchmark_returns.std() > 0 else 0

    metrics = {
        'name': name,
        'ticker': ticker,
        'entry_period': ENTRY_PERIOD,
        'exit_period': EXIT_PERIOD,
        'atr_period': ATR_PERIOD,
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': round(equity_df['equity'].iloc[-1], 2),
        'total_return': round(total_return, 4),
        'total_return_pct': round(total_return * 100, 2),
        'annual_return': round(annual_return, 4),
        'annual_return_pct': round(annual_return * 100, 2),
        'max_drawdown': round(max_drawdown, 4),
        'max_drawdown_pct': round(max_drawdown * 100, 2),
        'sharpe_ratio': round(sharpe, 3),
        'total_trades': n_trades,
        'win_rate': round(win_rate, 4),
        'win_rate_pct': round(win_rate * 100, 2),
        'profit_loss_ratio': round(profit_loss_ratio, 3),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(-abs(np.mean([t['pnl'] for t in loss_trades])) if loss_trades else 0, 2),
        'benchmark': {
            'total_return': round(benchmark_total_return, 4),
            'total_return_pct': round(benchmark_total_return * 100, 2),
            'annual_return': round(benchmark_annual, 4),
            'annual_return_pct': round(benchmark_annual * 100, 2),
            'max_drawdown': round(benchmark_max_drawdown, 4),
            'max_drawdown_pct': round(benchmark_max_drawdown * 100, 2),
            'sharpe_ratio': round(benchmark_sharpe, 3)
        }
    }

    return metrics, equity_df, trades


def plot_asset(df, name, ticker, metrics, output_dir='turtle_charts'):
    """绘制股价、唐奇安通道、买卖信号图"""
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    ax1 = axes[0]
    ax1.plot(df['date'], df['close'], label='收盘价', color='#1f2937', linewidth=1.2)
    ax1.plot(df['date'], df['upper_channel'], label=f'上轨({ENTRY_PERIOD}日最高)', color='#2563eb', linewidth=1.5, linestyle='--')
    ax1.plot(df['date'], df['lower_channel'], label=f'下轨({EXIT_PERIOD}日最低)', color='#dc2626', linewidth=1.5, linestyle='--')

    buy_points = df.dropna(subset=['buy_signal'])
    sell_points = df.dropna(subset=['sell_signal'])
    ax1.scatter(buy_points['date'], buy_points['buy_signal'], marker='^', color='#16a34a', s=100, zorder=5, label='买入信号')
    ax1.scatter(sell_points['date'], sell_points['sell_signal'], marker='v', color='#dc2626', s=100, zorder=5, label='卖出信号')

    ax1.set_title(f'{name} ({ticker}) 海龟交易法策略', fontsize=14, fontweight='bold')
    ax1.set_ylabel('价格', fontsize=11)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    ax2 = axes[1]
    ax2.plot(df['date'], df['atr'], label=f'ATR({ATR_PERIOD})', color='#7c3aed', linewidth=1.5)
    ax2.fill_between(df['date'], 0, df['atr'], color='#7c3aed', alpha=0.15)
    ax2.set_ylabel('ATR', fontsize=11)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    textstr = (f"累计收益: {metrics['total_return_pct']}% | "
               f"年化收益: {metrics['annual_return_pct']}% | "
               f"最大回撤: {metrics['max_drawdown_pct']}% | "
               f"夏普: {metrics['sharpe_ratio']} | "
               f"交易次数: {metrics['total_trades']} | "
               f"胜率: {metrics['win_rate_pct']}%")
    fig.text(0.5, 0.02, textstr, ha='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='#eff6ff', edgecolor='#2563eb'))

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fname = os.path.join(output_dir, f'{ticker.replace(".", "_")}_turtle.png')
    plt.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close()
    return fname


def generate_html(output_path='turtle_strategy_report.html'):
    """生成交互式 HTML 报告"""
    with open('turtle_backtest_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    assets = data['assets']
    asset_data = []

    for m in assets:
        ticker = m['ticker']
        safe = ticker.replace('.', '_')
        chart_path = f'turtle_charts/{safe}_turtle.png'
        equity_path = f'turtle_signals/{safe}_equity.csv'
        trades_path = f'turtle_signals/{safe}_trades.csv'

        with open(chart_path, 'rb') as f:
            chart_b64 = base64.b64encode(f.read()).decode('utf-8')

        equity_df = pd.read_csv(equity_path)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        sample_n = min(len(equity_df), 200)
        equity_sample = equity_df.iloc[::max(1, len(equity_df) // sample_n)].copy()
        equity_dates = equity_sample['date'].dt.strftime('%Y-%m-%d').tolist()
        equity_values = [round(v, 2) for v in equity_sample['equity'].tolist()]

        trades_df = pd.read_csv(trades_path)
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        recent_trades = trades_df.tail(10).sort_values('date', ascending=False)
        trade_rows = []
        for _, t in recent_trades.iterrows():
            trade_rows.append({
                'date': t['date'].strftime('%Y-%m-%d'),
                'type': '买入' if t['type'] == 'buy' else '卖出',
                'price': round(t['price'], 3),
                'shares': int(t['shares']),
                'capital': round(t['capital_after'], 2)
            })

        asset_data.append({
            'name': m['name'],
            'ticker': ticker,
            'metrics': m,
            'chart_b64': chart_b64,
            'equity_dates': equity_dates,
            'equity_values': equity_values,
            'trades': trade_rows
        })

    tabs_html = '\n'.join([
        f'<button class="tab-btn" data-index="{i}" onclick="switchAsset({i})">{a["name"]}</button>'
        for i, a in enumerate(asset_data)
    ])

    js_data = json.dumps(asset_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>海龟交易法策略回测报告</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #fdfae7;
      --primary: #1e2bfa;
      --text: #111111;
      --text-muted: #6b6b6b;
      --text-light: #9a9a9a;
      --accent-light: rgba(30, 43, 250, 0.08);
      --accent-medium: rgba(30, 43, 250, 0.15);
      --border: rgba(30, 43, 250, 0.2);
      --card-bg: rgba(30, 43, 250, 0.04);
      --green: #059669;
      --red: #dc2626;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
      font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}
    h1, h2, h3, h4 {{
      font-family: 'Space Grotesk', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
      font-weight: 600;
      line-height: 1.1;
      letter-spacing: -0.02em;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1.5px solid var(--border);
    }}
    header h1 {{
      font-size: clamp(1.8rem, 4vw, 3rem);
      font-weight: 700;
      color: var(--text);
    }}
    header .subtitle {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 0.5rem;
      max-width: 520px;
    }}
    header .meta {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 0.8rem;
      color: var(--text-light);
      text-align: right;
    }}
    .tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      margin-bottom: 2rem;
    }}
    .tab-btn {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 0.95rem;
      font-weight: 600;
      padding: 0.7rem 1.4rem;
      border-radius: 100px;
      border: 1.5px solid var(--border);
      background: var(--bg);
      color: var(--primary);
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .tab-btn:hover, .tab-btn.active {{
      background: var(--primary);
      color: var(--bg);
      border-color: var(--primary);
    }}
    .section-title {{
      font-size: clamp(1.3rem, 2.2vw, 1.7rem);
      margin: 2rem 0 1rem;
      display: flex;
      align-items: center;
      gap: 0.7rem;
    }}
    .section-title::before {{
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      background: var(--primary);
      border-radius: 50%;
    }}
    .chart-card {{
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: 16px;
      padding: 1.2rem;
      overflow: hidden;
    }}
    .chart-card img {{
      width: 100%;
      height: auto;
      border-radius: 10px;
      display: block;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }}
    .metric-card {{
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: 14px;
      padding: 1.3rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .metric-card .metric-value {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: clamp(1.8rem, 3vw, 2.4rem);
      font-weight: 700;
      color: var(--primary);
      line-height: 1;
    }}
    .metric-card .metric-value.positive {{ color: var(--green); }}
    .metric-card .metric-value.negative {{ color: var(--red); }}
    .metric-card .metric-label {{
      font-size: 0.9rem;
      color: var(--text-muted);
      font-weight: 500;
    }}
    .benchmark {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      background: var(--accent-light);
      border: 1.5px solid var(--border);
      border-radius: 14px;
      padding: 1.3rem;
    }}
    .benchmark-item h4 {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }}
    .benchmark-item .big {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text);
    }}
    .benchmark-item .small {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .table-wrap {{
      overflow-x: auto;
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    th, td {{
      padding: 0.85rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 600;
      color: var(--text);
      background: var(--accent-light);
    }}
    tr:last-child td {{ border-bottom: none; }}
    .tag-buy {{ color: var(--green); font-weight: 600; }}
    .tag-sell {{ color: var(--red); font-weight: 600; }}
    .strategy-note {{
      margin-top: 2rem;
      padding: 1.2rem 1.5rem;
      border-left: 4px solid var(--primary);
      background: var(--accent-light);
      border-radius: 0 12px 12px 0;
      font-size: 0.9rem;
      color: var(--text-muted);
      line-height: 1.6;
    }}
    @media (max-width: 768px) {{
      header {{ flex-direction: column; align-items: flex-start; }}
      .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>海龟交易法策略回测报告</h1>
        <p class="subtitle">基于唐奇安通道与 ATR，对五只标的进行突破买入、跌破卖出的趋势跟踪策略分析。</p>
      </div>
      <div class="meta">
        <div>上轨周期：{ENTRY_PERIOD}日最高价</div>
        <div>下轨周期：{EXIT_PERIOD}日最低价</div>
        <div>ATR 周期：{ATR_PERIOD}日</div>
      </div>
    </header>

    <nav class="tabs">
      {tabs_html}
    </nav>

    <main id="report">
      <h2 class="section-title" id="chart-title">股价走势与交易信号</h2>
      <div class="chart-card">
        <img id="chart-img" src="" alt="海龟策略图">
      </div>

      <h2 class="section-title">策略绩效指标</h2>
      <div class="metrics-grid" id="metrics-grid"></div>

      <h2 class="section-title">策略 vs 买入持有</h2>
      <div class="benchmark" id="benchmark"></div>

      <h2 class="section-title">最近交易记录</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>日期</th><th>类型</th><th>成交价</th><th>股数</th><th>交易后权益</th></tr>
          </thead>
          <tbody id="trades-body"></tbody>
        </table>
      </div>

      <div class="strategy-note">
        <strong>策略说明：</strong>当收盘价突破过去 {ENTRY_PERIOD} 日最高价时产生买入信号（绿色箭头），跌破过去 {EXIT_PERIOD} 日最低价时产生卖出信号（红色箭头）。回测假设初始资金 100,000 元，手续费 0.03%，滑点 0.1%，每次信号触发时全仓买入或卖出。该策略仅供研究参考，不构成投资建议。
      </div>
    </main>
  </div>

  <script>
    const assets = {js_data};
    let currentIndex = 0;

    function formatPct(value) {{
      const sign = value >= 0 ? '+' : '';
      return sign + value.toFixed(2) + '%';
    }}

    function render(index) {{
      currentIndex = index;
      const a = assets[index];
      const m = a.metrics;

      document.querySelectorAll('.tab-btn').forEach((btn, i) => {{
        btn.classList.toggle('active', i === index);
      }});

      document.getElementById('chart-img').src = 'data:image/png;base64,' + a.chart_b64;
      document.getElementById('chart-title').textContent = a.name + ' (' + a.ticker + ') — 股价走势与交易信号';

      const metricsGrid = document.getElementById('metrics-grid');
      metricsGrid.innerHTML = `
        <div class="metric-card">
          <div class="metric-value ${{m.total_return >= 0 ? 'positive' : 'negative'}}">${{formatPct(m.total_return_pct)}}</div>
          <div class="metric-label">累计收益率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value ${{m.annual_return >= 0 ? 'positive' : 'negative'}}">${{formatPct(m.annual_return_pct)}}</div>
          <div class="metric-label">年化收益率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value negative">${{formatPct(m.max_drawdown_pct)}}</div>
          <div class="metric-label">最大回撤</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">${{m.sharpe_ratio}}</div>
          <div class="metric-label">夏普比率</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">${{m.total_trades}}</div>
          <div class="metric-label">交易次数</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">${{m.win_rate_pct.toFixed(2)}}%</div>
          <div class="metric-label">胜率</div>
        </div>
      `;

      const b = m.benchmark;
      document.getElementById('benchmark').innerHTML = `
        <div class="benchmark-item">
          <h4>策略累计收益</h4>
          <div class="big" style="color:${{m.total_return >= 0 ? 'var(--green)' : 'var(--red)'}}">${{formatPct(m.total_return_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>买入持有累计收益</h4>
          <div class="big" style="color:${{b.total_return >= 0 ? 'var(--green)' : 'var(--red)'}}">${{formatPct(b.total_return_pct)}}</div>
        </div>
        <div class="benchmark-item"><h4>策略年化</h4><div class="small">${{formatPct(m.annual_return_pct)}}</div></div>
        <div class="benchmark-item"><h4>基准年化</h4><div class="small">${{formatPct(b.annual_return_pct)}}</div></div>
        <div class="benchmark-item"><h4>策略最大回撤</h4><div class="small">${{formatPct(m.max_drawdown_pct)}}</div></div>
        <div class="benchmark-item"><h4>基准最大回撤</h4><div class="small">${{formatPct(b.max_drawdown_pct)}}</div></div>
        <div class="benchmark-item"><h4>策略夏普</h4><div class="small">${{m.sharpe_ratio}}</div></div>
        <div class="benchmark-item"><h4>基准夏普</h4><div class="small">${{b.sharpe_ratio}}</div></div>
      `;

      const tbody = document.getElementById('trades-body');
      if (a.trades.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">该标的在回测周期内无完整交易记录</td></tr>';
      }} else {{
        tbody.innerHTML = a.trades.map(t => `
          <tr>
            <td>${{t.date}}</td>
            <td class="${{t.type === '买入' ? 'tag-buy' : 'tag-sell'}}">${{t.type}}</td>
            <td>${{t.price.toFixed(3)}}</td>
            <td>${{t.shares}}</td>
            <td>${{t.capital.toLocaleString('zh-CN', {{minimumFractionDigits: 2}})}}</td>
          </tr>
        `).join('');
      }}
    }}

    function switchAsset(index) {{ render(index); }}
    render(0);
  </script>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Turtle HTML report saved to: {output_path}')


def main(html_output='turtle_strategy_report.html'):
    os.makedirs('turtle_signals', exist_ok=True)
    os.makedirs('turtle_charts', exist_ok=True)

    assets = load_data()
    all_metrics = []
    summary_records = []

    for asset in assets:
        name = asset['name']
        ticker = asset['ticker']
        df = asset['df']
        print(f'Processing {name} ({ticker})...')

        df = calculate_signals(df)
        metrics, equity_df, trades = backtest(df, name, ticker)
        all_metrics.append(metrics)
        summary_records.append({
            'name': name,
            'ticker': ticker,
            'data_points': len(df),
            'chart': plot_asset(df, name, ticker, metrics)
        })

        signal_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                       'upper_channel', 'lower_channel', 'atr', 'signal', 'position',
                       'buy_signal', 'sell_signal']
        df[signal_cols].to_csv(f'turtle_signals/{ticker.replace(".", "_")}_signals.csv', index=False)
        equity_df.to_csv(f'turtle_signals/{ticker.replace(".", "_")}_equity.csv', index=False)
        pd.DataFrame(trades).to_csv(f'turtle_signals/{ticker.replace(".", "_")}_trades.csv', index=False)

    with open('turtle_backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'entry_period': ENTRY_PERIOD,
            'exit_period': EXIT_PERIOD,
            'atr_period': ATR_PERIOD,
            'initial_capital': INITIAL_CAPITAL,
            'commission': COMMISSION,
            'slippage': SLIPPAGE,
            'assets': all_metrics
        }, f, ensure_ascii=False, indent=2)

    with open('turtle_html_assets.json', 'w', encoding='utf-8') as f:
        json.dump({
            'assets': summary_records,
            'metrics': all_metrics
        }, f, ensure_ascii=False, indent=2)

    generate_html(output_path=html_output)
    print('All done. Results saved to turtle_signals/, turtle_charts/, turtle_backtest_results.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='海龟交易法策略分析与回测')
    parser.add_argument('--html-output', default='turtle_strategy_report.html', help='HTML 报告输出路径')
    args = parser.parse_args()
    main(html_output=args.html_output)
