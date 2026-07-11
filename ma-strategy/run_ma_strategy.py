#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MA 交叉策略分析与回测
- 标的：香农芯创、立讯精密、工业富联、积存金(AU9999.SGE)、通信ETF(515880.SH)
- 短均线窗口：5，长均线窗口：15
- 金叉买入，死叉卖出
- 输出：signals CSV、回测指标 JSON、可视化图表
"""
import os
import json
import glob
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import tushare as ts
import akshare as ak

# 中文显示
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'PingFang SC', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

SHORT_WINDOW = 5
LONG_WINDOW = 15
INITIAL_CAPITAL = 100000.0
COMMISSION = 0.0003
SLIPPAGE = 0.001
TRADING_DAYS_PER_YEAR = 252


def get_tushare_token():
    """优先从环境变量读取 Tushare token，其次从 mcp_config.json 读取"""
    token = os.environ.get('TUSHARE_TOKEN')
    if token:
        return token
    if os.path.exists('mcp_config.json'):
        try:
            with open('mcp_config.json', 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            url = cfg['mcpServers']['tushareMcp']['url']
            token = url.split('token=')[-1]
            return token
        except Exception:
            pass
    raise ValueError('未找到 Tushare token：请设置环境变量 TUSHARE_TOKEN 或保留 mcp_config.json（且勿提交到 GitHub）')


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


def fetch_data(data_dir='data'):
    """从网络获取最新日线数据并保存到 data/ 目录"""
    os.makedirs(data_dir, exist_ok=True)
    token = get_tushare_token()
    ts.set_token(token)
    pro = ts.pro_api()

    assets = [
        {'name': '香农芯创', 'ticker': '300475.SZ', 'source': 'tushare'},
        {'name': '立讯精密', 'ticker': '002475.SZ', 'source': 'tushare'},
        {'name': '工业富联', 'ticker': '601138.SH', 'source': 'tushare'},
        {'name': '积存金', 'ticker': 'AU9999.SGE', 'source': 'akshare_gold'},
        {'name': '通信ETF', 'ticker': '515880.SH', 'source': 'akshare_etf'},
    ]

    end_date = pd.Timestamp.now().strftime('%Y%m%d')
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=365 * 3)).strftime('%Y%m%d')

    for asset in assets:
        ticker = asset['ticker']
        name = asset['name']
        print(f'Fetching {name} ({ticker})...')

        try:
            if asset['source'] == 'tushare':
                df = pro.daily(ts_code=ticker, start_date=start_date, end_date=end_date)
                df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
                df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                df['date'] = pd.to_datetime(df['date'])
            elif asset['source'] == 'akshare_gold':
                df = ak.spot_hist_sge(symbol='Au99.99')
                df = df[['date', 'open', 'close', 'low', 'high']]
                df = df.rename(columns={'close': 'close'})
                df['date'] = pd.to_datetime(df['date'])
                df['volume'] = 0
                df['amount'] = 0
            elif asset['source'] == 'akshare_etf':
                df = ak.fund_etf_hist_sina(symbol='sh515880')
                df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                df['date'] = pd.to_datetime(df['date'])

            df = df.sort_values('date').reset_index(drop=True)
            df['name'] = name
            df['ticker'] = ticker
            df = df[df['date'] >= '2023-07-01'].copy()

            fname = os.path.join(data_dir, f'{ticker.replace(".", "_")}_daily.csv')
            df.to_csv(fname, index=False)
            print(f'  Saved {fname}: {len(df)} rows')
        except Exception as e:
            print(f'  ERROR fetching {name} ({ticker}): {e}')
            raise


def calculate_signals(df):
    """计算 MA5、MA15 和买卖信号"""
    df = df.copy()
    df['ma_short'] = df['close'].rolling(window=SHORT_WINDOW, min_periods=SHORT_WINDOW).mean()
    df['ma_long'] = df['close'].rolling(window=LONG_WINDOW, min_periods=LONG_WINDOW).mean()

    # 金叉 / 死叉
    df['signal'] = 0
    df.loc[df.index[SHORT_WINDOW:], 'signal'] = np.where(
        df['ma_short'].iloc[SHORT_WINDOW:] > df['ma_long'].iloc[SHORT_WINDOW:], 1, -1
    )
    df['signal_change'] = df['signal'].diff()

    df['buy_signal'] = np.where(df['signal_change'] == 2, df['close'], np.nan)
    df['sell_signal'] = np.where(df['signal_change'] == -2, df['close'], np.nan)

    # 持仓状态：1 持仓，0 空仓
    df['position'] = 0
    position = 0
    positions = []
    for _, row in df.iterrows():
        if row['signal_change'] == 2:
            position = 1
        elif row['signal_change'] == -2:
            position = 0
        positions.append(position)
    df['position'] = positions

    return df


def backtest(df, name, ticker):
    """根据信号进行模拟交易回测"""
    capital = INITIAL_CAPITAL
    position = 0
    shares = 0
    trades = []
    equity_curve = []
    buy_price = None

    for _, row in df.iterrows():
        price = row['close']
        date = row['date']

        if row['signal_change'] == 2 and position == 0:
            # 买入（含滑点和手续费）
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
        elif row['signal_change'] == -2 and position == 1:
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

        # 当日权益
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

    # 最大回撤
    cummax = equity_df['equity'].cummax()
    drawdown = (equity_df['equity'] - cummax) / cummax
    max_drawdown = drawdown.min()

    # 夏普比率（假设无风险利率为0）
    daily_returns = equity_df['returns']
    sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if daily_returns.std() > 0 else 0

    # 交易统计
    sell_trades = [t for t in trades if t['type'] == 'sell']
    n_trades = len(sell_trades)
    win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
    loss_trades = [t for t in sell_trades if t.get('pnl', 0) <= 0]
    win_rate = len(win_trades) / n_trades if n_trades > 0 else 0
    avg_win = np.mean([t['pnl'] for t in win_trades]) if win_trades else 0
    avg_loss = abs(np.mean([t['pnl'] for t in loss_trades])) if loss_trades else 1e-9
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    # 基准指标
    benchmark_total_return = (benchmark_equity.iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL
    benchmark_annual = (1 + benchmark_total_return) ** (1 / years) - 1 if years > 0 else 0
    benchmark_cummax = benchmark_equity.cummax()
    benchmark_drawdown = (benchmark_equity - benchmark_cummax) / benchmark_cummax
    benchmark_max_drawdown = benchmark_drawdown.min()
    benchmark_sharpe = (benchmark_returns.mean() / benchmark_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)) if benchmark_returns.std() > 0 else 0

    metrics = {
        'name': name,
        'ticker': ticker,
        'short_window': SHORT_WINDOW,
        'long_window': LONG_WINDOW,
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


def plot_asset(df, name, ticker, metrics, output_dir='charts'):
    """绘制股价、长短均线、买卖信号图"""
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # 子图1：价格 + 均线 + 信号
    ax1 = axes[0]
    ax1.plot(df['date'], df['close'], label='收盘价', color='#1f2937', linewidth=1.2)
    ax1.plot(df['date'], df['ma_short'], label=f'MA{SHORT_WINDOW}', color='#2563eb', linewidth=1.5)
    ax1.plot(df['date'], df['ma_long'], label=f'MA{LONG_WINDOW}', color='#dc2626', linewidth=1.5)

    buy_points = df.dropna(subset=['buy_signal'])
    sell_points = df.dropna(subset=['sell_signal'])
    ax1.scatter(buy_points['date'], buy_points['buy_signal'], marker='^', color='#16a34a', s=100, zorder=5, label='买入信号')
    ax1.scatter(sell_points['date'], sell_points['sell_signal'], marker='v', color='#dc2626', s=100, zorder=5, label='卖出信号')

    ax1.set_title(f'{name} ({ticker}) MA{SHORT_WINDOW}/MA{LONG_WINDOW} 交叉策略', fontsize=14, fontweight='bold')
    ax1.set_ylabel('价格', fontsize=11)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # 子图2：持仓状态
    ax2 = axes[1]
    ax2.fill_between(df['date'], 0, df['position'], color='#3b82f6', alpha=0.3, step='post')
    ax2.set_ylabel('持仓状态', fontsize=11)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['空仓', '持仓'])
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # 添加关键指标文本
    textstr = (f"累计收益: {metrics['total_return_pct']}% | "
               f"年化收益: {metrics['annual_return_pct']}% | "
               f"最大回撤: {metrics['max_drawdown_pct']}% | "
               f"夏普: {metrics['sharpe_ratio']} | "
               f"交易次数: {metrics['total_trades']} | "
               f"胜率: {metrics['win_rate_pct']}%")
    fig.text(0.5, 0.02, textstr, ha='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='#eff6ff', edgecolor='#2563eb'))

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fname = os.path.join(output_dir, f'{ticker.replace(".", "_")}_ma_cross.png')
    plt.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close()
    return fname


def main(refresh_data=False, html_output='MA交叉策略回测报告.html'):
    os.makedirs('signals', exist_ok=True)
    os.makedirs('charts', exist_ok=True)

    if refresh_data:
        fetch_data()

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

        # 保存信号表
        signal_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                       'ma_short', 'ma_long', 'signal', 'position',
                       'buy_signal', 'sell_signal', 'name', 'ticker']
        df[signal_cols].to_csv(f'signals/{ticker.replace(".", "_")}_signals.csv', index=False)

        # 保存权益曲线
        equity_df.to_csv(f'signals/{ticker.replace(".", "_")}_equity.csv', index=False)

        # 保存交易记录
        pd.DataFrame(trades).to_csv(f'signals/{ticker.replace(".", "_")}_trades.csv', index=False)

    # 保存汇总指标
    with open('backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'short_window': SHORT_WINDOW,
            'long_window': LONG_WINDOW,
            'initial_capital': INITIAL_CAPITAL,
            'commission': COMMISSION,
            'slippage': SLIPPAGE,
            'assets': all_metrics
        }, f, ensure_ascii=False, indent=2)

    # 保存用于 HTML 渲染的轻量摘要
    with open('html_assets.json', 'w', encoding='utf-8') as f:
        json.dump({
            'assets': summary_records,
            'metrics': all_metrics
        }, f, ensure_ascii=False, indent=2)

    print('All done. Results saved to signals/, charts/, backtest_results.json, html_assets.json')

    # 生成 HTML 报告
    from generate_html_report import generate_html
    generate_html(output_path=html_output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MA 交叉策略分析与回测')
    parser.add_argument('--refresh-data', action='store_true', help='重新从网络获取行情数据')
    parser.add_argument('--html-output', default='MA交叉策略回测报告.html', help='HTML 报告输出路径')
    args = parser.parse_args()
    main(refresh_data=args.refresh_data, html_output=args.html_output)
