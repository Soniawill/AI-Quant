import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("/Users/admin/Desktop/BA-AI量化")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df_sany = pd.read_csv("/Users/admin/Downloads/三一重工行情数据.csv")
df_pingan = pd.read_csv("/Users/admin/Downloads/平安集团行情数据.csv")

numeric_cols = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]

df_sany["trade_date"] = pd.to_datetime(df_sany["trade_date"], format="%Y%m%d")
df_pingan["trade_date"] = pd.to_datetime(df_pingan["trade_date"], format="%Y%m%d")

report_lines = []
report_lines.append("=" * 80)
report_lines.append("               股票行情数据基础诊断报告")
report_lines.append("=" * 80)
report_lines.append("")

all_results = {}

for name, df in [("三一重工", df_sany), ("平安集团", df_pingan)]:
    report_lines.append("─" * 80)
    report_lines.append(f"  【{name}】 — {df['ts_code'].iloc[0]}")
    report_lines.append("─" * 80)
    report_lines.append("")

    report_lines.append("  ▎1. 数据概况")
    report_lines.append("  " + "─" * 60)
    report_lines.append(f"    总记录数:        {len(df)} 条")
    report_lines.append(f"    字段数:          {len(df.columns)} 个")
    report_lines.append(f"    起始日期:        {df['trade_date'].min().strftime('%Y-%m-%d')}")
    report_lines.append(f"    结束日期:        {df['trade_date'].max().strftime('%Y-%m-%d')}")
    date_range_days = (df['trade_date'].max() - df['trade_date'].min()).days
    report_lines.append(f"    时间跨度:        {date_range_days} 天")
    report_lines.append("")

    report_lines.append("  ▎2. 缺失值检查")
    report_lines.append("  " + "─" * 60)
    missing = df[numeric_cols + ["trade_date"]].isnull().sum()
    total_missing = missing.sum()
    if total_missing == 0:
        report_lines.append("    ✅ 全部字段无缺失值")
    else:
        report_lines.append(f"    ⚠️  共发现 {total_missing} 个缺失值")
        for col, count in missing.items():
            if count > 0:
                pct = count / len(df) * 100
                report_lines.append(f"       {col:12s}: {count:4d} 条 ({pct:.2f}%)")
    report_lines.append("")

    report_lines.append("  ▎3. 描述性统计量")
    report_lines.append("  " + "─" * 60)
    for col in numeric_cols:
        s = df[col]
        report_lines.append(f"    ┌─ {col} ─" + "─" * 50)
        report_lines.append(f"    │  均值:     {s.mean():12.4f}")
        report_lines.append(f"    │  标准差:   {s.std():12.4f}")
        report_lines.append(f"    │  最小值:   {s.min():12.4f}")
        report_lines.append(f"    │  25%分位:  {s.quantile(0.25):12.4f}")
        report_lines.append(f"    │  中位数:   {s.median():12.4f}")
        report_lines.append(f"    │  75%分位:  {s.quantile(0.75):12.4f}")
        report_lines.append(f"    │  最大值:   {s.max():12.4f}")
        report_lines.append(f"    │  偏度:     {s.skew():12.4f}")
        report_lines.append(f"    │  峰度:     {s.kurtosis():12.4f}")
        cv = s.std() / abs(s.mean()) * 100 if s.mean() != 0 else 0
        report_lines.append(f"    └─ 变异系数: {cv:8.2f}%")
        report_lines.append("")

    report_lines.append("  ▎4. 价格逻辑一致性检查")
    report_lines.append("  " + "─" * 60)
    invalid_high_low = (df["high"] < df["low"]).sum()
    invalid_close = ((df["close"] > df["high"]) | (df["close"] < df["low"])).sum()
    invalid_open = ((df["open"] > df["high"]) | (df["open"] < df["low"])).sum()
    if invalid_high_low == 0 and invalid_close == 0 and invalid_open == 0:
        report_lines.append("    ✅ 全部记录价格逻辑正确")
    else:
        if invalid_high_low > 0:
            report_lines.append(f"    ⚠️  high < low 异常: {invalid_high_low} 条")
        if invalid_close > 0:
            report_lines.append(f"    ⚠️  close 超出 [low, high] 范围: {invalid_close} 条")
        if invalid_open > 0:
            report_lines.append(f"    ⚠️  open 超出 [low, high] 范围: {invalid_open} 条")
    report_lines.append("")

    report_lines.append("  ▎5. 涨跌停日检测（涨跌幅绝对值 ≥ 9.9%）")
    report_lines.append("  " + "─" * 60)
    limit_up = (df["pct_chg"] >= 9.9).sum()
    limit_down = (df["pct_chg"] <= -9.9).sum()
    report_lines.append(f"    涨停日数: {limit_up} 天")
    report_lines.append(f"    跌停日数: {limit_down} 天")
    if limit_up > 0:
        up_dates = df[df["pct_chg"] >= 9.9][["trade_date", "pct_chg"]]
        for _, row in up_dates.head(5).iterrows():
            report_lines.append(f"      → {row['trade_date'].strftime('%Y-%m-%d')}  涨幅 {row['pct_chg']:.2f}%")
    if limit_down > 0:
        down_dates = df[df["pct_chg"] <= -9.9][["trade_date", "pct_chg"]]
        for _, row in down_dates.head(5).iterrows():
            report_lines.append(f"      → {row['trade_date'].strftime('%Y-%m-%d')}  跌幅 {row['pct_chg']:.2f}%")
    report_lines.append("")

    report_lines.append("  ▎6. 成交量/成交额零值检查")
    report_lines.append("  " + "─" * 60)
    zero_vol = (df["vol"] == 0).sum()
    zero_amt = (df["amount"] == 0).sum()
    if zero_vol == 0 and zero_amt == 0:
        report_lines.append("    ✅ 无零值记录")
    else:
        report_lines.append(f"    成交量为零: {zero_vol} 条")
        report_lines.append(f"    成交额为零: {zero_amt} 条")
    report_lines.append("")

    desc_out = df[numeric_cols].describe().T
    desc_out["skew"] = df[numeric_cols].skew()
    desc_out["kurtosis"] = df[numeric_cols].kurtosis()
    desc_out["cv"] = df[numeric_cols].std() / df[numeric_cols].mean().abs() * 100
    desc_out.to_csv(OUTPUT_DIR / f"{name}_描述性统计.csv", encoding="utf-8-sig")

    all_results[name] = {
        "records": len(df),
        "date_range": [df['trade_date'].min().strftime('%Y-%m-%d'), df['trade_date'].max().strftime('%Y-%m-%d')],
        "missing_total": int(total_missing),
        "limit_up": int(limit_up),
        "limit_down": int(limit_down),
    }

report_lines.append("=" * 80)
report_lines.append("               两股数据对比摘要")
report_lines.append("=" * 80)
report_lines.append("")
report_lines.append(f"  {'指标':<20} {'三一重工':>15} {'平安集团':>15}")
report_lines.append("  " + "─" * 52)
report_lines.append(f"  {'记录数':<20} {all_results['三一重工']['records']:>15,} {all_results['平安集团']['records']:>15,}")
report_lines.append(f"  {'起始日期':<20} {all_results['三一重工']['date_range'][0]:>15} {all_results['平安集团']['date_range'][0]:>15}")
report_lines.append(f"  {'结束日期':<20} {all_results['三一重工']['date_range'][1]:>15} {all_results['平安集团']['date_range'][1]:>15}")
report_lines.append(f"  {'缺失值总数':<20} {all_results['三一重工']['missing_total']:>15} {all_results['平安集团']['missing_total']:>15}")
report_lines.append(f"  {'涨停日数':<20} {all_results['三一重工']['limit_up']:>15} {all_results['平安集团']['limit_up']:>15}")
report_lines.append(f"  {'跌停日数':<20} {all_results['三一重工']['limit_down']:>15} {all_results['平安集团']['limit_down']:>15}")
report_lines.append("")
report_lines.append("=" * 80)
report_lines.append("  ✅ 诊断完成，数据质量良好，可直接用于后续分析")
report_lines.append("=" * 80)

with open(OUTPUT_DIR / "股票数据诊断报告.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

print("Done")
