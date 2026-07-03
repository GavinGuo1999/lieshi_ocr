#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run the existing region pipeline for selected scan PDFs.

This is a thin wrapper around batch_region_pipeline.process_one so we can process
newly scanned pages without clearing or duplicating the existing 237-page output.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

import batch_region_pipeline as region_pipeline


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"


def clear_dir(path: Path) -> None:
    region_pipeline.clear_dir(path)


def parse_source_stems(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run region extraction for selected scan PDFs.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--source-stems", required=True, help="Comma-separated source PDF stems.")
    parser.add_argument("--cut-dir-name", default="cut_new6")
    parser.add_argument("--extracted-dir-name", default="extracted_new6")
    parser.add_argument("--clear-output", action="store_true")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    cut_dir = batch_dir / args.cut_dir_name
    extracted_dir = batch_dir / args.extracted_dir_name
    source_stems = parse_source_stems(args.source_stems)

    if args.clear_output:
        clear_dir(cut_dir)
        clear_dir(extracted_dir)
    else:
        cut_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = [path for path in sorted(scan_dir.glob("*.pdf")) if path.stem in source_stems]
    missing = sorted(source_stems - {path.stem for path in pdf_files})
    if missing:
        raise FileNotFoundError(f"Missing scan PDFs for stems: {', '.join(missing)}")

    ocr = RapidOCR()
    records = []
    for index, src_pdf in enumerate(pdf_files, 1):
        print(f"[{index}/{len(pdf_files)}] {src_pdf.name}", flush=True)
        try:
            record = region_pipeline.process_one(ocr, src_pdf, cut_dir, extracted_dir)
        except Exception as exc:
            record = {
                "source_pdf": str(src_pdf),
                "source_stem": src_pdf.stem,
                "code": "",
                "name": "",
                "cut_pdf": "",
                "json": "",
                "warnings": [f"process_error:{type(exc).__name__}:{exc}"],
            }
        records.append(record)
        status = "OK" if not record.get("warnings") else "WARN:" + ",".join(record["warnings"])
        print(f"  {status} {record.get('code', '')} {record.get('name', '')}", flush=True)

    warning_counts = Counter(w for record in records for w in record.get("warnings", []))
    code_counts = Counter(record["code"] for record in records if record.get("code"))
    duplicate_codes = sorted(code for code, count in code_counts.items() if count > 1)
    manifest = {
        "batch": args.batch,
        "scan_dir": str(scan_dir),
        "cut_dir": str(cut_dir),
        "extracted_dir": str(extracted_dir),
        "source_stems": sorted(source_stems),
        "total": len(records),
        "ok": sum(1 for record in records if not record.get("warnings")),
        "warning_counts": dict(sorted(warning_counts.items())),
        "duplicate_codes": duplicate_codes,
        "records": records,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    manifest_path = extracted_dir / "region_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}", flush=True)
    print(f"total={manifest['total']} ok={manifest['ok']} warnings={sum(warning_counts.values())}", flush=True)
    if warning_counts:
        print("warning_counts:", flush=True)
        for warning, count in sorted(warning_counts.items()):
            print(f"  {warning}: {count}", flush=True)


if __name__ == "__main__":
    main()
