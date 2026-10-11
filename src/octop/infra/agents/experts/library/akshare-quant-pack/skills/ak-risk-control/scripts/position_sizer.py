#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
position_sizer.py — ak-risk-control 技能内置仓位计算器

三种模式：
    equity   A股单笔风险预算（含100股取整、实际风险回算）
    futures  期货核算（保证金占用、名义敞口、强平距离，含风险预算兼容）
    kelly    Kelly折扣仓位（胜率/盈亏比来自回测单，禁拍脑袋）

用法示例：
    python3 position_sizer.py equity --capital 1000000 --risk-pct 0.01 --entry 12.50 --stop 11.80
    python3 position_sizer.py futures --capital 1000000 --risk-pct 0.01 --entry 3850 \
        --stop 3720 --multiplier 10 --margin-rate 0.12 --contract-ratio 0.5
    python3 position_sizer.py kelly --win-rate 0.55 --win-loss 1.4 --fraction 0.5 \
        --capital 1000000 --entry 12.5 --stop 11.8
"""

import argparse
import json
import sys


def fail(msg: str) -> int:
    print(f"[error] {msg}", file=sys.stderr)
    return 2


def risk_line(capital: float, risk_pct: float, entry: float, stop: float, lots: int = None):
    """给定方向的多头风险核算；lots 为 A股股数（非手），返回实际风险。"""
    per_share_risk = entry - stop
    if per_share_risk <= 0:
        return None, "止损价必须低于入场价（多头）"
    budget = capital * risk_pct
    if lots is None:
        lots = int(budget // (per_share_risk * 100)) * 100  # 100股整数倍向下取整
    actual = lots * per_share_risk
    return {"budget": round(budget, 2), "shares": lots,
            "actual_risk": round(actual, 2),
            "actual_risk_pct": round(actual / capital, 4),
            "position_value": round(lots * entry, 2),
            "position_pct": round(lots * entry / capital, 4)}, None


def mode_equity(a):
    res, err = risk_line(a.capital, a.risk_pct, a.entry, a.stop)
    if err:
        return fail(err)
    res["atr_stop"] = None
    if a.atr and a.atr > 0:
        stop_atr = a.entry - a.k * a.atr
        res2, _ = risk_line(a.capital, a.risk_pct, a.entry, stop_atr)
        res["atr_stop"] = {"stop_price": round(stop_atr, 2), **res2}
    print(json.dumps({"mode": "equity", "result": res,
                      "rules": {"single_trade_risk_redline": "≤2%",
                                "note": "100股整数倍向下取整；实际风险≤预算"}},
                     ensure_ascii=False, indent=2))
    return 0


def mode_futures(a):
    if a.stop >= a.entry:
        return fail("止损价必须低于入场价（多头）")
    per_pt_risk = a.entry - a.stop                      # 每点价差
    risk_per_lot = per_pt_risk * a.multiplier           # 每手风险
    budget = a.capital * a.risk_pct
    lots_risk = int(budget // risk_per_lot)             # 风险预算允许手数

    margin_per_lot = a.entry * a.multiplier * a.margin_rate
    lots_margin = int((a.capital * a.contract_ratio) // margin_per_lot)  # 保证金约束手数
    lots = max(0, min(lots_risk, lots_margin))
    if lots == 0:
        return fail("风险预算或保证金约束下可开手数为0：降低仓位预期或调整参数")

    notional = lots * a.entry * a.multiplier
    margin_used = lots * margin_per_lot
    actual_risk = lots * risk_per_lot
    # 强平距离：净值跌至维持保证金线（近似：亏损=占用资金×(1/保证金率-1) 的缓冲，再扣风险缓冲）
    buffer_move = (a.capital - margin_used) / (a.multiplier * lots)  # 反向波动多少点耗尽自由资金
    res = {
        "lots": lots,
        "risk_budget": round(budget, 2), "risk_per_lot": round(risk_per_lot, 2),
        "actual_risk": round(actual_risk, 2),
        "actual_risk_pct": round(actual_risk / a.capital, 4),
        "notional": round(notional, 2), "leverage": round(notional / a.capital, 2),
        "margin_used": round(margin_used, 2),
        "margin_pct": round(margin_used / a.capital, 4),
        "liquidation_move_pts": round(buffer_move, 1),
        "liquidation_move_atr": round(buffer_move / a.atr, 2) if a.atr else None,
        "binding_constraint": "risk_budget" if lots_risk <= lots_margin else "margin",
    }
    print(json.dumps({"mode": "futures", "result": res,
                      "rules": {"margin_used_pct": "建议≤40%", "risk_redline": "≤2%",
                                "note": "风控看名义敞口，不看占用资金；强平距离按自由资金估算，"
                                        "未含交易所/期货公司梯度保证金上调"}},
                     ensure_ascii=False, indent=2))
    return 0


def mode_kelly(a):
    if not (0 < a.win_rate < 1) or a.win_loss <= 0:
        return fail("win_rate∈(0,1)，win_loss>0")
    f = a.win_rate - (1 - a.win_rate) / a.win_loss
    if f <= 0:
        print(json.dumps({"mode": "kelly", "result": {"kelly_f": round(f, 4),
                          "advice": "负Kelly：该盈亏结构下期望为负，不建议参与"},
                          "source_rule": "胜率/盈亏比必须来自Echo回测单"}, ensure_ascii=False, indent=2))
        return 0
    eff = min(f * a.fraction, 0.20)  # 折扣 + 20% 单策略上限双保险
    res = {"kelly_f": round(f, 4), "fraction": a.fraction,
           "effective_f": round(eff, 4),
           "position_value": round(a.capital * eff, 2)}
    if a.entry and a.stop and a.entry > a.stop:
        per_share_risk = a.entry - a.stop
        res["shares"] = int((a.capital * eff) // per_share_risk)
        res["note"] = "股数按 Kelly 仓位金额 ÷ 每股止损距离 计算，未做100股取整；精确核算请用 equity 模式"
    print(json.dumps({"mode": "kelly", "result": res,
                      "rules": {"discount": "永远使用折扣Kelly（默认0.5）",
                                "cap": "单策略≤20%资金",
                                "source": "胜率/盈亏比必须来自回测单，样本<100笔再打半折"}},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="仓位计算器（风险预算/期货核算/Kelly）")
    sub = p.add_subparsers(dest="mode", required=True)

    def common(sp):
        sp.add_argument("--capital", type=float, required=True, help="总资金")
        sp.add_argument("--risk-pct", type=float, default=0.01, help="单笔风险比例，默认1%%")
        sp.add_argument("--entry", type=float, required=True)
        sp.add_argument("--stop", type=float, required=True)

    se = sub.add_parser("equity"); common(se)
    se.add_argument("--atr", type=float, default=None, help="ATR14，给定则附ATR止损方案")
    se.add_argument("--k", type=float, default=2.0, help="ATR倍数，默认2.0")

    sf = sub.add_parser("futures"); common(sf)
    sf.add_argument("--multiplier", type=float, required=True, help="合约乘数，如螺纹10")
    sf.add_argument("--margin-rate", type=float, required=True, help="保证金率，如0.12")
    sf.add_argument("--contract-ratio", type=float, default=0.4, help="保证金占用上限比例，默认0.4")
    sf.add_argument("--atr", type=float, default=None, help="用于换算强平距离的ATR倍数")

    sk = sub.add_parser("kelly")
    sk.add_argument("--capital", type=float, required=True)
    sk.add_argument("--win-rate", type=float, required=True)
    sk.add_argument("--win-loss", type=float, required=True, help="盈亏比")
    sk.add_argument("--fraction", type=float, default=0.5, help="Kelly折扣，默认0.5")
    sk.add_argument("--risk-pct", type=float, default=0.01)

    a = p.parse_args()
    return {"equity": mode_equity, "futures": mode_futures, "kelly": mode_kelly}[a.mode](a)


if __name__ == "__main__":
    sys.exit(main())
