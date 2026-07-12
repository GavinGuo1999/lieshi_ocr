"""Build a read-only OCR/Excel diagnostic report for human review."""

from __future__ import annotations

from datetime import datetime
from html import escape
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

from lieshi_ocr.excel.index import index_rows_by_code, load_workbook_sheet
from lieshi_ocr.excel.rules import comparable

JsonDict = dict[str, Any]


def build_ocr_audit(
    text_manifest_path: str | Path,
    records_path: str | Path,
    base_xlsx: str | Path,
) -> JsonDict:
    """Compare OCR values with a trusted workbook without modifying it."""

    text_path = Path(text_manifest_path)
    correction_path = Path(records_path)
    text_payload = _load_object(text_path)
    records_payload = _load_object(correction_path)
    text_regions = _index_text_regions(text_payload.get("records", []))
    raw_records = records_payload.get("records", [])
    if not isinstance(raw_records, list):
        raise ValueError("correction_records.json field 'records' must be a list")

    workbook, sheet = load_workbook_sheet(base_xlsx)
    try:
        excel_index = index_rows_by_code(sheet)
        audit_records = [
            _build_audit_record(record, text_regions, excel_index)
            for record in raw_records
            if isinstance(record, dict)
        ]
    finally:
        workbook.close()

    status_counts: dict[str, int] = {}
    for record in audit_records:
        status = str(record["name"]["match_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "text_manifest": text_path.as_posix(),
            "records": correction_path.as_posix(),
            "base_xlsx": Path(base_xlsx).as_posix(),
        },
        "summary": {
            "record_count": len(audit_records),
            "code_found": sum(1 for record in audit_records if record["code"]["excel_exists"]),
            "code_not_found": sum(1 for record in audit_records if not record["code"]["excel_exists"]),
            "name_status_counts": status_counts,
        },
        "records": audit_records,
    }


def write_ocr_audit_outputs(report: JsonDict, out_dir: str | Path) -> tuple[Path, Path]:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "ocr_audit_report.json"
    html_path = target_dir / "ocr_audit_report.html"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_ocr_audit_html(report, html_path.parent), encoding="utf-8")
    return json_path, html_path


def clean_ocr_name(value: object) -> str:
    """Apply only safe label, whitespace, and punctuation cleanup."""

    text = "" if value is None else str(value)
    text = re.sub(r"^\s*姓名\s*[:：]?\s*", "", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[:：,，.。;；|｜]+", "", text)
    return text


def render_ocr_audit_html(report: JsonDict, report_dir: str | Path) -> str:
    summary = report.get("summary", {})
    records = report.get("records", [])
    sections = "\n".join(_render_record(record, Path(report_dir)) for record in records if isinstance(record, dict))
    status_counts = summary.get("name_status_counts", {})
    status_text = "，".join(f"{key}: {value}" for key, value in sorted(status_counts.items())) or "无"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OCR 审计报告</title>
  <style>
    :root {{ color-scheme: light; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }}
    body {{ margin: 0; background: #f4f5f7; color: #202124; }}
    header {{ background: #183153; color: white; padding: 24px max(24px, calc((100% - 1120px) / 2)); }}
    header h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 4px 0; color: #dbe6f3; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .metric {{ background: white; border: 1px solid #d9dde3; border-radius: 6px; padding: 16px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    .record {{ background: white; border: 1px solid #d9dde3; border-radius: 6px; margin: 0 0 18px; overflow: hidden; }}
    .record > h2 {{ margin: 0; padding: 14px 18px; font-size: 19px; background: #eef2f6; border-bottom: 1px solid #d9dde3; }}
    .record-body {{ padding: 18px; }}
    .status {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: 600; }}
    .status-match {{ background: #dff3e4; color: #176b35; }}
    .status-mismatch {{ background: #fbe1e1; color: #9d2424; }}
    .status-review {{ background: #fff0cc; color: #765300; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 18px; table-layout: fixed; }}
    th, td {{ border: 1px solid #d9dde3; padding: 9px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ background: #f7f8fa; width: 23%; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0 18px; }}
    a {{ color: #075ea8; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f7f8fa; border: 1px solid #d9dde3; padding: 12px; max-height: 340px; overflow: auto; }}
    .warnings {{ margin: 8px 0 16px; padding-left: 20px; }}
    textarea {{ width: 100%; min-height: 90px; box-sizing: border-box; resize: vertical; padding: 10px; border: 1px solid #aeb5bf; border-radius: 4px; font: inherit; }}
    details {{ margin: 12px 0; }}
    @media (max-width: 720px) {{ .summary {{ grid-template-columns: 1fr; }} main {{ padding: 12px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>OCR 审计报告</h1>
    <p>只读诊断：编号定位与姓名校验均保持精确匹配，不执行 Excel 修改。</p>
    <p>生成时间：{escape(str(report.get("generated_at", "")))}</p>
  </header>
  <main>
    <div class="summary">
      <div class="metric">记录数<strong>{int(summary.get("record_count", 0))}</strong></div>
      <div class="metric">Excel 中找到编号<strong>{int(summary.get("code_found", 0))}</strong></div>
      <div class="metric">姓名状态<strong style="font-size:16px">{escape(status_text)}</strong></div>
    </div>
    {sections}
  </main>
  <script>
    document.querySelectorAll('textarea[data-audit-key]').forEach((field) => {{
      const key = 'lieshi-ocr-audit:' + location.pathname + ':' + field.dataset.auditKey;
      field.value = localStorage.getItem(key) || '';
      field.addEventListener('input', () => localStorage.setItem(key, field.value));
    }});
  </script>
</body>
</html>
"""


def _build_audit_record(record: JsonDict, text_regions: dict[str, dict[str, JsonDict]], excel_index: dict[str, Any]) -> JsonDict:
    source_stem = _text(record.get("source_stem"))
    regions = text_regions.get(source_stem, {})
    code_region = regions.get("code", {})
    name_region = regions.get("name", {})
    correction_region = regions.get("correction", {})
    record_regions = record.get("regions", {}) if isinstance(record.get("regions"), dict) else {}

    code = _text(record.get("code"))
    record_name = _text(record.get("name"))
    name_ocr = _text(name_region.get("text")) or _nested_text(record_regions, "name", "text") or record_name
    cleaned_name = clean_ocr_name(name_ocr)
    indexed = excel_index.get(code) if code else None
    expected_name = indexed.name if indexed is not None else ""
    match_status = _name_match_status(code, record_name, indexed)
    warnings = _string_list(record.get("warnings", []))
    if match_status == "name_mismatch" and "name_mismatch" not in warnings:
        warnings.append("name_mismatch")

    fields = record.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}
    raw_text = _text(record.get("raw_text")) or _text(correction_region.get("text"))
    text_source = _text(correction_region.get("text_source")) or _nested_text(record_regions, "correction", "text_source")

    return {
        "source_stem": source_stem,
        "source_pdf": _text(record.get("source_pdf")),
        "code": {
            "ocr_raw": _text(code_region.get("text")) or _nested_text(record_regions, "code", "text"),
            "record_value": code,
            "confidence": _number(code_region.get("confidence", _nested_value(record_regions, "code", "confidence"))),
            "excel_exists": indexed is not None,
            "excel_row": indexed.row if indexed is not None else 0,
        },
        "name": {
            "ocr_raw": name_ocr,
            "record_value": record_name,
            "cleaned": cleaned_name,
            "confidence": _number(name_region.get("confidence", _nested_value(record_regions, "name", "confidence"))),
            "excel_expected": expected_name,
            "match_status": match_status,
            "cleaned_matches_excel": bool(expected_name and comparable(expected_name) == comparable(cleaned_name)),
        },
        "links": {
            "source_pdf": _text(record.get("source_pdf")),
            "code_crop": _text(code_region.get("crop_pdf")) or _nested_text(record_regions, "code", "crop_pdf"),
            "name_crop": _text(name_region.get("crop_pdf")) or _nested_text(record_regions, "name", "crop_pdf"),
            "correction_crop": _text(correction_region.get("crop_pdf")) or _nested_text(record_regions, "correction", "crop_pdf"),
            "mineru_text_source": text_source,
        },
        "raw_text": raw_text,
        "fields": {str(key): _text(value) for key, value in fields.items()},
        "warnings": warnings,
        "manual_conclusion": "",
    }


def _render_record(record: JsonDict, report_dir: Path) -> str:
    code = record.get("code", {})
    name = record.get("name", {})
    links = record.get("links", {})
    fields = record.get("fields", {})
    warnings = record.get("warnings", [])
    source_stem = _text(record.get("source_stem"))
    status = _text(name.get("match_status"))
    status_label = {
        "match": "匹配",
        "name_mismatch": "姓名不一致",
        "name_missing": "姓名缺失",
        "code_missing": "编号缺失",
        "code_not_found": "编号未在 Excel 中找到",
    }.get(status, status or "待复核")
    status_class = "status-match" if status == "match" else "status-mismatch" if status == "name_mismatch" else "status-review"
    field_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(_text(value))}</td></tr>"
        for key, value in fields.items()
        if _text(value)
    ) or '<tr><td colspan="2">无解析候选字段</td></tr>'
    warning_items = "".join(f"<li>{escape(_text(item))}</li>" for item in warnings) or "<li>无</li>"
    link_items = "".join(
        _render_link(label, _text(links.get(key)), report_dir)
        for key, label in (
            ("source_pdf", "原始 PDF"),
            ("code_crop", "编号 crop"),
            ("name_crop", "姓名 crop"),
            ("correction_crop", "修正内容 crop"),
            ("mineru_text_source", "MinerU 原文"),
        )
    )
    return f"""
    <section class="record">
      <h2>{escape(_text(code.get("record_value")) or "编号缺失")} / {escape(_text(name.get("record_value")) or "姓名缺失")}</h2>
      <div class="record-body">
        <p><span class="status {status_class}">{escape(status_label)}</span></p>
        <table>
          <tr><th>OCR 编号</th><td>{escape(_text(code.get("ocr_raw")))}</td></tr>
          <tr><th>编号置信度</th><td>{_format_confidence(code.get("confidence"))}</td></tr>
          <tr><th>编号在 Excel 中存在</th><td>{'是' if code.get('excel_exists') else '否'}（行 {int(code.get('excel_row', 0)) or '-'}）</td></tr>
          <tr><th>OCR 姓名</th><td>{escape(_text(name.get("ocr_raw")))}</td></tr>
          <tr><th>安全清洗后姓名</th><td>{escape(_text(name.get("cleaned")))}</td></tr>
          <tr><th>Excel D 列预期姓名</th><td>{escape(_text(name.get("excel_expected")))}</td></tr>
          <tr><th>姓名置信度</th><td>{_format_confidence(name.get("confidence"))}</td></tr>
        </table>
        <div class="links">{link_items}</div>
        <details open><summary>Parser 候选字段</summary><table>{field_rows}</table></details>
        <details><summary>MinerU / correction 原文</summary><pre>{escape(_text(record.get("raw_text")))}</pre></details>
        <h3>Warnings</h3><ul class="warnings">{warning_items}</ul>
        <label for="manual-{escape(source_stem, quote=True)}"><strong>人工结论</strong></label>
        <textarea id="manual-{escape(source_stem, quote=True)}" data-audit-key="{escape(source_stem, quote=True)}"></textarea>
      </div>
    </section>"""


def _render_link(label: str, path_value: str, report_dir: Path) -> str:
    if not path_value:
        return f"<span>{escape(label)}：不可用</span>"
    target = Path(path_value)
    absolute = target if target.is_absolute() else (Path.cwd() / target)
    relative = Path(os.path.relpath(absolute.resolve(strict=False), report_dir.resolve(strict=False))).as_posix()
    href = quote(relative, safe="/:")
    suffix = "" if absolute.exists() else "（文件不存在）"
    return f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener">{escape(label)}</a>{escape(suffix)}'


def _name_match_status(code: str, name: str, indexed: Any) -> str:
    if not code:
        return "code_missing"
    if indexed is None:
        return "code_not_found"
    if not name:
        return "name_missing"
    return "match" if comparable(indexed.name) == comparable(name) else "name_mismatch"


def _index_text_regions(records: Any) -> dict[str, dict[str, JsonDict]]:
    index: dict[str, dict[str, JsonDict]] = {}
    if not isinstance(records, list):
        return index
    for record in records:
        if not isinstance(record, dict):
            continue
        source_stem = _text(record.get("source_stem"))
        region = _text(record.get("region"))
        if source_stem and region:
            index.setdefault(source_stem, {}).setdefault(region, record)
    return index


def _load_object(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _nested_value(regions: Any, region: str, key: str) -> Any:
    if not isinstance(regions, dict):
        return ""
    value = regions.get(region, {})
    return value.get(key, "") if isinstance(value, dict) else ""


def _nested_text(regions: Any, region: str, key: str) -> str:
    return _text(_nested_value(regions, region, key))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _format_confidence(value: Any) -> str:
    return f"{_number(value):.3f}"
