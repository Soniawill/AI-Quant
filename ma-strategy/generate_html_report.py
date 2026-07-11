#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 backtest_results.json 与图表生成交互式 HTML 报告
样式参考 beautiful-html-templates 的 blue-professional
"""
import os
import json
import base64
import pandas as pd
from datetime import datetime


def img_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def generate_html(output_path='MA交叉策略回测报告.html'):
    with open('backtest_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    assets = data['assets']

    # 读取每个标的的图表、权益曲线、交易明细
    asset_data = []
    for m in assets:
        ticker = m['ticker']
        safe = ticker.replace('.', '_')
        chart_path = f'charts/{safe}_ma_cross.png'
        equity_path = f'signals/{safe}_equity.csv'
        trades_path = f'signals/{safe}_trades.csv'

        chart_b64 = img_to_base64(chart_path)
        equity_df = pd.read_csv(equity_path)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        trades_df = pd.read_csv(trades_path)
        trades_df['date'] = pd.to_datetime(trades_df['date'])

        # 权益曲线数据点抽样，避免 HTML 过大
        sample_n = min(len(equity_df), 200)
        equity_sample = equity_df.iloc[::max(1, len(equity_df) // sample_n)].copy()
        equity_dates = equity_sample['date'].dt.strftime('%Y-%m-%d').tolist()
        equity_values = [round(v, 2) for v in equity_sample['equity'].tolist()]

        # 最近交易记录
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

    # 生成标签按钮 HTML
    tabs_html = '\n'.join([
        f'<button class="tab-btn" data-index="{i}" onclick="switchAsset({i})">{a["name"]}</button>'
        for i, a in enumerate(asset_data)
    ])

    # 把 asset_data 转成 JS 对象字符串
    js_data = json.dumps(asset_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MA5/MA15 交叉策略回测报告</title>
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
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}
    h1, h2, h3, h4 {{
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 600;
      line-height: 1.1;
      letter-spacing: -0.02em;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }}

    /* Header */
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

    /* Tabs */
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

    /* Section title */
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

    /* Chart card */
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

    /* Metrics grid */
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

    /* Benchmark */
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

    /* Trades table */
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

    /* Strategy note */
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
        <h1>MA5 / MA15 交叉策略回测报告</h1>
        <p class="subtitle">基于同花顺/Tushare/akshare 数据源，对五只标的进行短周期均线交叉策略分析、信号标注与模拟交易回测。</p>
      </div>
      <div class="meta">
        <div>数据区间：2023-07-01 至 2026-07-10</div>
        <div>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        <div>策略：金叉买入 · 死叉卖出 · 全仓交易</div>
      </div>
    </header>

    <nav class="tabs">
      {tabs_html}
    </nav>

    <main id="report">
      <h2 class="section-title" id="chart-title">股价走势与交易信号</h2>
      <div class="chart-card">
        <img id="chart-img" src="" alt="MA交叉策略图">
      </div>

      <h2 class="section-title">策略绩效指标</h2>
      <div class="metrics-grid" id="metrics-grid">
        <!-- JS 填充 -->
      </div>

      <h2 class="section-title">策略 vs 买入持有</h2>
      <div class="benchmark" id="benchmark">
        <!-- JS 填充 -->
      </div>

      <h2 class="section-title">最近交易记录</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>类型</th>
              <th>成交价</th>
              <th>股数</th>
              <th>交易后权益</th>
            </tr>
          </thead>
          <tbody id="trades-body">
            <!-- JS 填充 -->
          </tbody>
        </table>
      </div>

      <div class="strategy-note">
        <strong>策略说明：</strong>当 MA5 上穿 MA15 时产生买入信号（绿色箭头），MA5 下穿 MA15 时产生卖出信号（红色箭头）。回测假设初始资金 100,000 元，手续费 0.03%，滑点 0.1%，每次信号触发时全仓买入或卖出。该策略仅供研究参考，不构成投资建议。
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

      // Tabs
      document.querySelectorAll('.tab-btn').forEach((btn, i) => {{
        btn.classList.toggle('active', i === index);
      }});

      // Chart
      document.getElementById('chart-img').src = 'data:image/png;base64,' + a.chart_b64;
      document.getElementById('chart-title').textContent = a.name + ' (' + a.ticker + ') — 股价走势与交易信号';

      // Metrics
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

      // Benchmark
      const b = m.benchmark;
      document.getElementById('benchmark').innerHTML = `
        <div class="benchmark-item">
          <h4>策略累计收益</h4>
          <div class="big ${{m.total_return >= 0 ? 'positive' : 'negative'}}" style="color:${{m.total_return >= 0 ? 'var(--green)' : 'var(--red)'}}">${{formatPct(m.total_return_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>买入持有累计收益</h4>
          <div class="big ${{b.total_return >= 0 ? 'positive' : 'negative'}}" style="color:${{b.total_return >= 0 ? 'var(--green)' : 'var(--red)'}}">${{formatPct(b.total_return_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>策略年化</h4>
          <div class="small">${{formatPct(m.annual_return_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>基准年化</h4>
          <div class="small">${{formatPct(b.annual_return_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>策略最大回撤</h4>
          <div class="small">${{formatPct(m.max_drawdown_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>基准最大回撤</h4>
          <div class="small">${{formatPct(b.max_drawdown_pct)}}</div>
        </div>
        <div class="benchmark-item">
          <h4>策略夏普</h4>
          <div class="small">${{m.sharpe_ratio}}</div>
        </div>
        <div class="benchmark-item">
          <h4>基准夏普</h4>
          <div class="small">${{b.sharpe_ratio}}</div>
        </div>
      `;

      // Trades
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

    function switchAsset(index) {{
      render(index);
    }}

    // 初始化
    render(0);
  </script>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'HTML report saved to: {output_path}')


if __name__ == '__main__':
    generate_html()
