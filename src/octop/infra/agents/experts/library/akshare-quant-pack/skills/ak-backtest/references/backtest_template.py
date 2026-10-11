#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest_template.py — ak-backtest 技能参考模板（纯 pandas 向量化，框架无关）

定位：教学级参考实现，演示"诚实回测"的最小完整闭环——
    T日收盘信号 -> T+1开盘成交 -> 佣金+印花税+滑点 -> 涨跌停不可成交顺延 -> 绩效摘要
不追求生产级完备（无分笔资金曲线、无组合权重优化），复杂需求请换事件驱动框架，
但同一套执行假设必须保持。

用法：
    # 1) 自带演示数据离线试跑（验证环境与口径）
    python3 backtest_template.py --demo

    # 2) 用真实数据（ak-market-data 取数 + ak-technical-indicators 补指标后）
    python3 backtest_template.py --input kline_with_ind.csv \
        --fast 20 --slow 60 --commission 0.00025 --stamp 0.0005 --slippage 0.001 \
        --train-end 20231231 --out-dir ~/quant-data/backtests/demo

输出：<out-dir>/equity.csv（净值）、trades.csv（交易明细）、summary.json（参数与摘要）
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CN2EN = {"日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
         "开盘价": "open", "收盘价": "close", "最高价": "high", "最低价": "low"}


def demo_data() -> pd.DataFrame:
    """生成一段带趋势+震荡的模拟行情（几何随机游走 + 均值回归段），保证脚本可离线自证。"""
    rng = np.random.default_rng(42)
    n = 1200
    drift = np.concatenate([np.full(600, 0.0006), np.full(600, -0.0002)])
    noise = rng.normal(0, 0.018, n)
    ret = drift + noise
    close = 100.0 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    dates = pd.bdate_range("2019-01-01", periods=n).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": dates, "open": open_, "high": high,
                         "low": low, "close": close})


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={k: v for k, v in CN2EN.items() if k in df.columns})
    for c in ("open", "close"):
        if c not in df.columns:
            raise ValueError(f"缺少列 {c}，现有列: {df.columns.tolist()}")
    df["date"] = df["date"].astype(str)
    return df.sort_values("date").reset_index(drop=True)


def limit_up_down_mask(df: pd.DataFrame, limit: float = 0.10) -> pd.DataFrame:
    """近似的涨跌停不可成交判断：开盘价相对昨收盘超限视为一字板/超限开盘，顺延处理。
    简化处理：ST/北交所/创业板的限价差异未区分，使用者应按标的属性调整 limit。"""
    prev = df["close"].shift(1)
    ret_open = df["open"] / prev - 1.0
    return ret_open.abs() >= limit * 0.995


def run(df: pd.DataFrame, fast: int, slow: int, commission: float,
        stamp: float, slippage: float, train_end: str):
    # ---- 1) 信号：金叉持有、死叉空仓（T日收盘计算）----
    df["ma_f"] = df["close"].rolling(fast, min_periods=fast).mean()
    df["ma_s"] = df["close"].rolling(slow, min_periods=slow).mean()
    df["signal"] = np.where(df["ma_f"] > df["ma_s"], 1.0, 0.0)
    df["signal"] = df["signal"].where(df["ma_f"].notna() & df["ma_s"].notna(), 0.0)

    # ---- 2) 执行：T+1开盘成交，滑点+涨跌停顺延 ----
    df["pos"] = df["signal"].shift(1).fillna(0.0)          # 持仓 = 昨日信号（T+1 生效）
    blocked = limit_up_down_mask(df)                        # 一字板/超限开盘无法成交
    desired = df["pos"].diff().fillna(0.0)                  # 期望换仓动作
    df["pos"] = np.where(blocked & (desired != 0.0),
                         df["pos"].shift(1), df["pos"])     # 被锁门时保持旧仓（简化：顺延一日）
    df["pos"] = pd.Series(df["pos"], index=df.index).ffill().fillna(0.0)

    # ---- 3) 收益与成本：换仓日收 佣金(双边)+印花税(卖)+滑点(双边) ----
    df["ret"] = df["close"] / df["close"].shift(1) - 1.0
    trade_day = df["pos"].diff().abs().fillna(0.0) > 0
    cost = np.where(trade_day, commission * 2 + stamp * (df["pos"] < 1.0) + slippage * 2, 0.0)
    df["strat_ret"] = df["pos"] * df["ret"] - cost
    df["nav"] = (1.0 + df["strat_ret"].fillna(0.0)).cumprod()
    df["bh_nav"] = (1.0 + df["ret"].fillna(0.0)).cumprod()  # 买入持有基准

    train_mask = df["date"] <= train_end if train_end else pd.Series(True, index=df.index)
    return df, train_mask


def summarize(df: pd.DataFrame, mask: pd.Series) -> dict:
    sub = df[mask]
    r = sub["strat_ret"].dropna()
    years = max(len(r) / 244.0, 1e-9)
    nav = sub["nav"].iloc[-1] / sub["nav"].iloc[0]
    ann = nav ** (1 / years) - 1.0
    vol = r.std(ddof=0) * np.sqrt(244.0)
    sharpe = (r.mean() * 244.0) / vol if vol > 0 else float("nan")
    dd = (sub["nav"] / sub["nav"].cummax() - 1.0).min()
    return {"days": int(len(r)), "ann_ret": round(float(ann), 4),
            "ann_vol": round(float(vol), 4), "sharpe": round(float(sharpe), 3),
            "max_dd": round(float(dd), 4), "total_nav": round(float(nav), 4)}


def main() -> int:
    p = argparse.ArgumentParser(description="向量化双均线回测模板")
    p.add_argument("--input", default=None, help="OHLCV CSV；缺省用内置演示数据")
    p.add_argument("--demo", action="store_true", help="使用演示数据自证可跑通")
    p.add_argument("--fast", type=int, default=20)
    p.add_argument("--slow", type=int, default=60)
    p.add_argument("--commission", type=float, default=0.00025, help="单边佣金")
    p.add_argument("--stamp", type=float, default=0.0005, help="卖出印花税")
    p.add_argument("--slippage", type=float, default=0.001, help="单边滑点")
    p.add_argument("--train-end", default=None, help="训练集截止日 YYYYMMDD（样本内外切分）")
    p.add_argument("--out-dir", default="./backtest_out")
    a = p.parse_args()

    df = demo_data() if (a.demo or not a.input) else load(a.input)
    if a.fast >= a.slow:
        print("[error] fast 周期应小于 slow", file=sys.stderr)
        return 2

    df, train_mask = run(df, a.fast, a.slow, a.commission, a.stamp, a.slippage, a.train_end)

    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    df[["date", "nav", "bh_nav"]].to_csv(out / "equity.csv", index=False)

    trades = df[df["pos"].diff().abs() > 0][["date", "open", "pos"]]
    trades.to_csv(out / "trades.csv", index=False)

    summary = {
        "params": {"fast": a.fast, "slow": a.slow, "commission": a.commission,
                   "stamp": a.stamp, "slippage": a.slippage, "train_end": a.train_end,
                   "assumptions": "T日收盘信号T+1开盘成交；涨跌停顺延；成本双边计"},
        "train": summarize(df, train_mask),
        "test": summarize(df, ~train_mask) if a.train_end else None,
        "warnings": ["简化实现：未建模分笔资金、部分成交、期货保证金与换月；"
                     "样本外指标仅在提供 --train-end 时有效；"
                     "结果仅描述历史统计特征，不预测未来。"],
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                      encoding="utf-8")

    print("[ok] 输出目录:", out)
    print("训练期:", summary["train"])
    if summary["test"]:
        print("测试期:", summary["test"])
    print("[note] 绩效详表请用 ak-quant-report 的 performance.py 统一口径计算")
    return 0


if __name__ == "__main__":
    sys.exit(main())
