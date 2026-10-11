#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
indicators.py — ak-technical-indicators 技能内置指标计算脚本（纯 pandas/numpy，可离线运行）

口径与 SKILL.md 完全一致：
- SMA: rolling mean, min_periods=窗口
- EMA: ewm(span, adjust=False)
- MACD: 12/26/9, A股惯例 hist=2*(DIF-DEA)
- RSI: Wilder 平滑 ewm(alpha=1/n, adjust=False)
- BOLL: SMA20 ± 2×std(ddof=0)
- KDJ: 中国式 SMA 平滑 ewm(alpha=1/3)
- ATR: TR 的 Wilder 平滑
- ROC / 滚动年化波动率

用法：
    python3 indicators.py --input kline.csv --output out.csv \
        [--indicators ma,ema,macd,rsi,boll,kdj,atr,roc,vol] \
        [--ma-periods 5,10,20,60] [--ema-periods 12,26] [--rsi-period 14] \
        [--boll-period 20 --boll-k 2] [--kdj-period 9] [--atr-period 14] \
        [--roc-period 12] [--vol-period 20]
"""

import argparse
import sys

import numpy as np
import pandas as pd

CN2EN = {
    "日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
    "成交量": "volume", "开盘价": "open", "收盘价": "close", "最高价": "high", "最低价": "low",
}


def load_ohlcv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={k: v for k, v in CN2EN.items() if k in df.columns})
    need = ["high", "low", "close"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise ValueError(f"缺少必要列 {miss}；现有列: {df.columns.tolist()}")
    if "date" in df.columns:
        df["date"] = df["date"].astype(str)
        df = df.sort_values("date").reset_index(drop=True)
    return df


def wilder(s: pd.Series, n: int) -> pd.Series:
    """Wilder 平滑 = ewm(alpha=1/n, adjust=False)"""
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def add_ma(df, periods):
    for n in periods:
        df[f"ma_{n}"] = df["close"].rolling(n, min_periods=n).mean()
    return df


def add_ema(df, periods):
    for n in periods:
        df[f"ema_{n}"] = df["close"].ewm(span=n, adjust=False).mean()
    return df


def add_macd(df, fast=12, slow=26, sig=9):
    ema_f = df["close"].ewm(span=fast, adjust=False).mean()
    ema_s = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd_dif"] = ema_f - ema_s
    df["macd_dea"] = df["macd_dif"].ewm(span=sig, adjust=False).mean()
    df["macd_hist"] = 2.0 * (df["macd_dif"] - df["macd_dea"])  # A股软件惯例 ×2
    return df


def add_rsi(df, n=14):
    diff = df["close"].diff()
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)
    avg_up = wilder(up, n)
    avg_dn = wilder(down, n)
    rs = avg_up / avg_dn.replace(0.0, np.nan)
    df[f"rsi_{n}"] = 100.0 - 100.0 / (1.0 + rs)
    return df


def add_boll(df, n=20, k=2.0):
    mid = df["close"].rolling(n, min_periods=n).mean()
    sd = df["close"].rolling(n, min_periods=n).std(ddof=0)  # 总体标准差，与通达信一致
    df["boll_mid"] = mid
    df["boll_up"] = mid + k * sd
    df["boll_low"] = mid - k * sd
    return df


def add_kdj(df, n=9):
    low_n = df["low"].rolling(n, min_periods=n).min()
    high_n = df["high"].rolling(n, min_periods=n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n).replace(0.0, np.nan) * 100.0
    k = rsv.ewm(alpha=1.0 / 3, adjust=False).mean()          # 中国式 SMA(Y=(X+2Y')/3)
    d = k.ewm(alpha=1.0 / 3, adjust=False).mean()
    df["kdj_k"], df["kdj_d"], df["kdj_j"] = k, d, 3.0 * k - 2.0 * d
    return df


def add_atr(df, n=14):
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df[f"atr_{n}"] = wilder(tr, n)
    return df


def add_roc(df, n=12):
    df[f"roc_{n}"] = df["close"] / df["close"].shift(n) - 1.0
    return df


def add_vol(df, n=20):
    ret = df["close"].pct_change()
    df[f"vol_{n}"] = ret.rolling(n, min_periods=n).std(ddof=0) * np.sqrt(252.0)
    return df


WARMUP = {"ma": "max(窗口)", "ema": "~3×窗口后稳定", "macd": "≈ slow+sig", "rsi": "n",
          "boll": "n", "kdj": "n", "atr": "n", "roc": "n", "vol": "n"}


def main() -> int:
    p = argparse.ArgumentParser(description="技术指标计算（统一口径）")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--indicators", default="ma,ema,macd,rsi,boll,kdj,atr,roc,vol")
    p.add_argument("--ma-periods", default="5,10,20,60")
    p.add_argument("--ema-periods", default="12,26")
    p.add_argument("--rsi-period", type=int, default=14)
    p.add_argument("--boll-period", type=int, default=20)
    p.add_argument("--boll-k", type=float, default=2.0)
    p.add_argument("--kdj-period", type=int, default=9)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--roc-period", type=int, default=12)
    p.add_argument("--vol-period", type=int, default=20)
    a = p.parse_args()

    df = load_ohlcv(a.input)
    want = [x.strip() for x in a.indicators.split(",") if x.strip()]
    unknown = [x for x in want if x not in WARMUP]
    if unknown:
        print(f"[error] 未知指标: {unknown}（可用: {list(WARMUP)}）", file=sys.stderr)
        return 2

    ma_p = [int(x) for x in a.ma_periods.split(",")]
    ema_p = [int(x) for x in a.ema_periods.split(",")]

    if "ma" in want:
        df = add_ma(df, ma_p)
    if "ema" in want:
        df = add_ema(df, ema_p)
    if "macd" in want:
        df = add_macd(df)
    if "rsi" in want:
        df = add_rsi(df, a.rsi_period)
    if "boll" in want:
        df = add_boll(df, a.boll_period, a.boll_k)
    if "kdj" in want:
        df = add_kdj(df, a.kdj_period)
    if "atr" in want:
        df = add_atr(df, a.atr_period)
    if "roc" in want:
        df = add_roc(df, a.roc_period)
    if "vol" in want:
        df = add_vol(df, a.vol_period)

    out = df.copy()
    out.to_csv(a.output, index=False, encoding="utf-8-sig")

    print(f"[ok] 已保存 {a.output}  shape={df.shape}")
    print("指标身份证:")
    print(f"  - 输入: {a.input}")
    print(f"  - 口径: qfq前提未校验，请确认输入为前复权数据（SKILL.md §2）")
    print(f"  - 指标: {want}  参数: MA{ma_p} EMA{ema_p} RSI{a.rsi_period} "
          f"BOLL({a.boll_period},{a.boll_k}) KDJ{a.kdj_period} ATR{a.atr_period}")
    print(f"  - 热身期: {WARMUP}；前置 NaN 为正常现象，禁止静默 dropna 混入下游")
    tail_cols = [c for c in df.columns if c.split("_")[0] in WARMUP or c in ("date", "close")]
    print("\n末行快照:")
    print(df[tail_cols].tail(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
