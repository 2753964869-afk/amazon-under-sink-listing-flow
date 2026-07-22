#!/usr/bin/env python3
"""Export Amazon Reviews API logs and Chinese translations to a portable XLSX."""

from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


REVIEW_COLUMNS = [
    ("asin", "ASIN"),
    ("brand", "品牌"),
    ("sentiment_zh", "评价分类"),
    ("sentiment", "评价分类 (EN)"),
    ("rating", "星级"),
    ("review_title_original", "原始标题"),
    ("review_title_zh", "中文标题"),
    ("review_description_original", "原始评论"),
    ("review_description_zh", "中文翻译"),
    ("commentator", "评论者"),
    ("commenter_profile_link", "评论者主页"),
    ("published_at", "发布日期"),
    ("country", "国家"),
    ("variant", "变体"),
    ("is_verified", "已验证购买"),
    ("review_url", "评论链接"),
    ("source_file", "源文件"),
    ("source_index", "源序号"),
]

SUMMARY_COLUMNS = [
    "ASIN",
    "品牌",
    "评论总数",
    "好评数",
    "中评数",
    "差评数",
    "平均星级",
]

INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")
INVALID_XML_CHARS = re.compile("[\x00-\x08\x0B\x0C\x0E-\x1F]")
REVIEW_TITLE_KEYS = ("review_title", "reviewTitle", "review Title")
REVIEW_DESCRIPTION_KEYS = ("review_description", "review Description", "reviewDescription")


def parse_review_log(text: str) -> list[dict]:
    """Return the last schema-valid review array found in BrowserAct output."""
    decoder = json.JSONDecoder()
    candidates = []
    for position, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[position:])
        except json.JSONDecodeError:
            continue
        collect_review_arrays(value, candidates)
    non_empty = [candidate for candidate in candidates if candidate]
    if non_empty:
        return non_empty[-1]
    if candidates:
        return candidates[-1]
    raise ValueError("No JSON review array found in Amazon Reviews API output")


def collect_review_arrays(value, candidates: list[list[dict]]) -> None:
    if isinstance(value, list):
        if not value or all(is_review_record(item) for item in value):
            candidates.append(value)
        for item in value:
            collect_review_arrays(item, candidates)
        return
    if isinstance(value, dict):
        for item in value.values():
            collect_review_arrays(item, candidates)
        return
    if isinstance(value, str) and value.lstrip().startswith(("[", "{")):
        try:
            nested = json.loads(value)
        except json.JSONDecodeError:
            return
        collect_review_arrays(nested, candidates)


def is_review_record(value) -> bool:
    if not isinstance(value, dict) or "rating" not in value:
        return False
    return any(key in value for key in REVIEW_TITLE_KEYS + REVIEW_DESCRIPTION_KEYS)


def parse_rating(rating) -> int:
    try:
        score = float(rating)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Rating must be a finite whole number from 1 to 5, got {rating!r}") from exc
    if not math.isfinite(score) or not score.is_integer() or score < 1 or score > 5:
        raise ValueError(f"Rating must be a finite whole number from 1 to 5, got {rating!r}")
    return int(score)


def classify_sentiment(rating) -> tuple[str, str]:
    score = parse_rating(rating)
    if score >= 4:
        return "Positive", "好评"
    if score == 3:
        return "Neutral", "中评"
    return "Negative", "差评"


def parse_verified_purchase(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "y", "1", "verified", "是"}:
            return True
        if normalized in {"false", "no", "n", "0", "", "unverified", "否"}:
            return False
    raise ValueError(f"Invalid verified-purchase value: {value!r}")


def source_basename(source_file) -> str:
    return str(source_file or "").replace("\\", "/").rsplit("/", 1)[-1]


def first_value(raw: dict, *keys: str, default=""):
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return default


def normalize_review(
    *,
    raw: dict,
    asin: str,
    brand: str,
    source_file: str,
    source_index: int,
    translation: dict,
) -> dict:
    if not isinstance(translation, dict):
        raise ValueError(f"Chinese translation #{source_index} for {asin} must be an object")
    if "title_zh" not in translation or "description_zh" not in translation:
        raise ValueError(
            f"Chinese translation #{source_index} for {asin} must include title_zh and description_zh"
        )

    rating = parse_rating(first_value(raw, "rating"))
    sentiment, sentiment_zh = classify_sentiment(rating)
    return {
        "asin": str(asin),
        "brand": str(brand or ""),
        "sentiment_zh": sentiment_zh,
        "sentiment": sentiment,
        "rating": float(rating),
        "review_title_original": str(
            first_value(raw, "review_title", "reviewTitle", "review Title")
        ),
        "review_title_zh": str(translation.get("title_zh", "")),
        "review_description_original": str(
            first_value(raw, "review_description", "review Description", "reviewDescription")
        ),
        "review_description_zh": str(translation.get("description_zh", "")),
        "commentator": str(first_value(raw, "commentator", "Commentator")),
        "commenter_profile_link": str(
            first_value(raw, "commenter_profile_link", "Commenter profile link")
        ),
        "published_at": str(first_value(raw, "published_at", "Published at")),
        "country": str(first_value(raw, "country", "Country")),
        "variant": str(first_value(raw, "variant", "Variant")),
        "is_verified": parse_verified_purchase(
            first_value(raw, "is_verified", "Is Verified", default=False)
        ),
        "review_url": str(first_value(raw, "review_url", "Review URL")),
        "source_file": source_basename(source_file),
        "source_index": int(source_index),
    }


def load_manifest(manifest_path: Path) -> list[dict]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    products = manifest.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("Manifest must contain a non-empty products array")

    normalized = []
    for product in products:
        asin = str(product.get("asin", "")).strip()
        if not asin:
            raise ValueError("Every product must include an ASIN")
        reviews_file = Path(str(product.get("reviews_file", "")))
        if not reviews_file.is_absolute():
            reviews_file = manifest_path.parent / reviews_file
        if not reviews_file.exists():
            raise FileNotFoundError(f"Review file not found for {asin}: {reviews_file}")

        reviews = parse_review_log(reviews_file.read_text(encoding="utf-8-sig"))
        translations = product.get("translations")
        if not isinstance(translations, list) or len(translations) != len(reviews):
            actual = len(translations) if isinstance(translations, list) else 0
            raise ValueError(
                f"Chinese translation count for {asin} must equal review count "
                f"({len(reviews)}), got {actual}"
            )

        for index, (review, translation) in enumerate(zip(reviews, translations), start=1):
            normalized.append(
                normalize_review(
                    raw=review,
                    asin=asin,
                    brand=str(product.get("brand", "")),
                    source_file=reviews_file.name,
                    source_index=index,
                    translation=translation,
                )
            )
    return normalized


def export_manifest(manifest_path: Path, output_path: Path) -> Path:
    rows = load_manifest(Path(manifest_path))
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    products = defaultdict(list)
    for row in rows:
        products[row["asin"]].append(row)

    sheets = [("Summary", build_summary_rows(products))]
    all_rows = sorted(rows, key=review_sort_key)
    sheets.append(("All Reviews", build_review_rows(all_rows)))
    for asin, asin_rows in products.items():
        sheets.append((asin, build_review_rows(sorted(asin_rows, key=review_sort_key))))

    safe_sheets = unique_sheet_names(sheets)
    write_xlsx(output_path, safe_sheets)
    return output_path


def review_sort_key(row: dict):
    return (row["asin"], -float(row["rating"]), row["source_index"])


def build_summary_rows(products: dict[str, list[dict]]) -> list[list]:
    rows = [SUMMARY_COLUMNS]
    for asin in sorted(products):
        reviews = products[asin]
        counts = defaultdict(int)
        for review in reviews:
            counts[review["sentiment"]] += 1
        average = sum(float(review["rating"]) for review in reviews) / len(reviews)
        rows.append([
            asin,
            reviews[0]["brand"],
            len(reviews),
            counts["Positive"],
            counts["Neutral"],
            counts["Negative"],
            round(average, 2),
        ])
    return rows


def build_review_rows(reviews: list[dict]) -> list[list]:
    rows = [[header for _, header in REVIEW_COLUMNS]]
    for review in reviews:
        values = []
        for key, _ in REVIEW_COLUMNS:
            value = review.get(key, "")
            if key == "is_verified":
                value = "是" if value else "否"
            values.append(value)
        rows.append(values)
    return rows


def unique_sheet_names(sheets: list[tuple[str, list[list]]]) -> list[tuple[str, list[list]]]:
    used = set()
    result = []
    for raw_name, rows in sheets:
        base = INVALID_SHEET_CHARS.sub("_", str(raw_name)).strip(" '") or "Sheet"
        base = base[:31]
        name = base
        counter = 2
        while name.casefold() in used:
            suffix = f"_{counter}"
            name = f"{base[:31 - len(suffix)]}{suffix}"
            counter += 1
        used.add(name.casefold())
        result.append((name, rows))
    return result


def write_xlsx(output_path: Path, sheets: list[tuple[str, list[list]]]) -> None:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", root_relationships_xml())
        archive.writestr("docProps/core.xml", core_properties_xml(created))
        archive.writestr("docProps/app.xml", app_properties_xml([name for name, _ in sheets]))
        archive.writestr("xl/workbook.xml", workbook_xml([name for name, _ in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (name, rows) in enumerate(sheets, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                worksheet_xml(rows, is_summary=name == "Summary"),
            )


def content_types_xml(sheet_count: int) -> str:
    worksheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return xml_document(
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        f"{worksheet_overrides}</Types>"
    )


def root_relationships_xml() -> str:
    return xml_document(
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def core_properties_xml(created: str) -> str:
    return xml_document(
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def app_properties_xml(sheet_names: list[str]) -> str:
    titles = "".join(f"<vt:lpstr>{escape_xml(name)}</vt:lpstr>" for name in sheet_names)
    return xml_document(
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Codex</Application>'
        f'<TitlesOfParts><vt:vector size="{len(sheet_names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>'
        '</Properties>'
    )


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f"<sheet name={quoteattr(name)} sheetId=\"{index}\" r:id=\"rId{index}\"/>"
        for index, name in enumerate(sheet_names, start=1)
    )
    return xml_document(
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets><calcPr calcId=\"191029\" fullCalcOnLoad=\"1\"/>"
        '</workbook>'
    )


def workbook_relationships_xml(sheet_count: int) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    )
    relationships += (
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return xml_document(
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}</Relationships>"
    )


def styles_xml() -> str:
    return xml_document(
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Arial"/><family val="2"/></font>'
        '<font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Arial"/><family val="2"/></font>'
        '</fonts>'
        '<fills count="5">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF16324F"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFE7F5EC"/><bgColor indexed="64"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF4CC"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="7">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def worksheet_xml(rows: list[list], *, is_summary: bool) -> str:
    max_columns = max((len(row) for row in rows), default=1)
    max_rows = max(len(rows), 1)
    end_cell = f"{column_name(max_columns)}{max_rows}"
    widths = summary_widths(max_columns) if is_summary else review_widths(max_columns)
    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{column_name(column_index)}{row_index}"
            style = cell_style(row_index, column_index, row, is_summary)
            cells.append(cell_xml(reference, value, style))
        height = ' ht="30" customHeight="1"' if row_index == 1 else ''
        row_xml.append(f'<row r="{row_index}"{height}>{"".join(cells)}</row>')
    auto_filter = f'<autoFilter ref="A1:{end_cell}"/>' if rows else ""
    return xml_document(
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{end_cell}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'<cols>{columns}</cols><sheetData>{"".join(row_xml)}</sheetData>{auto_filter}'
        '<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
        '</worksheet>'
    )


def cell_style(row_index: int, column_index: int, row: list, is_summary: bool) -> int:
    if row_index == 1:
        return 1
    if is_summary:
        return 6 if column_index == 7 else 5
    if column_index == 3:
        sentiment = str(row[column_index - 1])
        if sentiment == "好评":
            return 3
        if sentiment == "中评":
            return 4
        return 5
    if column_index in (5, 15, 18):
        return 5
    return 2


def cell_xml(reference: str, value, style: int) -> str:
    if isinstance(value, bool):
        return f'<c r="{reference}" s="{style}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}" s="{style}"><v>{value}</v></c>'
    text = escape_xml(value)
    return (
        f'<c r="{reference}" s="{style}" t="inlineStr">'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def review_widths(count: int) -> list[float]:
    configured = [
        14, 14, 10, 14, 8, 28, 28, 55, 55,
        18, 38, 16, 15, 24, 12, 38, 38, 10,
    ]
    return (configured + [16] * count)[:count]


def summary_widths(count: int) -> list[float]:
    configured = [16, 18, 12, 12, 12, 12, 12]
    return (configured + [14] * count)[:count]


def column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def escape_xml(value) -> str:
    text = INVALID_XML_CHARS.sub("", str(value if value is not None else ""))
    return escape(text)


def xml_document(body: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Review workbook manifest JSON")
    parser.add_argument("--output", required=True, help="Output XLSX path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = export_manifest(Path(args.manifest), Path(args.output))
    print(output)


if __name__ == "__main__":
    main()
