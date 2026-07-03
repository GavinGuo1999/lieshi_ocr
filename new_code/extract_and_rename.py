#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR cropped review PDFs, rename them by code/name, and save extracted JSON.

Inputs:
- data/<batch>/cut/*_cut.pdf

Outputs:
- data/<batch>/rename_pdf/<code>_<name>.pdf
- data/<batch>/extracted/<code>_<name>.json
- data/<batch>/extracted/extract_manifest.json
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
RENDER_SCALE = 3.0


@dataclass
class OcrLine:
    text: str
    score: float
    box: list[list[float]]


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def safe_filename(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r'[\\/:*?"<>|]', "_", value)
    value = re.sub(r"\s+", "", value)
    return value or "未识别"


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace(" ", "").replace("\u3000", "")
    text = text.replace("：", ":")
    return text


def render_pdf(pdf_path: Path) -> Image.Image:
    doc = fitz.open(pdf_path)
    if doc.page_count != 1:
        doc.close()
        raise ValueError(f"Expected 1 page, got {doc.page_count}: {pdf_path}")
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), alpha=False)
    doc.close()
    return Image.open(io.BytesIO(pix.tobytes("png")))


def run_ocr(ocr: RapidOCR, pdf_path: Path) -> list[OcrLine]:
    image = render_pdf(pdf_path)
    result, _ = ocr(image, return_img=False)
    lines: list[OcrLine] = []
    for item in result or []:
        box, text, score = item[0], item[1], item[2]
        lines.append(OcrLine(text=str(text), score=float(score), box=box))
    return lines


def full_text(lines: list[OcrLine]) -> str:
    return "\n".join(line.text for line in lines if line.text.strip())


def extract_code(text: str) -> str:
    compact = normalize_text(text)
    match = re.search(r"晋祁县\s*(\d{6})", compact)
    if match:
        return "晋祁县" + match.group(1)
    match = re.search(r"编号[:：]?\s*晋?祁?县?\s*(\d{6})", compact)
    if match:
        return "晋祁县" + match.group(1)
    match = re.search(r"\b(\d{6})\b", compact)
    if match:
        return "晋祁县" + match.group(1)
    return ""


def extract_name_from_table(lines: list[OcrLine]) -> str:
    texts = [line.text.strip() for line in lines if line.text.strip()]
    for idx, text in enumerate(texts):
        if text == "姓名" and idx + 1 < len(texts):
            candidate = clean_name(texts[idx + 1])
            if candidate:
                return candidate
    return ""


def clean_name(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"(烈士|男|女|姓名|曾用名|性别|编号).*", "", value)
    value = re.sub(r"[^一-龥·]", "", value)
    if 2 <= len(value) <= 5:
        return value
    return ""


def extract_name_from_correction(text: str) -> str:
    compact = normalize_text(text)
    patterns = [
        r"事迹补充(?:完善|填写|更正)?为[“\"]([^“”\"，,]{2,5})烈士",
        r"烈士事迹[:：]?([^“”\"，,]{2,5})烈士",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if match:
            name = clean_name(match.group(1))
            if name:
                return name
    return ""


def extract_correction_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = None
    for idx, line in enumerate(lines):
        if "补充" in line and ("理由" in line or "完善" in line):
            start = idx
            break
    if start is None:
        return ""
    noise = {"修", "正", "内", "容", "及", "理", "由", "修正内容及理由"}
    cleaned = []
    for line in lines[start:]:
        compact = normalize_text(line)
        if compact in noise:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for i in range(1, 1000):
        candidate = path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot find unique filename for {path}")


def process_one(ocr: RapidOCR, cut_pdf: Path, rename_dir: Path, extracted_dir: Path) -> dict:
    lines = run_ocr(ocr, cut_pdf)
    text = full_text(lines)
    correction_text = extract_correction_text(text)
    code = extract_code(text)
    name = extract_name_from_correction(correction_text) or extract_name_from_table(lines)

    warnings = []
    if not code:
        warnings.append("code_not_found")
        code = cut_pdf.stem
    if not name:
        warnings.append("name_not_found")
        name = "未识别姓名"

    base_name = safe_filename(f"{code}_{name}")
    renamed_pdf = unique_path(rename_dir / f"{base_name}.pdf")
    json_path = unique_path(extracted_dir / f"{base_name}.json")

    shutil.copy2(cut_pdf, renamed_pdf)

    record = {
        "source_cut_pdf": str(cut_pdf),
        "renamed_pdf": str(renamed_pdf),
        "code": code,
        "name": name,
        "correction_text": correction_text,
        "ocr_text": text,
        "ocr_lines": [asdict(line) for line in lines],
        "warnings": warnings,
        "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "cut_pdf": str(cut_pdf),
        "renamed_pdf": str(renamed_pdf),
        "json": str(json_path),
        "code": code,
        "name": name,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract code/name/text and rename cropped PDFs.")
    parser.add_argument("--batch", default=DEFAULT_BATCH, help="Batch directory name under data/.")
    parser.add_argument("--clear", action="store_true", help="Clear rename_pdf and extracted before running.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    cut_dir = batch_dir / "cut"
    rename_dir = batch_dir / "rename_pdf"
    extracted_dir = batch_dir / "extracted"
    manifest_path = extracted_dir / "extract_manifest.json"

    cut_pdfs = sorted(cut_dir.glob("*_cut.pdf"))
    if not cut_pdfs:
        raise FileNotFoundError(f"No *_cut.pdf files found in {cut_dir}")

    if args.clear:
        clear_dir(rename_dir)
        clear_dir(extracted_dir)
    else:
        rename_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

    ocr = RapidOCR()
    records = []
    for idx, cut_pdf in enumerate(cut_pdfs, 1):
        print(f"[{idx}/{len(cut_pdfs)}] OCR {cut_pdf.name}")
        record = process_one(ocr, cut_pdf, rename_dir, extracted_dir)
        records.append(record)
        status = "OK" if not record["warnings"] else "WARN:" + ",".join(record["warnings"])
        print(f"  {status} {record['code']} {record['name']}")

    manifest = {
        "batch": args.batch,
        "cut_dir": str(cut_dir),
        "rename_dir": str(rename_dir),
        "extracted_dir": str(extracted_dir),
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
