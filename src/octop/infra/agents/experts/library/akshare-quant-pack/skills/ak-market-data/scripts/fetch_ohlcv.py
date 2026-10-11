#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_ohlcv.py — ak-market-data 技能内置统一取数脚本

支持四类标的：A股个股(stock) / 指数(index) / 期货主力连续(futures_main) / 期货具体合约(futures_contract)
功能：自动重试、中文列名映射为英文标准列名、基础质检、数据身份证打印、CSV 落盘。

用法示例：
    python3 fetch_ohlcv.py --kind stock --symbol 000001 --start 20230101 --end 20251231 \
        --adjust qfq --out ~/quant-data/raw/000001_daily.csv
    python3 fetch_ohlcv.py --kind futures_main --symbol RB0 --out rb_main.csv
"""

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

# 中 -> 英 标准列名映射（接口未返回的字段自动忽略；新增字段保留原名并提示）
STOCK_MAP = {
    "日期": "date", "股票代码": "symbol", "开盘": "open", "收盘": "close",
    "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount",
    "振幅": "amplitude", "涨跌幅": "pct_chg", "涨跌额": "chg", "换手率": "turnover",
}
FUT_MAP = {
    "日期": "date", "开盘价": "open", "收盘价": "close", "最高价": "high",
    "最低价": "low", "成交量": "volume", "持仓量": "open_interest",
    "动态结算价": "settle", "结算价": "settle",
}


def rename_std(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    unmapped = [c for c in df.columns if c not in mapping]
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    if unmapped:
        print(f"[warn] 未映射字段（保留原名）: {unmapped}")
    return df


def with_retry(fn, retries: int = 3, pause: float = 2.0):
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 —— 取数层需要把所有上游异常兜住后重试
            last_err = e
            wait = pause * (i + 1)
            print(f"[retry] 第 {i + 1} 次失败: {type(e).__name__}: {e} -> {wait:.0f}s 后重试")
            time.sleep(wait)
    raise RuntimeError(f"重试 {retries} 次仍失败: {last_err}") from last_err


def validate_date(s: str) -> str:
    dt.datetime.strptime(s, "%Y%m%d")
    return s


def quality_check(df: pd.DataFrame, kind: str) -> None:
    print("\n===== 质检 =====")
    print(f"shape: {df.shape}")
    if "date" in df.columns:
        df["date"] = df["date"].astype(str)
        dup = int(df["date"].duplicated().sum())
        print(f"重复日期行: {dup}")
    if "pct_chg" in df.columns:  # A股涨跌幅合理性（含新股/除权等极端情形上限约±44%）
        bad = df["pct_chg"].abs() > 45
        if bad.any():
            print(f"[warn] 疑似异常涨跌幅 {int(bad.sum())} 行（|pct_chg|>45%），请人工核对:\n{df[bad].head()}")
    if "close" in df.columns and df["close"].isna().any():
        print(f"[warn] close 存在缺失 {int(df['close'].isna().sum())} 处，需在交付单中说明处理方式")
    print("缺失值统计（仅显示>0）:")
    na = df.isna().sum()
    print(na[na > 0].to_string() if (na > 0).any() else "  无缺失")


def data_id_card(kind: str, symbol: str, args) -> str:
    return (
        f"数据身份证 | kind={kind} symbol={symbol} adjust={args.adjust or '-'} "
        f"range={args.start or '-'}~{args.end or '-'} | "
        f"fetch_time={dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S CST')} | source=AKShare"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="AKShare 统一行情取数")
    p.add_argument("--kind", required=True,
                   choices=["stock", "index", "futures_main", "futures_contract"])
    p.add_argument("--symbol", required=True, help="如 000001 / 000300 / RB0 / RB2410")
    p.add_argument("--start", default=None, help="YYYYMMDD")
    p.add_argument("--end", default=None, help="YYYYMMDD，默认今天")
    p.add_argument("--adjust", default="", choices=["", "qfq", "hfq"], help="仅 stock 有效")
    p.add_argument("--period", default="daily", help="stock: daily/weekly/monthly")
    p.add_argument("--out", required=True, help="输出 CSV 路径")
    args = p.parse_args()

    if args.start:
        validate_date(args.start)
    end = args.end or dt.datetime.now().strftime("%Y%m%d")
    validate_date(end)

    import akshare as ak  # 延迟导入：先让 --help 可用

    kind, symbol = args.kind, args.symbol.strip()
    print(f"[fetch] kind={kind} symbol={symbol} start={args.start} end={end}")

    if kind == "stock":
        df = with_retry(lambda: ak.stock_zh_a_hist(
            symbol=symbol, period=args.period, start_date=args.start or "19900101",
            end_date=end, adjust=args.adjust))
        df = rename_std(df, STOCK_MAP)
    elif kind == "index":
        df = with_retry(lambda: ak.index_zh_a_hist(
            symbol=symbol, period=args.period, start_date=args.start or "19900101",
            end_date=end))
        df = rename_std(df, STOCK_MAP)
    elif kind == "futures_main":
        df = with_retry(lambda: ak.futures_main_sina(
            symbol=symbol, start_date=args.start or "19900101", end_date=end))
        df = rename_std(df, FUT_MAP)
    else:  # futures_contract
        df = with_retry(lambda: ak.futures_zh_daily_sina(symbol=symbol))
        df = rename_std(df, FUT_MAP)

    if df.empty:
        print("[error] 返回为空：核对代码是否正确/区间是否有数据/是否被限频", file=sys.stderr)
        return 2

    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"\n[ok] 已保存 {out}")
    print(data_id_card(kind, symbol, args))
    quality_check(df, kind)
    print("\nhead/tail 预览:")
    print(pd.concat([df.head(3), df.tail(3)]).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
