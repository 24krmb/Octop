#!/usr/bin/env python3
"""Render verified research JSON as a portable HTML snapshot (no network access)."""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CST = timezone(timedelta(hours=8))
ENDPOINT_MODES = {
    "pre_window_anchor": "端点口径：窗口前或起点原始基准 → 窗口内末条原始记录。",
    "in_window": "端点口径：窗口内首末有效原始记录；各标的实际起点可不同，不代表完整假期累计表现。",
}


def text(value):
    return escape(str(value), quote=True)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("时间必须包含时区")
    return result


def date_text(value):
    return timestamp(value).astimezone(CST).strftime("%Y-%m-%d %H:%M") if value else "未提供"


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError("缺少有效价格")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("价格不是数字") from exc
    if not result.is_finite():
        raise ValueError("价格必须为有限数值")
    return result


def price_text(value):
    if value is None:
        return "—"
    try:
        return format(number(value), ",f")
    except ValueError:
        return "无效价格"


def measure(row, start, end, endpoint_mode="pre_window_anchor"):
    """Only admit verified, comparable endpoints; return reason for excluded rows."""
    if endpoint_mode not in ENDPOINT_MODES:
        raise ValueError("不支持的端点口径")
    if row.get("comparable") is not True:
        return None, row.get("note") or "未确认可比口径"
    try:
        base, last = number(row.get("base")), number(row.get("last"))
        first, final = timestamp(row["base_time"]), timestamp(row["last_time"])
    except (KeyError, TypeError, AttributeError, ValueError):
        return None, "缺少有效价格或带时区的取价时间"
    if base <= 0:
        return None, "基准价非正，不采用普通百分比排名"
    valid_window = (first <= start <= final <= end if endpoint_mode == "pre_window_anchor"
                    else start <= first < final <= end)
    if not valid_window or first >= final:
        return None, "实际端点不满足统一观察窗口"
    return (last / base - 1) * 100, ""


def links(sources):
    result = []
    for item in sources:
        url = item.get("url", "")
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("来源必须为不含凭证的 HTTP(S) 原文链接")
        result.append(f'<a href="{text(url)}" rel="noopener noreferrer">{text(item["label"])}</a>')
    return " · ".join(result)


def cards(items, css):
    return "".join(f'<article class="{css}"><h3>{text(i["title"])}</h3><p>{text(i["text"])}</p></article>' for i in items)


def risk_disclaimer(level):
    values = re.findall(r"^> (风险提示：.*)$", (ROOT / "references/disclosure.md").read_text(encoding="utf-8"), re.M)
    if level not in ("normal", "enhanced") or len(values) != 2:
        raise ValueError("风险提示配置错误")
    return values[0 if level == "normal" else 1]


def render(data):
    if type(data.get("demo")) is not bool:
        raise ValueError("必须显式设置 demo 布尔值")
    scenario = data.get("scenario", "holiday")
    if scenario not in ("holiday", "custom_interval", "simulated_holiday"):
        raise ValueError("不支持的观察场景")
    endpoint_mode = data.get("endpoint_mode", "pre_window_anchor")
    if endpoint_mode not in ENDPOINT_MODES:
        raise ValueError("不支持的端点口径")
    endpoint_note = ENDPOINT_MODES[endpoint_mode]
    banner = ""
    if data["demo"]:
        banner = "样式演示 · 以下日期、价格与事件均为合成样例，不代表真实市场。"
    elif scenario == "simulated_holiday":
        banner = "假期场景模拟 · 仅假设国内休市，使用真实区间行情与资讯；不代表该期间是法定假期。"
    elif scenario == "custom_interval":
        banner = "自定义区间观察 · 使用实际取得的资料，不要求该期间属于法定假期。"
    start, end = timestamp(data["requested_start"]), timestamp(data["requested_end"])
    generated = timestamp(data["generated_at"])
    news_end = timestamp(data["news_cutoff"])
    if not start < end <= generated or news_end > generated:
        raise ValueError("观察窗口或资讯截止晚于生成时间，或起止顺序错误")
    if data.get("sync_at") and timestamp(data["sync_at"]) > generated:
        raise ValueError("同步时间晚于生成时间")
    rows, seen, valid = [], set(), []
    for row in data["markets"]:
        for field in ("name", "exchange", "symbol", "basis", "unit", "source"):
            if not row.get(field):
                raise ValueError(f"行情缺少 {field}")
        identifier = ("name", row["name"]) if row["symbol"] in ("未提供", "未返回代码") else ("symbol", row["symbol"])
        identity = (row["exchange"], identifier, row["basis"])
        if identity in seen:
            raise ValueError("同一外盘标的重复，请先合并国内映射")
        seen.add(identity)
        pct, reason = measure(row, start, end, endpoint_mode)
        if pct is not None:
            valid.append((row, pct))
        direction = "up" if pct is not None and pct > 0 else "down" if pct is not None and pct < 0 else "flat"
        result = f"{pct:+.2f}%" if pct is not None else "未纳入排名"
        def endpoint(label):
            try:
                shown_time = date_text(row.get(label + "_time"))
            except (TypeError, AttributeError, ValueError):
                shown_time = "时间无效"
            return f'{text(price_text(row.get(label)))}<small>{text(shown_time)}</small>'
        note = "；".join(dict.fromkeys(x for x in [reason, row.get("note", "")] if x))
        rows.append(f'<tr><td><strong>{text(row["name"])}</strong><small>{text(row.get("category", ""))} · {text(row["exchange"])} / {text(row["symbol"])}</small><small>关联：{text("、".join(row.get("domestic", [])) or "未确认")}</small></td>'
                    f'<td>{endpoint("base")}</td><td>{endpoint("last")}</td><td class="{direction}">{result}</td>'
                    f'<td>{text(row["basis"])} · {text(row["unit"])}<small>{text(row["source"])}</small><small>{text(note)}</small></td></tr>')
    scale = max((abs(p) for _, p in valid), default=Decimal(1)) or Decimal(1)
    chart = ['<div class="chart-head"><span>已覆盖可比标的</span><span>下跌 ←</span><span>0 → 上涨</span><span></span></div>']
    for row, pct in sorted(valid, key=lambda item: item[1], reverse=True):
        width = abs(pct) / scale * 100
        bar = f'<span class="bar {"pos" if pct >= 0 else "neg"}" style="width:{width:.4f}%"></span>'
        chart.append(f'<div class="bar-row"><span class="bar-label">{text(row["name"])}</span><span class="bar-half neg">{bar if pct < 0 else ""}</span><span class="bar-half">{bar if pct >= 0 else ""}</span><span class="bar-value {"up" if pct > 0 else "down" if pct < 0 else "flat"}">{pct:+.2f}%</span></div>')
    if not valid:
        chart.append('<p class="muted">本期没有满足统一口径的可比行情，详见明细与缺口说明。</p>')
    events = []
    for event in data["events"]:
        if not data["demo"] and not event.get("sources"):
            raise ValueError("真实事件缺少可核实来源")
        source_html = links(event.get("sources", [])) or "合成样例，无真实新闻来源"
        events.append(f'<article class="event"><h3>{text(event["title"])}</h3><p class="event-meta">事件：{text(event["happened_at"])} · 发布：{text(event["published_at"])}</p><p>{text(event["fact"])}</p><p><strong>关联解读：</strong>{text(event["interpretation"])}</p><p><strong>继续观察：</strong>{text(event["watch"])}</p><p class="timing">{text(event["timing_note"])}</p><p class="sources">{source_html}</p></article>')
    dates = [timestamp(r["last_time"]) for r, _ in valid]
    coverage_times = (f'{date_text(min(dates).isoformat())} 至 {date_text(max(dates).isoformat())}（各品种不同）' if len(set(dates)) > 1 else date_text(dates[0].isoformat())) if dates else "无可比行情截止时间"
    generated_note = f'生成：{date_text(data["generated_at"])}'
    if events:
        generated_note += f' · 资讯检索截止：{date_text(data["news_cutoff"])}'
    meta = [f'观察窗口：{date_text(data["requested_start"])} → {date_text(data["requested_end"])}', f'可比行情末值时点：{coverage_times}', generated_note, '以上时间均为北京时间；行情为已同步数据快照，非实时报价。']
    meta.append(endpoint_note)
    if data.get("sync_at"):
        meta.append(f'服务返回同步时间：{date_text(data["sync_at"])}')
    limitations = list(data.get("limitations", []))
    excluded = len(rows) - len(valid)
    if excluded:
        limitations.append(f'{excluded} 项未进入可比排名；具体原因见行情明细。')
    if not rows:
        limitations.append('本期未取得行情记录，不构成完整行情报告。')
    if not events:
        limitations.append('本报告未列示已核验事件，不代表观察区间内没有重要事件。')
    limitations = list(dict.fromkeys(limitations))
    method_notes = list(data["method_notes"])
    if endpoint_note not in method_notes:
        method_notes.append(endpoint_note)
    level = data.get("risk_level", "enhanced")
    disclosure = risk_disclaimer(level)
    replacements = {
        "CSS": (ROOT / "assets/report.css").read_text(encoding="utf-8"), "TITLE": text(data["title"]),
        "RISK_LEVEL": level, "SUBTITLE": text(data["subtitle"]),
        "EDITION": {"holiday": "假期外盘观察", "custom_interval": "自定义区间观察", "simulated_holiday": "假期场景模拟"}[scenario] + (" · 行情版" if rows and not events else ""),
        "DEMO": f'<p class="banner">{text(banner)}</p>' if banner else "",
        "META": "".join(f'<div>{text(m)}</div>' for m in meta),
        "LIMITATIONS": '<aside class="warning">' + "".join(f'<p>{text(x)}</p>' for x in limitations) + '</aside>' if limitations else "",
        "TAKEAWAYS": cards(data["takeaways"], "takeaway"),
        "COVERAGE": text(f'{data["coverage_note"]} 本次列示 {len(rows)} 项，{len(valid)} 项纳入排名；涨跌按原币种计算。'),
        "CHART": "".join(chart), "COUNT": str(len(rows)), "ROWS": "".join(rows),
        "EVENTS_SECTION": '<section><div class="section-head"><span>03</span><h2>重要事件</h2></div>' + "".join(events) + '</section>' if events else "",
        "OBSERVATIONS_NUMBER": "04" if events else "03",
        "OBSERVATIONS": cards(data["observations"], "observation"),
        "METHOD": "".join(f'<p class="method">{text(m)}</p>' for m in method_notes),
        "DISCLAIMER": text(disclosure),
    }
    template = (ROOT / "assets/report.html").read_text(encoding="utf-8")
    html = re.sub(r"@@([A-Z_]+)@@", lambda match: replacements[match[1]], template)
    evidence = dict(data, scenario=scenario, endpoint_mode=endpoint_mode, method_notes=method_notes,
                    limitations=limitations, risk_level=level, risk_disclaimer=disclosure)
    return html, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    evidence_path = args.output.with_suffix(".evidence.json")
    if args.input.resolve() in (args.output.resolve(), evidence_path.resolve()):
        parser.error("输入路径不能与输出 HTML 或底稿路径相同")
    html, evidence = render(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 {args.output}")


if __name__ == "__main__":
    main()
