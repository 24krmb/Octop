#!/usr/bin/env python3
"""Deterministic summaries for Fiona member-seat position structure analysis.

Inputs are the JSON payloads returned by the MCP tools:

  - ``get_futures_member_positions`` (futures_market_data):
    contract x member x position_type detail, in hands (手).
  - ``get_member_position_summary`` (market_data_calculate):
    product x member long/short/net summary.

The script accepts the full MCP payload (``{"items": [...], "total": ...}``),
a bare list, or ``structured_content``, and normalizes both Chinese and English
keys. It computes rankings, concentration, long/short ratio, net positions and
seat changes without importing any third-party library.

Concentration (CR5/CR10/CR20) uses the whole-market position total of the type
as the denominator when ``--market-total`` is supplied; otherwise it falls back
to the total of the interface-returned seats and flags the denominator.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Candidate keys for the core value / change columns (checked in order).
VALUE_KEYS = [
    "成交/持仓量(手)", "成交量(手)", "持仓量(手)", "成交/持仓量",
    "多头持仓量", "空头持仓量",
    "volume", "amount", "value", "quantity",
]
CHANGE_KEYS = [
    "成交/持仓量变化(手)", "成交量变化(手)", "持仓量变化(手)", "成交/持仓量变化",
    "change", "change_amount", "变化", "增减",
]
LONG_KEYS = ["多头持仓量", "long_position", "long", "多头持仓"]
SHORT_KEYS = ["空头持仓量", "short_position", "short", "空头持仓"]
NET_KEYS = ["净持仓量", "net_position", "net", "净持仓"]

MEMBER_KEYS = ["会员简称", "member_name", "member", "公司简称", "席位"]
CONTRACT_KEYS = ["合约代码", "contract_code", "contract", "合约"]
SYMBOL_KEYS = ["品种代码", "symbol", "product_code", "品种"]
DATE_KEYS = ["交易日期", "trade_date", "日期"]
TYPE_KEYS = ["持仓类型", "position_type", "类型", "type"]


def _pick(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _normalize_position_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "1": "volume", "2": "long", "3": "short",
        "trade_volume": "volume", "volume": "volume",
        "long_position": "long", "long": "long",
        "short_position": "short", "short": "short",
        "成交量": "volume", "多头持仓": "long", "空头持仓": "short",
        "多头": "long", "空头": "short",
    }
    return mapping.get(text, text)


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        data: Any = payload
    elif isinstance(payload, dict):
        data = (
            payload.get("items")
            if isinstance(payload.get("items"), list)
            else payload.get("data")
        )
        if not isinstance(data, list):
            sc = payload.get("structured_content")
            if isinstance(sc, dict):
                data = sc.get("items", [])
        if not isinstance(data, list):
            return []
    else:
        return []
    return [row for row in data if isinstance(row, dict)]


def _detail_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in _rows(payload):
        value = _to_float(_pick(row, VALUE_KEYS))
        change = _to_float(_pick(row, CHANGE_KEYS))
        if value is None and change is None:
            continue
        records.append({
            "member": _pick(row, MEMBER_KEYS),
            "contract": _pick(row, CONTRACT_KEYS),
            "symbol": _pick(row, SYMBOL_KEYS),
            "trade_date": _pick(row, DATE_KEYS),
            "position_type": _normalize_position_type(_pick(row, TYPE_KEYS)),
            "value": value,
            "change": change,
        })
    return records


def _scope(record: dict[str, Any]) -> str:
    contract = record.get("contract")
    if contract:
        return str(contract)
    symbol = record.get("symbol")
    if symbol:
        return f"symbol:{symbol}"
    return "__all__"


def _type_summary(
    rows: list[dict[str, Any]],
    top: int,
    market_total: float | None = None,
) -> dict[str, Any]:
    valid = sorted(
        [row for row in rows if row["value"] is not None],
        key=lambda row: (row["value"] or 0),
        reverse=True,
    )
    # 会员合计：接口返回的全部席位（通常为交易所公布的前 20 名）之和，用于 share 分母。
    member_total = sum(row["value"] for row in valid if row["value"] is not None)
    # CR 分母：优先全市场该类型持仓合计；未提供时回退为会员合计并在输出中标注。
    concentration_base = market_total if market_total is not None else member_total
    ranking = [
        {
            "member": row["member"],
            "value": row["value"],
            "change": row["change"],
            "share": round(row["value"] / member_total, 6) if member_total else None,
        }
        for row in valid[:top]
    ]
    concentration: dict[str, float | None] = {}
    for n in (5, 10, 20):
        subtotal = sum(row["value"] for row in valid[:n] if row["value"] is not None)
        concentration[f"cr{n}"] = round(subtotal / concentration_base, 6) if concentration_base else None

    changed = [row for row in valid if row["change"] is not None]
    increase = sorted(changed, key=lambda row: row["change"], reverse=True)[:top]
    decrease = sorted(changed, key=lambda row: row["change"])[:top]
    return {
        "total": member_total,
        "market_total": market_total,
        "concentration_denominator": (
            "market_total" if market_total is not None else "member_total"
        ),
        "count": len(valid),
        "ranking": ranking,
        "concentration": concentration,
        "top_increase": [
            {"member": row["member"], "change": row["change"]} for row in increase
        ],
        "top_decrease": [
            {"member": row["member"], "change": row["change"]} for row in decrease
        ],
    }


def _analyze_scope(
    rows: list[dict[str, Any]],
    top: int,
    market_totals: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    market_totals = market_totals or {}
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_type[row["position_type"]].append(row)

    long_rows = by_type.get("long", [])
    short_rows = by_type.get("short", [])
    volume_rows = by_type.get("volume", [])

    long_by_member = {
        row["member"]: row["value"]
        for row in long_rows
        if row["member"] is not None and row["value"] is not None
    }
    short_by_member = {
        row["member"]: row["value"]
        for row in short_rows
        if row["member"] is not None and row["value"] is not None
    }
    net_rows = []
    for member in set(long_by_member) | set(short_by_member):
        long_value = long_by_member.get(member, 0.0)
        short_value = short_by_member.get(member, 0.0)
        net_rows.append({
            "member": member,
            "long": long_value,
            "short": short_value,
            "net": long_value - short_value,
        })
    net_rows.sort(key=lambda row: row["net"], reverse=True)
    net_long = [row for row in net_rows if row["net"] > 0][:top]
    net_short = sorted(
        [row for row in net_rows if row["net"] < 0],
        key=lambda row: row["net"],
    )[:top]

    long_total = sum(row["value"] for row in long_rows if row["value"] is not None)
    short_total = sum(row["value"] for row in short_rows if row["value"] is not None)

    return {
        "long": _type_summary(long_rows, top, market_total=market_totals.get("long")),
        "short": _type_summary(short_rows, top, market_total=market_totals.get("short")),
        "volume": _type_summary(volume_rows, top, market_total=market_totals.get("volume")),
        "net": {
            "top_net_long": net_long,
            "top_net_short": net_short,
        },
        "long_total": long_total,
        "short_total": short_total,
        "long_short_ratio": round(long_total / short_total, 6) if short_total else None,
    }


def analyze(
    payload: Any,
    top: int = 20,
    market_totals: dict[str, dict[str, float | None]] | None = None,
) -> dict[str, Any]:
    """market_totals: {scope: {"long": .., "short": .., "volume": ..}}，全市场该类型持仓合计，用作 CR 分母。"""
    market_totals = market_totals or {}
    records = _detail_records(payload)
    by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_scope[_scope(record)].append(record)

    scopes: dict[str, Any] = {}
    for scope, rows in sorted(by_scope.items()):
        scopes[scope] = _analyze_scope(rows, top, market_totals=market_totals.get(scope))

    return {
        "row_count": len(records),
        "scope_count": len(by_scope),
        "scopes": scopes,
    }


def net_from_summary(payload: Any, top: int = 20) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for row in _rows(payload):
        long_value = _to_float(_pick(row, LONG_KEYS))
        short_value = _to_float(_pick(row, SHORT_KEYS))
        net_value = _to_float(_pick(row, NET_KEYS))
        if net_value is None and long_value is not None and short_value is not None:
            net_value = long_value - short_value
        if net_value is None and long_value is None and short_value is None:
            continue
        records.append({
            "member": _pick(row, MEMBER_KEYS),
            "symbol": _pick(row, SYMBOL_KEYS),
            "trade_date": _pick(row, DATE_KEYS),
            "long": long_value,
            "short": short_value,
            "net": net_value,
        })

    ordered = sorted(
        records,
        key=lambda row: (row["net"] is None, row["net"] or 0),
        reverse=True,
    )
    return {
        "row_count": len(records),
        "top_net_long": [
            row for row in ordered if row["net"] is not None and row["net"] > 0
        ][:top],
        "top_net_short": sorted(
            [row for row in ordered if row["net"] is not None and row["net"] < 0],
            key=lambda row: row["net"],
        )[:top],
        "top_by_net": ordered[:top],
    }


def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument(
        "--input", required=True, help="get_futures_member_positions 的 JSON 文件路径，或 - 读取 stdin"
    )
    analyze_parser.add_argument("--top", type=int, default=20, help="返回前 N 席位，默认 20")
    analyze_parser.add_argument(
        "--market-total", default=None,
        help='全市场持仓量 JSON 文件路径，格式 {"scope": {"long": .., "short": .., "volume": ..}}，作为 CR 分母；缺省时用接口返回席位合计并标注',
    )

    net_parser = subparsers.add_parser("net")
    net_parser.add_argument(
        "--input", required=True, help="get_member_position_summary 的 JSON 文件路径，或 - 读取 stdin"
    )
    net_parser.add_argument("--top", type=int, default=20, help="返回前 N 席位，默认 20")

    args = parser.parse_args()

    try:
        payload = _load(args.input)
        if args.command == "analyze":
            market_totals = None
            if getattr(args, "market_total", None):
                market_totals = _load(args.market_total)
            result = analyze(payload, top=args.top, market_totals=market_totals)
        else:
            result = net_from_summary(payload, top=args.top)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
