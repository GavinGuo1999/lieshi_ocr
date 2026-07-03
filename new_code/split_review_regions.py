#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Split review-form scans into fixed regions without OCR.

Default test mode processes the first 3 PDFs in data/<batch>/scan.

Outputs:
- data/<batch>/cut_parts/<source_stem>__code.pdf
- data/<batch>/cut_parts/<source_stem>__table.pdf
- data/<batch>/cut_parts/<source_stem>__correction.pdf
- data/<batch>/cut_parts/_preview/*.png
- data/<batch>/cut_parts/split_manifest.json
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import fitz


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"

# Coordinates are PDF points on the current scan layout, measured from the
# original one-page PDF. Keep these stable for batch processing.
REGIONS = {
    "code": fitz.Rect(395, 45, 545, 90),
    "table": fitz.Rect(35, 45, 545, 325),
    # The correction body excludes the left vertical label to reduce OCR noise.
    "correction": fitz.Rect(70, 305, 545, 520),
}


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def save_region(src_pdf: Path, region_name: str, clip: fitz.Rect, out_pdf: Path, preview_png: Path | None) -> dict:
    src_doc = fitz.open(src_pdf)
    if src_doc.page_count != 1:
        src_doc.close()
        raise ValueError(f"Expected 1 page, got {src_doc.page_count}: {src_pdf}")

    page = src_doc[0]
    page_rect = page.rect
    clip = clip & page_rect

    out_doc = fitz.open()
    out_page = out_doc.new_page(width=clip.width, height=clip.height)
    out_page.show_pdf_page(out_page.rect, src_doc, 0, clip=clip)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(out_pdf, garbage=4, deflate=True)
    out_doc.close()

    if preview_png is not None:
        preview_png.parent.mkdir(parents=True, exist_ok=True)
        preview = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
        preview.save(preview_png)

    src_doc.close()
    return {
        "region": region_name,
        "pdf": str(out_pdf),
        "preview_png": str(preview_png) if preview_png else "",
        "clip_rect": [round(clip.x0, 2), round(clip.y0, 2), round(clip.x1, 2), round(clip.y1, 2)],
        "size": [round(clip.width, 2), round(clip.height, 2)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Split review-form scans into fixed regions.")
    parser.add_argument("--batch", default=DEFAULT_BATCH, help="Batch directory name under data/.")
    parser.add_argument("--limit", type=int, default=3, help="Number of PDFs to process. Use 0 for all.")
    parser.add_argument("--no-preview", action="store_true", help="Do not write PNG preview files.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    out_dir = batch_dir / "cut_parts"
    preview_dir = out_dir / "_preview"
    manifest_path = out_dir / "split_manifest.json"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {scan_dir}")

    clear_dir(out_dir)

    records = []
    for index, src_pdf in enumerate(pdf_files, 1):
        source_record = {"source_pdf": str(src_pdf), "regions": []}
        print(f"[{index}/{len(pdf_files)}] split {src_pdf.name}")
        for region_name, rect in REGIONS.items():
            out_pdf = out_dir / f"{src_pdf.stem}__{region_name}.pdf"
            preview_png = None if args.no_preview else preview_dir / f"{src_pdf.stem}__{region_name}.png"
            region_record = save_region(src_pdf, region_name, rect, out_pdf, preview_png)
            source_record["regions"].append(region_record)
            print(f"  {region_name}: {out_pdf.name}")
        records.append(source_record)

    manifest = {
        "batch": args.batch,
        "scan_dir": str(scan_dir),
        "out_dir": str(out_dir),
        "regions": {
            name: [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]
            for name, rect in REGIONS.items()
        },
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
