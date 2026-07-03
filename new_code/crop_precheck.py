#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate full-batch crop precheck previews without OCR.

Each preview is the original page rendered at low resolution with fixed crop
boxes drawn over it:
- red: code
- blue: name
- green: correction content

Outputs:
- data/<batch>/_crop_check/previews/<source_stem>__check.png
- data/<batch>/_crop_check/crop_precheck_manifest.json
- data/<batch>/_crop_check/crop_precheck_manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
PREVIEW_SCALE = 1.4

# Coordinates are PDF points on the original scan page.
REGIONS = {
    "code": fitz.Rect(365, 35, 560, 105),
    "name": fitz.Rect(55, 112, 225, 165),
    "correction": fitz.Rect(55, 295, 560, 535),
}

COLORS = {
    "code": (220, 40, 40),
    "name": (40, 110, 230),
    "correction": (30, 150, 80),
}


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def scaled_rect(rect: fitz.Rect, scale: float) -> tuple[int, int, int, int]:
    return (
        int(round(rect.x0 * scale)),
        int(round(rect.y0 * scale)),
        int(round(rect.x1 * scale)),
        int(round(rect.y1 * scale)),
    )


def draw_precheck(pdf_path: Path, preview_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    record = {
        "source_pdf": str(pdf_path),
        "source_stem": pdf_path.stem,
        "page_count": doc.page_count,
        "page_size": None,
        "preview": str(preview_path),
        "regions": {},
        "warnings": [],
    }

    if doc.page_count != 1:
        record["warnings"].append(f"page_count_{doc.page_count}")

    page = doc[0]
    page_rect = page.rect
    record["page_size"] = [round(page_rect.width, 2), round(page_rect.height, 2)]

    pix = page.get_pixmap(matrix=fitz.Matrix(PREVIEW_SCALE, PREVIEW_SCALE), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(image)

    for name, rect in REGIONS.items():
        clipped = rect & page_rect
        if clipped.is_empty:
            record["warnings"].append(f"{name}_empty")
            continue
        box = scaled_rect(clipped, PREVIEW_SCALE)
        color = COLORS[name]
        draw.rectangle(box, outline=color, width=4)
        draw.text((box[0] + 4, max(0, box[1] - 18)), name, fill=color)
        record["regions"][name] = {
            "rect": [round(clipped.x0, 2), round(clipped.y0, 2), round(clipped.x1, 2), round(clipped.y1, 2)],
            "size": [round(clipped.width, 2), round(clipped.height, 2)],
        }

    preview_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(preview_path, optimize=True)
    doc.close()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate crop precheck previews for a batch.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=0, help="Use 0 for all files.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    check_dir = batch_dir / "_crop_check"
    preview_dir = check_dir / "previews"
    json_path = check_dir / "crop_precheck_manifest.json"
    csv_path = check_dir / "crop_precheck_manifest.csv"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    clear_dir(check_dir)

    records = []
    for index, pdf_path in enumerate(pdf_files, 1):
        preview_path = preview_dir / f"{pdf_path.stem}__check.png"
        record = draw_precheck(pdf_path, preview_path)
        records.append(record)
        if index % 20 == 0 or index == len(pdf_files):
            print(f"precheck {index}/{len(pdf_files)}")

    manifest = {
        "batch": args.batch,
        "scan_dir": str(scan_dir),
        "check_dir": str(check_dir),
        "preview_dir": str(preview_dir),
        "scale": PREVIEW_SCALE,
        "regions": {
            name: [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]
            for name, rect in REGIONS.items()
        },
        "records": records,
    }
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["source_stem", "page_count", "page_width", "page_height", "preview", "warnings"])
        for record in records:
            width, height = record["page_size"]
            writer.writerow([
                record["source_stem"],
                record["page_count"],
                width,
                height,
                record["preview"],
                ";".join(record["warnings"]),
            ])

    print(f"json: {json_path}")
    print(f"csv: {csv_path}")


if __name__ == "__main__":
    main()
