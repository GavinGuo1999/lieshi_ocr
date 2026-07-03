#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crop batch-2 review forms to the useful area:
- header/title/code
- original-info table
- correction content and reason

Outputs:
- data/<batch>/cut/<source_stem>_cut.pdf
- data/<batch>/cut/cut_manifest.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import fitz


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"

# PDF points on the current scan layout (586.6 x 841.7 pt).
# This keeps the region shown in the user's screenshot and removes the
# lower proof-material/signature/notes area.
CROP_RECT = fitz.Rect(35, 45, 545, 520)


def crop_pdf(src_pdf: Path, dst_pdf: Path) -> dict:
    src_doc = fitz.open(src_pdf)
    out_doc = fitz.open()

    if src_doc.page_count != 1:
        raise ValueError(f"Expected 1 page, got {src_doc.page_count}: {src_pdf}")

    src_page = src_doc[0]
    page_rect = src_page.rect
    crop_rect = CROP_RECT & page_rect

    out_page = out_doc.new_page(width=crop_rect.width, height=crop_rect.height)
    out_page.show_pdf_page(out_page.rect, src_doc, 0, clip=crop_rect)

    dst_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(dst_pdf, garbage=4, deflate=True)
    out_doc.close()
    src_doc.close()

    return {
        "source_pdf": str(src_pdf),
        "cut_pdf": str(dst_pdf),
        "page_count": 1,
        "source_rect": [round(page_rect.x0, 2), round(page_rect.y0, 2), round(page_rect.x1, 2), round(page_rect.y1, 2)],
        "crop_rect": [round(crop_rect.x0, 2), round(crop_rect.y0, 2), round(crop_rect.x1, 2), round(crop_rect.y1, 2)],
    }


def merge_pdfs(pdf_paths: list[Path], merged_pdf: Path) -> None:
    merged = fitz.open()
    for pdf_path in pdf_paths:
        part = fitz.open(pdf_path)
        merged.insert_pdf(part)
        part.close()
    merged_pdf.parent.mkdir(parents=True, exist_ok=True)
    merged.save(merged_pdf, garbage=4, deflate=True)
    merged.close()


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop useful review-form area for a batch.")
    parser.add_argument("--batch", default=DEFAULT_BATCH, help="Batch directory name under data/.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    cut_dir = batch_dir / "cut"
    manifest_path = cut_dir / "cut_manifest.json"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {scan_dir}")

    clear_dir(cut_dir)

    records = []
    for src_pdf in pdf_files:
        dst_pdf = cut_dir / f"{src_pdf.stem}_cut.pdf"
        record = crop_pdf(src_pdf, dst_pdf)
        records.append(record)
        print(f"cut: {src_pdf.name} -> {dst_pdf.name}")

    manifest = {
        "batch": args.batch,
        "input_dir": str(scan_dir),
        "cut_dir": str(cut_dir),
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
