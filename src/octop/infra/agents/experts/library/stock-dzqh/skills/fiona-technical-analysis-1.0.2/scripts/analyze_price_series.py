#!/usr/bin/env python3
"""Generate auditable technical statistics from one OHLC price series."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


ALIASES = {
    "time": ("datetime", "date", "trade_date", "时间", "日期", "交易日期"),
    "open": ("open", "开盘", "开盘价"),
    "high": ("high", "最高", "最高价"),
    "low": ("low", "最低", "最低价"),
    "close": ("close", "last", "收盘", "收盘价", "最新价"),
    "volume": ("volume", "成交量"),
    "open_interest": ("open_interest", "oi", "持仓量"),
}


def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("items", "data", "tableData", "rows", "series"):
        if key in value:
            found = _rows(value[key])
            if found:
                return found
    return []


def _first(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _normalise(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(raw_rows):
        item = {name: _first(row, aliases) for name, aliases in ALIASES.items()}
        for name in ("open", "high", "low", "close", "volume", "open_interest"):
            item[name] = _number(item[name])
        if item["high"] is None or item["low"] is None or item["close"] is None:
            continue
        item["_order"] = index
        result.append(item)
    if result and all(item["time"] is not None for item in result):
        result.sort(key=lambda item: str(item["time"]))
    for item in result:
        item["time"] = str(item["time"] if item["time"] is not None else item["_order"])
        item.pop("_order")
    return result


def _mean(values: list[float], length: int) -> float | None:
    return statistics.fmean(values[-length:]) if len(values) >= length else None


def _pct_change(values: list[float], bars: int) -> float | None:
    if len(values) <= bars or values[-bars - 1] == 0:
        return None
    return (values[-1] / values[-bars - 1] - 1) * 100


def _true_ranges(rows: list[dict[str, Any]]) -> list[float]:
    result = []
    previous_close = None
    for row in rows:
        candidates = [row["high"] - row["low"]]
        if previous_close is not None:
            candidates.extend(
                [abs(row["high"] - previous_close), abs(row["low"] - previous_close)]
            )
        result.append(max(candidates))
        previous_close = row["close"]
    return result


def _swings(rows: list[dict[str, Any]], window: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    highs, lows = [], []
    for index in range(window, len(rows) - window):
        segment = rows[index - window:index + window + 1]
        row = rows[index]
        if row["high"] == max(item["high"] for item in segment):
            highs.append({"time": row["time"], "level": row["high"], "index": index})
        if row["low"] == min(item["low"] for item in segment):
            lows.append({"time": row["time"], "level": row["low"], "index": index})
    return highs, lows


def _dedupe_levels(candidates: list[dict[str, Any]], tolerance: float, reverse: bool) -> list[dict[str, Any]]:
    selected = []
    for item in sorted(candidates, key=lambda value: value["level"], reverse=reverse):
        if any(abs(item["level"] - prior["level"]) <= tolerance for prior in selected):
            continue
        selected.append(item)
        if len(selected) == 3:
            break
    return selected


def analyze(rows: list[dict[str, Any]], pivot_window: int) -> dict[str, Any]:
    if len(rows) < max(5, pivot_window * 2 + 1):
        raise ValueError("至少需要5行且必须足以覆盖摆动点窗口的有效OHLC数据")

    closes = [row["close"] for row in rows]
    returns = [
        closes[index] / closes[index - 1] - 1
        for index in range(1, len(closes)) if closes[index - 1] != 0
    ]
    true_ranges = _true_ranges(rows)
    atr14 = _mean(true_ranges, 14)
    latest = rows[-1]
    lookback = rows[-20:]
    rolling_high = max(row["high"] for row in lookback)
    rolling_low = min(row["low"] for row in lookback)
    high_swings, low_swings = _swings(rows, pivot_window)
    tolerance = max((atr14 or 0) * 0.25, latest["close"] * 0.001)

    support_candidates = [item for item in low_swings if item["level"] <= latest["close"]]
    resistance_candidates = [item for item in high_swings if item["level"] >= latest["close"]]
    support_candidates.append({"time": lookback[0]["time"], "level": rolling_low, "source": "rolling_low_20"})
    resistance_candidates.append({"time": lookback[0]["time"], "level": rolling_high, "source": "rolling_high_20"})
    for item in support_candidates:
        item.setdefault("source", "swing_low")
        item.pop("index", None)
    for item in resistance_candidates:
        item.setdefault("source", "swing_high")
        item.pop("index", None)

    support = _dedupe_levels(support_candidates, tolerance, reverse=True)
    resistance = _dedupe_levels(resistance_candidates, tolerance, reverse=False)
    sma = {str(length): _mean(closes, length) for length in (5, 10, 20, 60)}
    valid_sma = {name: value for name, value in sma.items() if value is not None}
    close_vs_sma = {
        name: (latest["close"] / value - 1) * 100
        for name, value in valid_sma.items() if value != 0
    }

    return {
        "status": "ok",
        "rows": len(rows),
        "from": rows[0]["time"],
        "through": latest["time"],
        "latest": {
            "close": latest["close"],
            "volume": latest["volume"],
            "open_interest": latest["open_interest"],
        },
        "trend_statistics": {
            "returns_pct": {str(bars): _pct_change(closes, bars) for bars in (1, 5, 20, 60)},
            "sma": sma,
            "close_vs_sma_pct": close_vs_sma,
        },
        "volatility_statistics": {
            "atr14": atr14,
            "atr14_pct": (atr14 / latest["close"] * 100) if atr14 is not None and latest["close"] else None,
            "close_return_std20_pct": (
                statistics.stdev(returns[-20:]) * 100 if len(returns) >= 2 else None
            ),
            "note": "close_return_std20_pct为最近最多20根K线收益率标准差，未年化",
        },
        "price_structure": {
            "rolling_high_20": rolling_high,
            "rolling_low_20": rolling_low,
            "range_position_20": (
                (latest["close"] - rolling_low) / (rolling_high - rolling_low)
                if rolling_high != rolling_low else None
            ),
            "support_candidates": support,
            "resistance_candidates": resistance,
            "level_merge_tolerance": tolerance,
        },
        "usage_note": "统计结果只提供可复核证据；结合合约口径、成交持仓和多周期TA后再形成判断。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从单一OHLC时序生成趋势、波动和价格结构统计")
    parser.add_argument("--input", required=True, help="市场数据MCP JSON文件；使用-从stdin读取")
    parser.add_argument("--pivot-window", type=int, default=2, help="摆动高低点左右窗口，默认2")
    parser.add_argument("--output", default="", help="可选输出JSON路径；默认写stdout")
    args = parser.parse_args()
    if not 1 <= args.pivot_window <= 20:
        parser.error("--pivot-window 必须在1到20之间")
    try:
        result = analyze(_normalise(_rows(_load(args.input))), args.pivot_window)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
