#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate full-batch PNG prechecks for small fixed regions.

Outputs:
- data/<batch>/_code_crop_check/<source_stem>__code.png
- data/<batch>/_name_crop_check/<source_stem>__name.png
- manifest JSON in each output directory
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import fitz


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
RENDER_SCALE = 4.0

REGIONS = {
    "code": {
        "rect": fitz.Rect(365, 35, 560, 105),
        "out_dir_name": "_code_crop_check",
    },
    "name": {
        "rect": fitz.Rect(118, 120, 205, 150),
        "out_dir_name": "_name_crop_check",
    },
}


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def render_region(pdf_path: Path, region: str, out_dir: Path) -> dict:
    spec = REGIONS[region]
    doc = fitz.open(pdf_path)
    if doc.page_count != 1:
        page_count = doc.page_count
        doc.close()
        raise ValueError(f"Expected 1 page, got {page_count}: {pdf_path}")
    page = doc[0]
    rect = spec["rect"] & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), clip=rect, alpha=False)
    out_png = out_dir / f"{pdf_path.stem}__{region}.png"
    pix.save(out_png)
    doc.close()
    return {
        "source_pdf": str(pdf_path),
        "source_stem": pdf_path.stem,
        "png": str(out_png),
        "rect": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
        "image_size": [pix.width, pix.height],
        "file_size": out_png.stat().st_size,
        "warnings": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate small-region crop prechecks.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--region", choices=sorted(REGIONS.keys()), required=True)
    parser.add_argument("--limit", type=int, default=0, help="Use 0 for all files.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    out_dir = batch_dir / REGIONS[args.region]["out_dir_name"]
    manifest_path = out_dir / f"{args.region}_crop_manifest.json"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    clear_dir(out_dir)

    records = []
    for index, pdf_path in enumerate(pdf_files, 1):
        try:
            record = render_region(pdf_path, args.region, out_dir)
        except Exception as exc:
            record = {
                "source_pdf": str(pdf_path),
                "source_stem": pdf_path.stem,
                "png": "",
                "rect": [],
                "image_size": [],
                "file_size": 0,
                "warnings": [f"{type(exc).__name__}: {exc}"],
            }
        records.append(record)
        if index % 25 == 0 or index == len(pdf_files):
            print(f"{args.region} crop {index}/{len(pdf_files)}")

    manifest = {
        "batch": args.batch,
        "region": args.region,
        "scan_dir": str(scan_dir),
        "out_dir": str(out_dir),
        "render_scale": RENDER_SCALE,
        "rect": [
            round(REGIONS[args.region]["rect"].x0, 2),
            round(REGIONS[args.region]["rect"].y0, 2),
            round(REGIONS[args.region]["rect"].x1, 2),
            round(REGIONS[args.region]["rect"].y1, 2),
        ],
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
