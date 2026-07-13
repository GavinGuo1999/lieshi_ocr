"""Build a read-only audit report for Excel story candidates."""

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
from lieshi_ocr.excel.rules import COL_STORY, COL_STORY_BACKUP, STORY_REVIEW_LENGTH, comparable
from lieshi_ocr.parse.correction_text import DATE_PATTERN

JsonDict = dict[str, Any]


def build_story_candidate_audit(
    records_path: str | Path,
    dry_run_path: str | Path,
    base_xlsx: str | Path,
) -> JsonDict:
    """Join review records, dry-run K candidates, and current v4 K/T values."""

    records_file = Path(records_path)
    dry_run_file = Path(dry_run_path)
    records_payload = _load_object(records_file)
    dry_run_payload = _load_object(dry_run_file)
    records = records_payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("correction_records.json field 'records' must be a list")

    candidates = _index_story_candidates(dry_run_payload)
    workbook, sheet = load_workbook_sheet(base_xlsx)
    try:
        excel_index = index_rows_by_code(sheet)
        audit_records = [
            _build_record(record, candidates, excel_index, sheet)
            for record in records
            if isinstance(record, dict)
        ]
    finally:
        workbook.close()

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "records": records_file.as_posix(),
            "dry_run": dry_run_file.as_posix(),
            "base_xlsx": Path(base_xlsx).as_posix(),
        },
        "summary": {
            "record_count": len(audit_records),
            "proposed_story_count": sum(1 for item in audit_records if item["candidate"]["status"] == "proposed"),
            "blocked_story_count": sum(1 for item in audit_records if item["candidate"]["status"] == "blocked"),
            "missing_story_count": sum(1 for item in audit_records if item["candidate"]["status"] == "missing"),
            "long_story_count": sum(1 for item in audit_records if item["candidate"]["length"] > STORY_REVIEW_LENGTH),
            "multiple_date_count": sum(1 for item in audit_records if len(item["date_candidates"]) > 1),
        },
        "records": audit_records,
    }


def write_story_candidate_audit_outputs(report: JsonDict, out_dir: str | Path) -> tuple[Path, Path]:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "story_candidate_audit.json"
    html_path = target_dir / "story_candidate_audit.html"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_story_candidate_audit_html(report, html_path.parent), encoding="utf-8")
    return json_path, html_path


def render_story_candidate_audit_html(report: JsonDict, report_dir: str | Path) -> str:
    summary = report.get("summary", {})
    records = report.get("records", [])
    sections = "\n".join(
        _render_record(item, Path(report_dir)) for item in records if isinstance(item, dict)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>事迹候选审计报告</title>
  <style>
    :root {{ color-scheme: light; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }}
    body {{ margin: 0; background: #f3f5f7; color: #202124; }}
    header {{ background: #243447; color: white; padding: 24px max(24px, calc((100% - 1180px) / 2)); }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 4px 0; color: #dbe4ed; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    .summary {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin-bottom: 20px; }}
    .metric {{ background: white; border: 1px solid #d7dce2; border-radius: 6px; padding: 14px; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 24px; }}
    .record {{ background: white; border: 1px solid #d7dce2; border-radius: 6px; margin-bottom: 18px; overflow: hidden; }}
    .record > h2 {{ margin: 0; padding: 14px 18px; font-size: 19px; background: #edf1f5; border-bottom: 1px solid #d7dce2; }}
    .record-body {{ padding: 18px; }}
    .status {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: 600; }}
    .status-blocked {{ background: #fbe1e1; color: #982626; }}
    .status-proposed {{ background: #fff0cc; color: #765300; }}
    .status-missing {{ background: #e6e9ed; color: #4d5661; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 12px 0 18px; }}
    th, td {{ border: 1px solid #d7dce2; padding: 9px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ width: 22%; background: #f7f8fa; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; max-height: 360px; overflow: auto; background: #f7f8fa; border: 1px solid #d7dce2; padding: 12px; }}
    .warnings {{ margin: 8px 0 16px; padding-left: 20px; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 10px 0 16px; }}
    a {{ color: #075ea8; }}
    textarea {{ width: 100%; min-height: 90px; box-sizing: border-box; resize: vertical; padding: 10px; font: inherit; border: 1px solid #aeb5bf; border-radius: 4px; }}
    .review-tools {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 0 0 20px; padding: 14px; background: white; border: 1px solid #d7dce2; border-radius: 6px; }}
    .review-progress {{ margin-right: auto; font-size: 17px; }}
    button, .file-button {{ display: inline-flex; align-items: center; min-height: 36px; box-sizing: border-box; padding: 7px 12px; border: 1px solid #8d98a5; border-radius: 4px; background: #fff; color: #202124; font: inherit; cursor: pointer; }}
    button:hover, .file-button:hover {{ background: #eef2f6; }}
    button.danger {{ border-color: #b84b4b; color: #8c2020; }}
    #review-message {{ flex-basis: 100%; min-height: 20px; color: #4d5661; }}
    details {{ margin: 12px 0; }}
    @media (max-width: 820px) {{ .summary {{ grid-template-columns: 1fr 1fr; }} main {{ padding: 12px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>事迹候选审计报告</h1>
    <p>只读比较当前 K、当前 T、候选 K 与 MinerU 原文；不修改 Excel，不自动缩写。</p>
    <p>生成时间：{escape(_text(report.get("generated_at")))}</p>
  </header>
  <main>
    <div class="summary">
      {_metric("记录", summary.get("record_count", 0))}
      {_metric("可审批 K", summary.get("proposed_story_count", 0))}
      {_metric("阻断 K", summary.get("blocked_story_count", 0))}
      {_metric("超过 40 字", summary.get("long_story_count", 0))}
      {_metric("多日期", summary.get("multiple_date_count", 0))}
    </div>
    <section class="review-tools" aria-label="人工意见管理">
      <div class="review-progress">已审 <strong id="review-filled">0</strong>/<span id="review-total">{int(summary.get("record_count", 0))}</span></div>
      <button type="button" id="export-reviews">导出意见 JSON</button>
      <label class="file-button" for="import-reviews">导入意见 JSON</label>
      <input type="file" id="import-reviews" accept="application/json,.json" hidden>
      <button type="button" id="clear-reviews" class="danger">清空意见</button>
      <span id="review-message" role="status" aria-live="polite"></span>
    </section>
    {sections}
  </main>
  <script>
    (() => {{
      const fields = Array.from(document.querySelectorAll('textarea[data-audit-key]'));
      const filled = document.getElementById('review-filled');
      const message = document.getElementById('review-message');
      const storageKey = (field) => 'lieshi-ocr-story-audit:' + location.pathname + ':' + field.dataset.auditKey;
      const updateCount = () => {{
        filled.textContent = String(fields.filter((field) => field.value.trim()).length);
      }};
      const setMessage = (text) => {{ message.textContent = text; }};

      fields.forEach((field) => {{
        field.value = localStorage.getItem(storageKey(field)) || '';
        field.addEventListener('input', () => {{
          if (field.value) localStorage.setItem(storageKey(field), field.value);
          else localStorage.removeItem(storageKey(field));
          updateCount();
        }});
      }});
      updateCount();

      document.getElementById('export-reviews').addEventListener('click', () => {{
        const opinions = {{}};
        fields.forEach((field) => {{
          if (field.value.trim()) opinions[field.dataset.auditKey] = field.value;
        }});
        const payload = {{
          schema: 'lieshi_ocr_story_review_opinions',
          version: 1,
          exported_at: new Date().toISOString(),
          report_path: location.pathname,
          record_count: fields.length,
          filled_count: Object.keys(opinions).length,
          opinions,
        }};
        const blob = new Blob([JSON.stringify(payload, null, 2) + '\\n'], {{type: 'application/json'}});
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'story_review_opinions.json';
        link.click();
        URL.revokeObjectURL(url);
        setMessage('已导出 ' + payload.filled_count + ' 条人工意见。');
      }});

      document.getElementById('import-reviews').addEventListener('change', async (event) => {{
        const input = event.currentTarget;
        const file = input.files && input.files[0];
        if (!file) return;
        try {{
          const payload = JSON.parse(await file.text());
          if (payload.schema !== 'lieshi_ocr_story_review_opinions' || payload.version !== 1 || !payload.opinions || typeof payload.opinions !== 'object' || Array.isArray(payload.opinions)) {{
            throw new Error('invalid review export');
          }}
          let imported = 0;
          fields.forEach((field) => {{
            const value = payload.opinions[field.dataset.auditKey];
            if (typeof value !== 'string') return;
            field.value = value;
            if (value) localStorage.setItem(storageKey(field), value);
            else localStorage.removeItem(storageKey(field));
            imported += 1;
          }});
          updateCount();
          setMessage('已导入 ' + imported + ' 条匹配的人工意见。');
        }} catch (_error) {{
          setMessage('导入失败：文件格式或版本不受支持。');
        }} finally {{
          input.value = '';
        }}
      }});

      document.getElementById('clear-reviews').addEventListener('click', () => {{
        if (!confirm('确认清空本报告的全部人工意见？此操作不可撤销，建议先导出备份。')) return;
        fields.forEach((field) => {{
          localStorage.removeItem(storageKey(field));
          field.value = '';
        }});
        updateCount();
        setMessage('已清空本报告的人工意见。');
      }});
    }})();
  </script>
</body>
</html>
"""


def _build_record(
    record: JsonDict,
    candidates: dict[str, list[JsonDict]],
    excel_index: dict[str, Any],
    sheet: Any,
) -> JsonDict:
    code = _text(record.get("code"))
    name = _text(record.get("name"))
    source_stem = _text(record.get("source_stem"))
    indexed = excel_index.get(code) if code else None
    candidate_options = candidates.get(code, [])
    candidate = candidate_options[0] if candidate_options else {}
    status = _text(candidate.get("audit_status")) or "missing"
    fields = record.get("fields", {}) if isinstance(record.get("fields"), dict) else {}
    raw_text = _text(record.get("raw_text"))
    candidate_text = _text(candidate.get("new"))
    candidate_length = _integer(candidate.get("story_length")) or len(candidate_text)
    warnings = _dedupe(
        _string_list(record.get("warnings", []))
        + _string_list(candidate.get("warnings", []))
        + (["multiple_story_candidates"] if len(candidate_options) > 1 else [])
    )
    if not code:
        warnings = _dedupe(warnings + ["code_missing"])
    elif indexed is None:
        warnings = _dedupe(warnings + ["code_not_found"])

    correction_region = record.get("regions", {}).get("correction", {}) if isinstance(record.get("regions"), dict) else {}
    if not isinstance(correction_region, dict):
        correction_region = {}
    return {
        "source_stem": source_stem,
        "code": code,
        "name": name,
        "excel": {
            "row": indexed.row if indexed is not None else 0,
            "expected_name": indexed.name if indexed is not None else "",
            "name_matches": bool(indexed is not None and comparable(indexed.name) == comparable(name)),
            "current_story": _text(sheet.cell(indexed.row, COL_STORY).value) if indexed is not None else "",
            "current_backup": _text(sheet.cell(indexed.row, COL_STORY_BACKUP).value) if indexed is not None else "",
        },
        "candidate": {
            "id": _text(candidate.get("id")),
            "status": status,
            "value": candidate_text,
            "length": candidate_length,
            "block_reason": _text(candidate.get("block_reason")),
        },
        "date_candidates": find_date_candidates(raw_text),
        "parsed_candidates": {
            "牺牲时间": _text(fields.get("牺牲时间")),
            "牺牲地点": _text(fields.get("牺牲地点")),
            "牺牲原因": _text(fields.get("牺牲原因")),
            "事迹": _text(fields.get("事迹")),
        },
        "raw_text": raw_text,
        "links": {
            "source_pdf": _text(record.get("source_pdf")),
            "mineru_text_source": _text(correction_region.get("text_source")),
            "correction_crop": _text(correction_region.get("crop_pdf")),
        },
        "warnings": warnings,
        "manual_conclusion": "",
    }


def find_date_candidates(text: str) -> list[str]:
    values = [re.sub(r"\s+", "", match.group(0)) for match in re.finditer(DATE_PATTERN, text)]
    return _dedupe(values)


def _index_story_candidates(dry_run: JsonDict) -> dict[str, list[JsonDict]]:
    result: dict[str, list[JsonDict]] = {}
    for key, status in (("proposed_changes", "proposed"), ("blocked_changes", "blocked")):
        changes = dry_run.get(key, [])
        if not isinstance(changes, list):
            continue
        for raw_change in changes:
            if not isinstance(raw_change, dict):
                continue
            if _text(raw_change.get("column_letter")).upper() != "K" and _integer(raw_change.get("column")) != COL_STORY:
                continue
            change = dict(raw_change)
            change["audit_status"] = status
            code = _text(change.get("code"))
            if code:
                result.setdefault(code, []).append(change)
    return result


def _render_record(record: JsonDict, report_dir: Path) -> str:
    excel = record.get("excel", {})
    candidate = record.get("candidate", {})
    parsed = record.get("parsed_candidates", {})
    links = record.get("links", {})
    warnings = _string_list(record.get("warnings", []))
    status = _text(candidate.get("status")) or "missing"
    status_label = {"blocked": "已阻断", "proposed": "可审批", "missing": "无 K 候选"}.get(status, status)
    date_text = "、".join(_string_list(record.get("date_candidates", []))) or "无"
    parsed_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(_text(value)) or '无'}</td></tr>"
        for key, value in parsed.items()
    )
    warning_items = "".join(f"<li>{escape(item)}</li>" for item in warnings) or "<li>无</li>"
    link_items = "".join(
        _render_link(label, _text(links.get(key)), report_dir)
        for key, label in (("source_pdf", "原始 PDF"), ("mineru_text_source", "MinerU 原文文件"))
    )
    audit_key = _text(record.get("code")) or _text(record.get("source_stem"))
    return f"""
    <section class="record">
      <h2>{escape(_text(record.get("code")) or "编号缺失")} / {escape(_text(record.get("name")) or "姓名缺失")}</h2>
      <div class="record-body">
        <p><span class="status status-{escape(status, quote=True)}">{escape(status_label)}</span></p>
        <table>
          <tr><th>Excel 行</th><td>{int(excel.get("row", 0)) or '-'}</td></tr>
          <tr><th>当前 K</th><td>{escape(_text(excel.get("current_story"))) or '空'}</td></tr>
          <tr><th>当前 T</th><td>{escape(_text(excel.get("current_backup"))) or '空'}</td></tr>
          <tr><th>候选 K</th><td>{escape(_text(candidate.get("value"))) or '无'}</td></tr>
          <tr><th>候选长度</th><td>{_integer(candidate.get("length"))}</td></tr>
          <tr><th>阻断原因</th><td>{escape(_text(candidate.get("block_reason"))) or '无'}</td></tr>
          <tr><th>检测到的日期</th><td>{escape(date_text)}</td></tr>
        </table>
        <div class="links">{link_items}</div>
        <details open><summary>解析候选字段</summary><table>{parsed_rows}</table></details>
        <details><summary>MinerU 原文</summary><pre>{escape(_text(record.get("raw_text")))}</pre></details>
        <h3>Warnings</h3><ul class="warnings">{warning_items}</ul>
        <label for="manual-{escape(audit_key, quote=True)}"><strong>人工意见</strong></label>
        <textarea id="manual-{escape(audit_key, quote=True)}" data-audit-key="{escape(audit_key, quote=True)}"></textarea>
      </div>
    </section>"""


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric">{escape(label)}<strong>{_integer(value)}</strong></div>'


def _render_link(label: str, path_value: str, report_dir: Path) -> str:
    if not path_value:
        return f"<span>{escape(label)}：不可用</span>"
    target = Path(path_value)
    absolute = target if target.is_absolute() else Path.cwd() / target
    try:
        relative = Path(os.path.relpath(absolute.resolve(strict=False), report_dir.resolve(strict=False))).as_posix()
    except ValueError:
        return f"<span>{escape(label)}：无法生成同盘相对链接</span>"
    href = quote(relative, safe="/:")
    suffix = "" if absolute.exists() else "（文件不存在）"
    return f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener">{escape(label)}</a>{escape(suffix)}'


def _load_object(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
