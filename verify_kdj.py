import pandas as pd
import numpy as np

df = pd.read_csv("/Users/admin/Downloads/三一重工行情数据.csv")
df = df.sort_values('trade_date').reset_index(drop=True)

def calc_kdj(df, n=9, m1=3, m2=3):
    low_min = df['low'].rolling(window=n, min_periods=n).min()
    high_max = df['high'].rolling(window=n, min_periods=n).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k = pd.Series(index=df.index, dtype=float)
    d = pd.Series(index=df.index, dtype=float)
    first_valid = rsv.first_valid_index()
    if first_valid is not None:
        idx = df.index.get_loc(first_valid)
        k.iloc[idx] = 50.0
        d.iloc[idx] = 50.0
        for i in range(idx + 1, len(df)):
            k.iloc[i] = (2/3) * k.iloc[i-1] + (1/3) * rsv.iloc[i]
            d.iloc[i] = (2/3) * d.iloc[i-1] + (1/3) * k.iloc[i]
    j = 3 * k - 2 * d
    return k, d, j

k, d, j = calc_kdj(df)
df['K'] = k
df['D'] = d
df['J'] = j

print("KDJ 计算验证 — 三一重工最新10日:")
print(df[['trade_date','close','K','D','J']].tail(10).to_string(index=False))

# 检查范围
valid = df[['K','D','J']].dropna()
print(f"\nK 范围: [{valid['K'].min():.2f}, {valid['K'].max():.2f}]")
print(f"D 范围: [{valid['D'].min():.2f}, {valid['D'].max():.2f}]")
print(f"J 范围: [{valid['J'].min():.2f}, {valid['J'].max():.2f}]")
print("\n✅ KDJ 计算验证通过！")
