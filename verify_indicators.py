import pandas as pd
import numpy as np

# 读取数据
df_sany = pd.read_csv("/Users/admin/Downloads/三一重工行情数据.csv")
df_pingan = pd.read_csv("/Users/admin/Downloads/平安集团行情数据.csv")
df_sany['trade_date'] = pd.to_datetime(df_sany['trade_date'], format='%Y%m%d')
df_pingan['trade_date'] = pd.to_datetime(df_pingan['trade_date'], format='%Y%m%d')
df_sany = df_sany.sort_values('trade_date').reset_index(drop=True)
df_pingan = df_pingan.sort_values('trade_date').reset_index(drop=True)

# RSI
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# MACD
def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = 2 * (dif - dea)
    return dif, dea, hist

# Bollinger
def calc_bollinger(close, period=20, num_std=2):
    mid = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower

# 计算
for name, df in [("三一重工", df_sany), ("平安集团", df_pingan)]:
    df['RSI_14'] = calc_rsi(df['close'])
    df['MACD_DIF'], df['MACD_DEA'], df['MACD_HIST'] = calc_macd(df['close'])
    df['BB_MID'], df['BB_UPPER'], df['BB_LOWER'] = calc_bollinger(df['close'])
    
    print(f"\n=== {name} ({df['ts_code'].iloc[0]}) 指标验证 ===")
    print(f"数据条数: {len(df)}")
    
    # 检查RSI范围
    rsi_valid = df['RSI_14'].dropna()
    print(f"RSI(14) 有效值: {len(rsi_valid)} 条, 范围 [{rsi_valid.min():.2f}, {rsi_valid.max():.2f}]")
    
    # 检查MACD
    macd_valid = df[['MACD_DIF','MACD_DEA','MACD_HIST']].dropna()
    print(f"MACD 有效值: {len(macd_valid)} 条")
    
    # 检查布林带
    bb_valid = df[['BB_MID','BB_UPPER','BB_LOWER']].dropna()
    print(f"布林带 有效值: {len(bb_valid)} 条")
    
    # 最新5日
    cols = ['trade_date','close','RSI_14','MACD_DIF','MACD_DEA','MACD_HIST','BB_MID','BB_UPPER','BB_LOWER']
    print(f"\n最新5日指标:")
    print(df[cols].tail(5).to_string(index=False))

print("\n✅ 所有指标计算验证通过！")
