#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
screener_template.py — ak-stock-screener 技能内置快照筛选脚本

设计目标：一次请求（stock_zh_a_spot_em）完成"硬条件初筛 + 快照因子打分 + Top-N 排序"。
快照因子含：60日涨跌幅(momentum60)、换手率(turnover)、市净率(pb)、市盈率-动态(pe)、
振幅(amplitude)、总市值(mktcap)。字段自动探测，方向与去极值统一处理。

用法：
    python3 screener_template.py \
        --min-amount 2 --max-pe 40 --min-pe 0 --min-mktcap 50 \
        --exclude-bj --exclude-st \
        --weights momentum60:0.4,turnover:0.2,pb:0.2,amplitude:0.2 \
        --top 30 --out ~/quant-data/proc/screener_result.csv
"""

import argparse
import datetime as dt
import sys

import numpy as np
import pandas as pd

# 因子方向：+1 越大越好，-1 越小越好
FACTOR_SIGN = {"momentum60": +1, "turnover": -1, "pb": -1, "pe": -1,
               "amplitude": +1, "mktcap": +1}


def detect(df: pd.DataFrame, candidates: list) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    return ""


def winsor_z(s: pd.Series) -> pd.Series:
    """±3 MAD 去极值后 z-score。"""
    med = s.median()
    mad = (s - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return (s - s.mean()) / (s.std(ddof=0) or np.nan)
    clipped = s.clip(med - 3 * mad, med + 3 * mad)
    sd = clipped.std(ddof=0)
    return (clipped - clipped.mean()) / sd if sd > 0 else clipped * 0.0


def main() -> int:
    p = argparse.ArgumentParser(description="快照多因子选股（单次请求）")
    p.add_argument("--min-amount", type=float, default=0.5, help="最低成交额（亿元）")
    p.add_argument("--min-pe", type=float, default=None, help="最小PE（动态），亏损票自动剔除")
    p.add_argument("--max-pe", type=float, default=None, help="最大PE（动态）")
    p.add_argument("--min-mktcap", type=float, default=None, help="最小总市值（亿元）")
    p.add_argument("--max-mktcap", type=float, default=None, help="最大总市值（亿元）")
    p.add_argument("--exclude-bj", action="store_true", help="剔除北交所（8/4/92开头）")
    p.add_argument("--exclude-st", action="store_true", help="剔除ST/*ST/退")
    p.add_argument("--weights", default="momentum60:0.4,turnover:0.2,pb:0.2,amplitude:0.2")
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--out", default="./screener_result.csv")
    a = p.parse_args()

    import akshare as ak
    print("[fetch] stock_zh_a_spot_em ...")
    df = ak.stock_zh_a_spot_em()
    print(f"[ok] 全市场 {len(df)} 条；列名: {df.columns.tolist()}")

    # ---- 字段探测（列名随版本微调，禁止硬编码单一名）----
    col_code = detect(df, ["代码"])
    col_name = detect(df, ["名称"])
    col_amt = detect(df, ["成交额"])
    col_pct60 = detect(df, ["60日涨跌幅"])
    col_turn = detect(df, ["换手率"])
    col_pb = detect(df, ["市净率"])
    col_pe = detect(df, ["市盈率-动态", "市盈率"])
    col_amp = detect(df, ["振幅"])
    col_cap = detect(df, ["总市值"])
    for label, col in [("成交额", col_amt), ("60日涨跌幅", col_pct60), ("换手率", col_turn),
                       ("市净率", col_pb), ("市盈率动态", col_pe), ("总市值", col_cap)]:
        if not col:
            print(f"[warn] 快照中未找到字段: {label}（版本差异），相关因子将跳过")

    out = df[[c for c in [col_code, col_name] if c]].copy()
    out.columns = ["code", "name"][: out.shape[1]]

    # ---- 硬条件初筛 ----
    if col_amt:
        out["amount_yi"] = pd.to_numeric(df[col_amt], errors="coerce") / 1e8  # 元 -> 亿元
        out = out[out["amount_yi"] >= a.min_amount]
    if col_cap:
        out["mktcap_yi"] = pd.to_numeric(df[col_cap], errors="coerce") / 1e8
        if a.min_mktcap is not None:
            out = out[out["mktcap_yi"] >= a.min_mktcap]
        if a.max_mktcap is not None:
            out = out[out["mktcap_yi"] <= a.max_mktcap]
    if col_pe:
        out["pe"] = pd.to_numeric(df[col_pe], errors="coerce")
        out = out[out["pe"] > 0]  # 亏损票 PE 无意义
        if a.min_pe is not None:
            out = out[out["pe"] >= a.min_pe]
        if a.max_pe is not None:
            out = out[out["pe"] <= a.max_pe]
    if col_pb:
        out["pb"] = pd.to_numeric(df[col_pb], errors="coerce")
    if col_pct60:
        out["momentum60"] = pd.to_numeric(df[col_pct60], errors="coerce")
    if col_turn:
        out["turnover"] = pd.to_numeric(df[col_turn], errors="coerce")
    if col_amp:
        out["amplitude"] = pd.to_numeric(df[col_amp], errors="coerce")
    if a.exclude_bj:
        out = out[~out["code"].str.startswith(("4", "8", "92"))]
    if a.exclude_st:
        out = out[~out["name"].str.contains("ST|退", na=False)]

    print(f"[filter] 硬条件后剩余 {len(out)} 票")

    # ---- 因子打分：去极值 -> z-score -> 加权 ----
    weights = {}
    for kv in a.weights.split(","):
        k, w = kv.split(":")
        if k in out.columns and k in FACTOR_SIGN:
            weights[k] = float(w)
    total_w = sum(weights.values())
    if total_w <= 0:
        print("[error] 有效因子权重为空（字段缺失或拼写错误）", file=sys.stderr)
        return 2

    score = pd.Series(0.0, index=out.index)
    for k, w in weights.items():
        z = winsor_z(out[k])
        score = score + (FACTOR_SIGN[k] * w / total_w) * z.fillna(0.0)
        out[f"z_{k}"] = z.round(4)
    out["score"] = score.round(4)
    out = out.sort_values("score", ascending=False)

    top = out.head(a.top)
    out.to_csv(a.out, index=False, encoding="utf-8-sig")

    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n===== 口径声明 =====")
    print(f"数据时点: {ts}（盘中快照，收盘后数据为准） | 源: stock_zh_a_spot_em")
    print(f"硬条件: 成交额>={a.min_amount}亿", end="")
    if a.min_pe is not None or a.max_pe is not None:
        print(f" | PE∈[{a.min_pe},{a.max_pe}]", end="")
    if a.min_mktcap is not None:
        print(f" | 市值>={a.min_mktcap}亿", end="")
    print(f" | 剔除北交所={a.exclude_bj} 剔除ST={a.exclude_st}")
    print(f"因子与权重(方向已含): {weights} | 打分: ±3MAD去极值+zscore+加权 | 缺失按0分处理")
    print("\n===== Top {} =====".format(a.top))
    cols = [c for c in ["code", "name", "score", "momentum60", "turnover", "pb", "pe", "amount_yi", "mktcap_yi"] if c in top.columns]
    print(top[cols].to_string(index=False))
    print("\n[disclaimer] 筛选结果为统计排序，不构成投资建议；历史截面不代表未来表现。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
