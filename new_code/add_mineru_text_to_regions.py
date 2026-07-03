#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add MinerU Markdown text to existing region pipeline outputs.

This script reuses:
- data/<batch>/<cut-dir-name>/*.pdf
- data/<batch>/<source-extracted-dir-name>/region_manifest.json

It writes:
- data/<batch>/<output-dir-name>/*.json
- data/<batch>/<output-dir-name>/mineru_text_manifest.json
- data/<batch>/<mineru-output-dir-name>/... MinerU raw outputs
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
MAGIC_PDF = Path(r"C:\Users\guozhibo\AppData\Local\Programs\Python\Python312\Scripts\magic-pdf.exe")

FIELD_PATTERN = (
    r"姓名|籍贯|出生时间|入党/入团时间|入党时间|入团时间|"
    r"参加革命（工作）时间|参加革命\(工作\)时间|参加革命时间|参加工作时间|"
    r"政治面貌|民族|生前（部队）单位及曾任职务|生前\(部队\)单位及曾任职务|"
    r"生前部队单位及曾任职务|生前单位及曾任职务|曾任职务|"
    r"牺牲时间|牺牲地点|牺牲原因|事迹|安葬地|安葬地点"
)

FIELD_FIXES = {
    "牺牺牲": "牺牲",
    "栖牲地点": "牺牲地点",
    "牺性地点": "牺牲地点",
    "牺牲地占": "牺牲地点",
    "牲地点": "牺牲地点",
    "西牺牲地点": "牺牲地点",
    "栖牲原因": "牺牲原因",
    "牺性原因": "牺牲原因",
    "牲原因": "牺牲原因",
    "性原因": "牺牲原因",
    "西牺牲原因": "牺牲原因",
    "牺牲原困": "牺牲原因",
    "音贯补充完善为": "籍贯补充完善为",
    "贯补充完善为": "籍贯补充完善为",
    "出年时间补充完善为": "出生时间补充完善为",
    "西牲时间补充完善为": "牺牲时间补充完善为",
    "族补充完善为": "民族补充完善为",
    "已族补充完善为": "民族补充完善为",
    "三前（部队）单位及曾任职务": "生前（部队）单位及曾任职务",
    "主前（部队）单位及曾任职务": "生前（部队）单位及曾任职务",
    "迹补充完善为": "事迹补充完善为",
    "复迹补充完善为": "事迹补充完善为",
    "葬地补充完善为": "安葬地补充完善为",
    "事迹补充完普为": "事迹补充完善为",
    "补充完普为": "补充完善为",
}


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def load_source_records(manifest_path: Path) -> list[dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get("records", [])


def normalize_mineru_text(text: str) -> str:
    value = text or ""
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    for old, new in FIELD_FIXES.items():
        value = value.replace(old, new)
    value = value.replace("牺牺牲", "牺牲")
    value = value.replace("籍籍贯", "籍贯")
    value = value.replace("民民族", "民族")
    value = value.replace("事事迹", "事迹")
    value = value.replace("安安葬地", "安葬地")
    value = re.sub(r"(?m)^牺牲?原因补充完善为", "牺牲原因补充完善为", value)
    value = re.sub(r"(?m)^牺牲?地点补充完善为", "牺牲地点补充完善为", value)
    value = re.sub(r"(?m)^补充完善为(?=[^\n]*原牺牲地点)", "牺牲地点补充完善为", value)
    value = re.sub(r"(?m)^善为(?=[^\n]*原牺牲原因)", "牺牲原因补充完善为", value)
    value = re.sub(r"(?m)^[|丨]?补充完善为(?=[^\n]*原牺牲原因)", "牺牲原因补充完善为", value)
    value = re.sub(r"(?m)^充完善为(?=[^\n]*原牺牲原因)", "牺牲原因补充完善为", value)
    value = re.sub(r"(?m)^[|丨]?补充完善为(?=[^\n]*原安葬地)", "安葬地补充完善为", value)
    value = re.sub(r"(?m)^充完善为(?=[^\n]*原安葬地)", "安葬地补充完善为", value)
    value = value.replace("：", ":")
    return value.strip()


def parse_correction_items(text: str) -> dict:
    clean = normalize_mineru_text(text).replace("\n", "")
    pattern = re.compile(
        rf"(?P<field>{FIELD_PATTERN})补充完善为[“\"']?"
        r"(?P<value>.*?)[”\"']?理由[:：]"
        rf"(?P<reason>.*?)(?=(?:{FIELD_PATTERN})补充完善为|$)"
    )
    items: dict[str, dict[str, str]] = {}
    for match in pattern.finditer(clean):
        field = match.group("field").strip("。；;，,、")
        value = match.group("value").strip("。；;，,")
        reason = match.group("reason").strip("。；;，,")
        if field and (value or reason):
            items[field] = {"value": value, "reason": reason}
    return items


def find_mineru_markdown(mineru_root: Path, cut_pdf: Path) -> Path | None:
    expected = list(mineru_root.glob(f"**/{cut_pdf.stem}.md"))
    if expected:
        return expected[0]
    return None


def run_mineru(cut_pdf: Path, mineru_root: Path, force: bool) -> tuple[str, Path | None, str | None]:
    existing = find_mineru_markdown(mineru_root, cut_pdf)
    if existing and not force:
        return existing.read_text(encoding="utf-8"), existing, None

    cmd = [
        str(MAGIC_PDF),
        "-p",
        str(cut_pdf),
        "-o",
        str(mineru_root),
        "-m",
        "ocr",
        "-l",
        "ch",
    ]
    proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return "", None, (proc.stderr or proc.stdout or "").strip()

    md_path = find_mineru_markdown(mineru_root, cut_pdf)
    if not md_path:
        return "", None, "mineru_markdown_not_found"
    return md_path.read_text(encoding="utf-8"), md_path, None


def quality_from_warnings(warnings: list[str]) -> str:
    if any(w.startswith("mineru_error") or w in {"mineru_text_empty", "mineru_markdown_missing"} for w in warnings):
        return "failed"
    if warnings:
        return "review_needed"
    return "ok"


def should_include(record: dict, source_stems: set[str], limit: int, count: int) -> bool:
    if source_stems:
        return record.get("source_stem") in source_stems
    return limit <= 0 or count < limit


def load_full_source_record(record: dict) -> dict:
    json_path = Path(record.get("json", ""))
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return record
    return record


def source_correction_text(record: dict) -> str:
    ocr = record.get("ocr") or {}
    return ocr.get("correction_text_clean") or ocr.get("correction_text_raw") or ""


def write_summary(path: Path, manifest: dict) -> None:
    lines = [
        "# MinerU 正文试跑汇总",
        "",
        f"- batch：`{manifest['batch']}`",
        f"- total：{manifest['total']}",
        f"- ok：{manifest['quality_counts'].get('ok', 0)}",
        f"- review_needed：{manifest['quality_counts'].get('review_needed', 0)}",
        f"- failed：{manifest['quality_counts'].get('failed', 0)}",
        "",
        "## Warning Counts",
        "",
    ]
    if manifest["warning_counts"]:
        for warning, count in manifest["warning_counts"].items():
            lines.append(f"- `{warning}`：{count}")
    else:
        lines.append("- 无")
    lines.extend(["", "## Records", "", "| source_stem | code | name | quality | items | markers | warnings |", "| --- | --- | --- | --- | ---: | ---: | --- |"])
    for record in manifest["records"]:
        lines.append(
            f"| `{record.get('source_stem', '')}` | `{record.get('code', '')}` | {record.get('name', '')} | "
            f"`{record.get('quality', '')}` | {record.get('mineru_item_count', 0)} | "
            f"{record.get('mineru_marker_count', 0)} | {', '.join(record.get('warnings', [])) or '无'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Use MinerU Markdown as correction body text.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=0, help="Use 0 for all selected records.")
    parser.add_argument("--source-stems", default="", help="Comma-separated source_stem values to run.")
    parser.add_argument("--cut-dir-name", default="cut")
    parser.add_argument("--source-extracted-dir-name", default="extracted")
    parser.add_argument("--output-dir-name", default="extracted_mineru_text")
    parser.add_argument("--mineru-output-dir-name", default="mineru_text")
    parser.add_argument("--clear-output", action="store_true")
    parser.add_argument("--force-mineru", action="store_true")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    source_manifest = batch_dir / args.source_extracted_dir_name / "region_manifest.json"
    out_dir = batch_dir / args.output_dir_name
    mineru_root = batch_dir / args.mineru_output_dir_name

    if not MAGIC_PDF.exists():
        raise FileNotFoundError(f"magic-pdf not found: {MAGIC_PDF}")
    if not source_manifest.exists():
        raise FileNotFoundError(f"source manifest not found: {source_manifest}")

    if args.clear_output:
        clear_dir(out_dir)
        clear_dir(mineru_root)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        mineru_root.mkdir(parents=True, exist_ok=True)

    source_stems = {item.strip() for item in args.source_stems.split(",") if item.strip()}
    records = []
    selected_count = 0

    for record in load_source_records(source_manifest):
        if not should_include(record, source_stems, args.limit, selected_count):
            continue
        selected_count += 1
        source_stem = record.get("source_stem", "")
        code = record.get("code", "")
        name = record.get("name", "")
        cut_pdf = Path(record.get("cut_pdf", ""))
        warnings = []
        print(f"[{selected_count}] {source_stem} {code} {name}", flush=True)

        markdown = ""
        markdown_path = None
        mineru_error = None
        if not cut_pdf.exists():
            mineru_error = f"cut_pdf_not_found:{cut_pdf}"
        else:
            markdown, markdown_path, mineru_error = run_mineru(cut_pdf, mineru_root, args.force_mineru)

        if mineru_error:
            warnings.append("mineru_error")
        source_full_record = load_full_source_record(record)
        normalized = normalize_mineru_text(markdown)
        text_source = "mineru"
        if not normalized:
            fallback = normalize_mineru_text(source_correction_text(source_full_record))
            if fallback:
                normalized = fallback
                text_source = "rapidocr_fallback"
                warnings.append("mineru_text_empty_rapidocr_fallback")
            else:
                warnings.append("mineru_text_empty")

        correction_items = parse_correction_items(normalized)
        marker_count = normalized.count("补充完善为")
        reason_count = normalized.count("理由")
        if normalized and marker_count == 0:
            warnings.append("non_standard_note")
        elif normalized and not correction_items:
            warnings.append("parse_no_items")
        elif marker_count != len(correction_items) or reason_count < len(correction_items):
            warnings.append("parse_low_confidence")

        quality = quality_from_warnings(warnings)
        out_record = {
            **source_full_record,
            "quality": quality,
            "warnings": warnings,
            "mineru": {
                "markdown_path": str(markdown_path) if markdown_path else "",
                "markdown": markdown,
                "text_normalized": normalized,
                "text_source": text_source,
                "error": mineru_error,
            },
            "correction_items": correction_items,
            "mineru_item_count": len(correction_items),
            "mineru_marker_count": marker_count,
            "mineru_reason_count": reason_count,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        out_json = out_dir / f"{Path(record.get('json', source_stem + '.json')).stem}.json"
        out_record["json"] = str(out_json)
        out_json.write_text(json.dumps(out_record, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append({
            "source_stem": source_stem,
            "code": code,
            "name": name,
            "json": str(out_json),
            "quality": quality,
            "warnings": warnings,
            "mineru_item_count": len(correction_items),
            "mineru_marker_count": marker_count,
            "mineru_reason_count": reason_count,
        })
        print(
            f"  {quality} items={len(correction_items)} markers={marker_count} warnings={','.join(warnings) or 'none'}",
            flush=True,
        )

    warning_counts = Counter(w for record in records for w in record["warnings"])
    quality_counts = Counter(record["quality"] for record in records)
    manifest = {
        "batch": args.batch,
        "source_manifest": str(source_manifest),
        "output_dir": str(out_dir),
        "mineru_output_dir": str(mineru_root),
        "total": len(records),
        "quality_counts": dict(sorted(quality_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "records": records,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    manifest_path = out_dir / "mineru_text_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = out_dir / "mineru_text_summary.md"
    write_summary(summary_path, manifest)
    print(f"manifest: {manifest_path}", flush=True)
    print(f"summary: {summary_path}", flush=True)
    print(
        f"total={len(records)} quality={dict(sorted(quality_counts.items()))} warnings={dict(sorted(warning_counts.items()))}",
        flush=True,
    )


if __name__ == "__main__":
    main()
