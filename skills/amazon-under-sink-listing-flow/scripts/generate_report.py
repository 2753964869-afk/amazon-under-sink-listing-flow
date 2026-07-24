#!/usr/bin/env python3
"""Generate a standalone escaped HTML report from structured JSON."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


MAX_TABLE_ROWS = 200
MAX_BAR_ITEMS = 20
MAX_QA_ITEMS = 50


def escape(value) -> str:
    return html.escape(str("" if value is None else value), quote=True)


def render_metric(item) -> str:
    if not isinstance(item, dict):
        item = {}
    hint = f'<div class="hint">{escape(item.get("hint"))}</div>' if item.get("hint") else ""
    return (
        '<div class="metric">'
        f'<div class="label">{escape(item.get("label"))}</div>'
        f'<div class="value">{escape(item.get("value"))}</div>'
        f"{hint}</div>"
    )


def render_basis(section) -> str:
    basis = section.get("basis")
    if not basis:
        return ""
    if isinstance(basis, list):
        body = "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in basis) + "</ul>"
    else:
        body = f'<p class="prewrap">{escape(basis)}</p>'
    return f'<div class="basis"><div class="basis-title">判断依据</div>{body}</div>'


def render_qa_items(section) -> str:
    items = section.get("items") if isinstance(section.get("items"), list) else []
    cards = []
    for item in items[:MAX_QA_ITEMS]:
        if not isinstance(item, dict):
            continue
        question = item.get("question") or item.get("q")
        answer = item.get("answer") or item.get("a")
        if not question and not answer:
            continue
        meta_parts = []
        for label, key in (("推荐原因", "basis"), ("关键词", "keywords"), ("场景", "scenario"), ("优先级", "priority")):
            value = item.get(key)
            if isinstance(value, list):
                value = ", ".join(str(part) for part in value if part)
            if value:
                meta_parts.append(f'<span><strong>{escape(label)}:</strong> {escape(value)}</span>')
        meta = f'<div class="qa-meta">{"".join(meta_parts)}</div>' if meta_parts else ""
        cards.append(
            '<div class="qa-card">'
            f'<div class="qa-question"><span>Q</span>{escape(question)}</div>'
            f'<div class="qa-answer"><span>A</span>{escape(answer)}</div>'
            f"{meta}</div>"
        )
    return '<div class="qa-list">' + "".join(cards) + "</div>"


def render_section(section) -> str:
    if not isinstance(section, dict):
        section = {}
    section_type = section.get("type", "text")
    title = escape(section.get("title") or "分析")
    if section_type == "insights":
        items = section.get("items") if isinstance(section.get("items"), list) else []
        body = "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"
    elif section_type == "table":
        columns = section.get("columns") if isinstance(section.get("columns"), list) else []
        rows = section.get("rows") if isinstance(section.get("rows"), list) else []
        head = "".join(f"<th>{escape(column)}</th>" for column in columns)
        body_rows = []
        for row in rows[:MAX_TABLE_ROWS]:
            cells = row if isinstance(row, list) else []
            body_rows.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>")
        body = f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'
    elif section_type == "bars":
        items = section.get("items") if isinstance(section.get("items"), list) else []
        items = [item for item in items[:MAX_BAR_ITEMS] if isinstance(item, dict)]
        maximum = max((float(item.get("value") or 0) for item in items), default=1) or 1
        rows = []
        for item in items:
            value = float(item.get("value") or 0)
            width = max(2, min(100, round(value / maximum * 100)))
            rows.append(
                '<div class="bar-row">'
                f'<div class="bar-label">{escape(item.get("label"))}</div>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>'
                f'<div class="bar-value">{escape(item.get("value"))}</div></div>'
            )
        body = "".join(rows)
    elif section_type == "metrics":
        items = section.get("items") if isinstance(section.get("items"), list) else []
        body = '<div class="metrics">' + "".join(render_metric(item) for item in items) + "</div>"
    elif section_type == "qa":
        body = render_qa_items(section)
    else:
        body = f'<p class="prewrap">{escape(section.get("content"))}</p>'
    return f"<section><h2>{title}</h2>{body}{render_basis(section)}</section>"


def render_html(report: dict) -> str:
    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object")
    title = str(report.get("title", "")).strip()
    if not title:
        raise ValueError("Report title is required")
    subtitle = str(report.get("subtitle", "")).strip()
    summary = report.get("summary") if isinstance(report.get("summary"), list) else []
    sections = report.get("sections") if isinstance(report.get("sections"), list) else []
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    source = report.get("source")
    generated_at = report.get("generatedAt")
    meta = "".join(
        value for value in (
            f"<span>数据来源：{escape(source)}</span>" if source else "",
            f"<span>生成时间：{escape(generated_at)}</span>" if generated_at else "",
        ) if value
    )
    summary_html = (
        '<div class="metrics">' + "".join(render_metric(item) for item in summary) + "</div>"
        if summary else ""
    )
    notes_html = (
        '<section class="notes"><h2>说明</h2><ul>'
        + "".join(f"<li>{escape(note)}</li>" for note in notes)
        + "</ul></section>"
        if notes else ""
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f7fb;color:#1f2937;font-family:Arial,"Microsoft YaHei",sans-serif}}
header{{padding:26px 32px;background:#16324f;color:#fff}}h1{{margin:0 0 8px;font-size:28px;letter-spacing:0}}h2{{margin:0 0 14px;font-size:18px}}
.subtitle,.meta{{color:#d9e5f2;font-size:14px;line-height:22px}}.meta{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px;font-size:13px}}
.meta span{{padding:4px 8px;border:1px solid rgba(255,255,255,.28);border-radius:6px}}main{{max-width:1180px;margin:0 auto;padding:22px}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px}}.metric,section{{background:#fff;border:1px solid #dce3ec;border-radius:8px}}
.metric{{padding:14px}}.label{{color:#64748b;font-size:13px}}.value{{margin-top:7px;color:#0f172a;font-size:24px;font-weight:700;word-break:break-word}}
.hint{{margin-top:5px;color:#64748b;font-size:12px;line-height:18px}}section{{margin-bottom:16px;padding:16px;overflow:hidden}}ul{{margin:0;padding-left:20px}}li,p{{line-height:24px}}
.prewrap{{margin:0;white-space:pre-wrap}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:9px 10px;border-bottom:1px solid #e5eaf1;text-align:left;vertical-align:top}}
th{{background:#f1f5f9;color:#334155;position:sticky;top:0}}.table-wrap{{max-height:560px;overflow:auto;border:1px solid #edf1f6;border-radius:6px}}
.bar-row{{display:grid;grid-template-columns:minmax(140px,32%) 1fr auto;gap:10px;align-items:center;margin:10px 0}}.bar-track{{height:12px;border-radius:999px;background:#e2e8f0;overflow:hidden}}
.bar-fill{{height:100%;background:#0f766e}}.bar-value{{min-width:48px;text-align:right;font-weight:700;font-size:13px}}.notes{{color:#475569;font-size:13px}}
.basis{{margin-top:14px;padding:12px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;color:#334155;font-size:13px}}.basis-title{{margin-bottom:6px;color:#0f172a;font-weight:700}}
.qa-list{{display:grid;gap:12px}}.qa-card{{padding:13px 14px;border:1px solid #e2e8f0;border-radius:6px;background:#fbfdff}}.qa-question,.qa-answer{{display:grid;grid-template-columns:24px 1fr;gap:8px;line-height:22px}}.qa-question{{font-weight:700;color:#0f172a}}.qa-answer{{margin-top:8px;color:#334155}}.qa-question span,.qa-answer span{{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:#e0f2fe;color:#075985;font-size:12px}}.qa-answer span{{background:#dcfce7;color:#166534}}.qa-meta{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;color:#64748b;font-size:12px}}.qa-meta span{{padding:4px 7px;border:1px solid #e2e8f0;border-radius:999px;background:#fff}}
@media(max-width:760px){{header{{padding:20px}}main{{padding:14px}}.bar-row{{grid-template-columns:1fr;gap:4px}}.bar-value{{text-align:left}}}}
</style></head><body><header><h1>{escape(title)}</h1>{f'<div class="subtitle">{escape(subtitle)}</div>' if subtitle else ''}<div class="meta">{meta}</div></header>
<main>{summary_html}{''.join(render_section(section) for section in sections)}{notes_html}</main></body></html>'''


def generate_report(input_path, output_path) -> Path:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    report = json.loads(input_path.read_text(encoding="utf-8-sig"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_html(report))
    return output_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Structured report JSON")
    parser.add_argument("--output", required=True, help="Standalone HTML output")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    print(generate_report(args.input, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
