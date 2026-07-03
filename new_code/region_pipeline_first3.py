#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test pipeline for the first 3 scanned review forms.

It does not save code/name crop PDFs. It only uses those regions in memory
for OCR, then saves the correction-content PDF named as <code>_<name>.pdf.

Outputs:
- data/<batch>/cut/<code>_<name>__<source_stem>.pdf
- data/<batch>/extracted/<code>_<name>__<source_stem>.json
- data/<batch>/extracted/region_manifest.json
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import time
from pathlib import Path

import fitz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
DEFAULT_LIMIT = 3
OCR_SCALE = 4.0

PREFIX = "\u664b\u7941\u53bf"
UNKNOWN_NAME = "\u672a\u8bc6\u522b\u59d3\u540d"

# Coordinates are PDF points on the original scan page.
REGIONS = {
    "code": fitz.Rect(365, 35, 560, 105),
    "name": fitz.Rect(118, 120, 205, 150),
    # Correction content body only. This removes the left vertical label.
    "correction": fitz.Rect(55, 295, 560, 535),
}


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]', "_", value or "")
    value = re.sub(r"\s+", "", value).strip("._ ")
    return value or "unknown"


def render_region(page: fitz.Page, rect: fitz.Rect, scale: float = OCR_SCALE) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def ocr_region(ocr: RapidOCR, page: fitz.Page, rect: fitz.Rect) -> list[dict]:
    image = render_region(page, rect)
    result, _ = ocr(image, return_img=False)
    rows = []
    for item in result or []:
        rows.append({
            "text": str(item[1]),
            "score": float(item[2]),
        })
    return rows


def join_text(rows: list[dict]) -> str:
    return "\n".join(row["text"] for row in rows if row["text"].strip())


def extract_code(text: str) -> str:
    match = re.search(r"(\d{6})", text or "")
    if match:
        return PREFIX + match.group(1)
    return ""


def clean_name(text: str) -> str:
    text = re.sub(r"\s+", "", text or "")
    text = re.sub(r"[\u59d3\u540d\uff1a:]", "", text)
    text = re.sub(r"[^\u4e00-\u9fff\u00b7]", "", text)
    if 2 <= len(text) <= 5:
        return text
    return ""


def extract_name(name_text: str, correction_text: str) -> str:
    name_label = "\u59d3\u540d"
    name_lines = [line.strip() for line in name_text.splitlines() if line.strip()]

    for idx, line in enumerate(name_lines):
        if name_label in line and idx + 1 < len(name_lines):
            name = clean_name(name_lines[idx + 1])
            if name:
                return name

    # Fallback: find "XXX烈士" in the correction body.
    martyr = "\u70c8\u58eb"
    for match in re.finditer(r"([\u4e00-\u9fff\u00b7]{2,5})" + martyr, correction_text or ""):
        name = clean_name(match.group(1))
        if name:
            return name

    for line in reversed(name_lines):
        name = clean_name(line)
        if name:
            return name
    return ""


def save_pdf_region(src_doc: fitz.Document, rect: fitz.Rect, out_pdf: Path) -> None:
    out_doc = fitz.open()
    out_page = out_doc.new_page(width=rect.width, height=rect.height)
    out_page.show_pdf_page(out_page.rect, src_doc, 0, clip=rect)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(out_pdf, garbage=4, deflate=True)
    out_doc.close()


def process_one(ocr: RapidOCR, src_pdf: Path, cut_dir: Path, extracted_dir: Path) -> dict:
    src_doc = fitz.open(src_pdf)
    if src_doc.page_count != 1:
        src_doc.close()
        raise ValueError(f"Expected 1 page, got {src_doc.page_count}: {src_pdf}")

    page = src_doc[0]
    page_rect = page.rect
    rects = {name: rect & page_rect for name, rect in REGIONS.items()}

    code_rows = ocr_region(ocr, page, rects["code"])
    name_rows = ocr_region(ocr, page, rects["name"])
    correction_rows = ocr_region(ocr, page, rects["correction"])

    code_text = join_text(code_rows)
    name_text = join_text(name_rows)
    correction_text = join_text(correction_rows)

    warnings = []
    code = extract_code(code_text)
    if not code:
        warnings.append("code_not_found")
        code = src_pdf.stem

    name = extract_name(name_text, correction_text)
    if not name:
        warnings.append("name_not_found")
        name = UNKNOWN_NAME

    base = safe_filename(f"{code}_{name}__{src_pdf.stem}")
    cut_pdf = cut_dir / f"{base}.pdf"
    json_path = extracted_dir / f"{base}.json"

    save_pdf_region(src_doc, rects["correction"], cut_pdf)

    src_doc.close()

    record = {
        "source_pdf": str(src_pdf),
        "source_stem": src_pdf.stem,
        "cut_pdf": str(cut_pdf),
        "code": code,
        "name": name,
        "code_ocr_text": code_text,
        "name_ocr_text": name_text,
        "correction_text": correction_text,
        "code_ocr_rows": code_rows,
        "name_ocr_rows": name_rows,
        "correction_ocr_rows": correction_rows,
        "regions": {
            region: [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]
            for region, r in rects.items()
        },
        "warnings": warnings,
        "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    extracted_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "source_pdf": str(src_pdf),
        "source_stem": src_pdf.stem,
        "cut_pdf": str(cut_pdf),
        "json": str(json_path),
        "code": code,
        "name": name,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the region-based test pipeline.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    cut_dir = batch_dir / "cut"
    extracted_dir = batch_dir / "extracted"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    clear_dir(cut_dir)
    clear_dir(extracted_dir)

    ocr = RapidOCR()
    records = []
    for index, src_pdf in enumerate(pdf_files, 1):
        print(f"[{index}/{len(pdf_files)}] {src_pdf.name}")
        record = process_one(ocr, src_pdf, cut_dir, extracted_dir)
        records.append(record)
        status = "OK" if not record["warnings"] else "WARN:" + ",".join(record["warnings"])
        print(f"  {status} {record['code']} {record['name']}")

    manifest = {
        "batch": args.batch,
        "limit": args.limit,
        "scan_dir": str(scan_dir),
        "cut_dir": str(cut_dir),
        "extracted_dir": str(extracted_dir),
        "records": records,
    }
    manifest_path = extracted_dir / "region_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
