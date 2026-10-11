#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
performance.py — ak-quant-report 技能内置绩效计算脚本（统一口径，禁止手算）

输入：
    --equity  净值曲线 CSV，至少含 date, nav 两列；可带 benchmark_nav 列
              （ak-backtest 模板输出的 equity.csv 直接可用）
    --trades  可选，交易明细 CSV（含 date/open/pos 或 entry_price/exit_price）

输出（--out-dir）：
    performance.json / performance.txt / nav_curve.png（策略vs基准净值 + 回撤阴影）

口径：244交易日折算年化；夏普含无风险利率(--rf, 默认2%)；ddof=0；
     最大回撤输出起止与修复日期；胜率/盈亏比仅在提供 --trades 时计算。
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 244.0

# ---- 中文字体自动探测（无中文字体环境退化为英文标签并告警）----
FONT_CANDIDATES = ["Noto Sans SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei",
                   "SimHei", "Microsoft YaHei", "PingFang SC", "DejaVu Sans"]


def setup_plot_font():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.font_manager as fm
        avail = {f.name for f in fm.fontManager.ttflist}
        for name in FONT_CANDIDATES:
            if name in avail:
                matplotlib.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                matplotlib.rcParams["axes.unicode_minus"] = False
                return name, True
        matplotlib.rcParams["axes.unicode_minus"] = False
        return None, False
    except Exception:  # noqa: BLE001 —— 出图失败不阻断指标计算
        return None, False


def max_drawdown(nav: pd.Series):
    peak = nav.cummax()
    dd = nav / peak - 1.0
    mdd = float(dd.min())
    end_idx = int(dd.idxmin())
    start_idx = int(nav[: end_idx + 1].idxmax())
    end_d = dd[end_idx:]
    rec_idx = int(end_d[end_d >= -1e-9].index[0]) if (end_d >= -1e-9).any() else None
    return mdd, start_idx, end_idx, rec_idx


def perf_block(nav: pd.Series, rf: float):
    nav = nav / nav.iloc[0]
    ret = nav.pct_change().dropna()
    years = max(len(nav) / TRADING_DAYS, 1e-9)
    ann = float(nav.iloc[-1] ** (1 / years) - 1.0)
    vol = float(ret.std(ddof=0) * np.sqrt(TRADING_DAYS))
    sharpe = float((ann - rf) / vol) if vol > 0 else None
    downside = ret[ret < 0]
    dvol = float(downside.std(ddof=0) * np.sqrt(TRADING_DAYS)) if len(downside) > 1 else None
    sortino = float((ann - rf) / dvol) if dvol else None
    mdd, i0, i1, rec = max_drawdown(nav.reset_index(drop=True))
    calmar = float(ann / abs(mdd)) if mdd < 0 else None
    return {
        "total_return": round(float(nav.iloc[-1] - 1.0), 4),
        "ann_return": round(ann, 4), "ann_vol": round(vol, 4),
        "sharpe": round(sharpe, 3) if sharpe is not None else None,
        "sortino": round(sortino, 3) if sortino is not None else None,
        "max_drawdown": round(mdd, 4),
        "max_dd_peak_day": int(i0), "max_dd_trough_day": int(i1),
        "max_dd_recovered_day": (int(rec) if rec is not None else None),
        "calmar": round(calmar, 3) if calmar is not None else None,
        "days": int(len(nav)),
    }


def trade_stats(trades_path: str):
    t = pd.read_csv(trades_path)
    # 兼容两种明细：买卖配对(entry_price/exit_price) 或 仓位快照(pos)
    if {"entry_price", "exit_price"}.issubset(t.columns):
        wins = t[t["exit_price"] > t["entry_price"]]
        losses = t[t["exit_price"] <= t["entry_price"]]
    elif {"date", "open", "pos"}.issubset(t.columns):
        # 由持仓快照推导单次开平仓收益（简化：相邻开仓区间）
        return None
    else:
        return None
    wr = len(wins) / max(len(wins) + len(losses), 1)
    avg_w = float((wins["exit_price"] / wins["entry_price"] - 1).mean()) if len(wins) else 0.0
    avg_l = abs(float((losses["exit_price"] / losses["entry_price"] - 1).mean())) if len(losses) else np.nan
    plr = avg_w / avg_l if avg_l and np.isfinite(avg_l) and avg_l > 0 else None
    return {"win_rate": round(wr, 4), "avg_win": round(avg_w, 4),
            "avg_loss": round(avg_l, 4), "profit_loss_ratio": round(plr, 3) if plr else None,
            "n_trades": int(len(wins) + len(losses))}


def monthly_table(nav: pd.Series, dates: pd.Series) -> pd.DataFrame:
    s = pd.Series(nav.values, index=pd.to_datetime(dates))
    m = s.resample("ME").last()
    m0 = s.resample("ME").first()
    ret = m / m.shift(1) - 1.0
    ret.iloc[0] = m.iloc[0] / m0.iloc[0] - 1.0
    tab = (ret * 100).round(2).to_frame("ret_pct")
    tab["year"] = tab.index.year
    tab["month"] = tab.index.month
    return tab.pivot_table(index="year", columns="month", values="ret_pct")


def main() -> int:
    p = argparse.ArgumentParser(description="统一口径绩效计算")
    p.add_argument("--equity", required=True, help="净值CSV：date[,nav[,benchmark_nav]]")
    p.add_argument("--nav-col", default="nav")
    p.add_argument("--trades", default=None)
    p.add_argument("--rf", type=float, default=0.02, help="无风险利率（年化），默认2%%")
    p.add_argument("--out-dir", default="./perf_out")
    a = p.parse_args()

    eq = pd.read_csv(a.equity)
    eq["date"] = eq["date"].astype(str)
    eq = eq.sort_values("date").reset_index(drop=True)
    if a.nav_col not in eq.columns:
        print(f"[error] 缺少净值列 {a.nav_col}，现有列: {eq.columns.tolist()}", file=sys.stderr)
        return 2

    strat = perf_block(eq[a.nav_col], a.rf)
    bench = perf_block(eq["benchmark_nav"], a.rf) if "benchmark_nav" in eq.columns else None
    ts = trade_stats(a.trades) if a.trades else None
    month = monthly_table(eq[a.nav_col], eq["date"])

    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    result = {"assumptions": {"trading_days": 244, "rf": a.rf, "ddof": 0,
                              "source": a.equity,
                              "note": "历史统计特征，不构成对未来表现的任何预测"},
              "strategy": strat, "benchmark": bench, "trades": ts,
              "monthly_return_pct": month.to_dict()}
    (out / "performance.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                          encoding="utf-8")

    lines = ["===== 绩效摘要（统一口径） ====="]
    lines.append(f"年化收益: {strat['ann_return']*100:.2f}%  |  年化波动: {strat['ann_vol']*100:.2f}%")
    lines.append(f"夏普: {strat['sharpe']}  |  索提诺: {strat['sortino']}  |  卡玛: {strat['calmar']}")
    lines.append(f"最大回撤: {strat['max_drawdown']*100:.2f}%  (峰{strat['max_dd_peak_day']}→谷{strat['max_dd_trough_day']}"
                 f"→修复{strat['max_dd_recovered_day']})")
    if bench:
        lines.append(f"[基准] 年化 {bench['ann_return']*100:.2f}% | 夏普 {bench['sharpe']} | 最大回撤 {bench['max_drawdown']*100:.2f}%")
    if ts:
        lines.append(f"胜率: {ts['win_rate']*100:.1f}% | 盈亏比: {ts['profit_loss_ratio']} | 交易数: {ts['n_trades']}")
    lines.append("月度收益(%):")
    lines.append(month.fillna("").to_string())
    lines.append("⚠ 年化>50%且回撤<10%时，先按 ak-backtest §5 排查实现错误再庆祝")
    (out / "performance.txt").write_text("\n".join(lines), encoding="utf-8")

    # ---- 净值图（五要素：标题/轴单位/区间/脚注/中文字体）----
    font, ok = setup_plot_font()
    try:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                       constrained_layout=True)
        ax1.plot(eq["date"], eq[a.nav_col], lw=1.4, label="Strategy")
        if "benchmark_nav" in eq.columns:
            ax1.plot(eq["date"], eq["benchmark_nav"], lw=1.0, alpha=0.8, label="Benchmark")
        ax1.set_title("Equity Curve / 净值曲线")
        ax1.set_ylabel("NAV (净值)")
        ax1.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
        nav = eq[a.nav_col] / eq[a.nav_col].iloc[0]
        dd = nav / nav.cummax() - 1.0
        ax2.fill_between(eq["date"], dd * 100, 0, alpha=0.5)
        ax2.set_title("Drawdown / 回撤(%)")
        ax2.set_ylabel("回撤 (%)")
        step = max(len(eq) // 8, 1)
        ax2.set_xticks(range(0, len(eq), step))
        ax2.set_xticklabels(eq["date"][::step], rotation=30, fontsize=8)
        fig.suptitle(f"{eq['date'].iloc[0]} ~ {eq['date'].iloc[-1]} | "
                     f"font={font or 'NONE(中文可能乱码)'} | 口径: 244交易日, rf={a.rf}",
                     fontsize=9, y=0.995)
        fig.savefig(out / "nav_curve.png", dpi=150)
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 出图失败（指标不受影响）: {type(e).__name__}: {e}")

    print(f"[ok] 绩效输出: {out}/performance.json | performance.txt | nav_curve.png")
    if not ok:
        print("[warn] 未检测到中文字体，图中中文可能显示为方块（指标计算不受影响）")
    print("\n".join(lines[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
