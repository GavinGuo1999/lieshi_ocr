#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Precheck name-value cell cropping using table vertical-line detection.

Outputs:
- data/<batch>/_name_line_crop_check/<source_stem>__name.png
- data/<batch>/_name_line_crop_check/<source_stem>__name_detected.png
- data/<batch>/_name_line_crop_check/name_line_crop_manifest.json
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"
RENDER_SCALE = 5.0

# Wide candidate: includes the "姓名" label cell, the name value cell,
# and the left edge of "曾用名" for reliable vertical-line detection.
CANDIDATE_RECT = fitz.Rect(55, 112, 230, 158)


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def group_positions(values: list[int], max_gap: int = 5) -> list[tuple[int, int]]:
    if not values:
        return []
    groups = []
    start = prev = values[0]
    for value in values[1:]:
        if value - prev <= max_gap:
            prev = value
        else:
            groups.append((start, prev))
            start = prev = value
    groups.append((start, prev))
    return groups


def render_candidate(pdf_path: Path) -> tuple[Image.Image, fitz.Rect]:
    doc = fitz.open(pdf_path)
    if doc.page_count != 1:
        page_count = doc.page_count
        doc.close()
        raise ValueError(f"Expected 1 page, got {page_count}: {pdf_path}")
    page = doc[0]
    rect = CANDIDATE_RECT & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), clip=rect, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    doc.close()
    return image, rect


def find_name_cell_bounds(image: Image.Image) -> tuple[int, int, int, int, dict]:
    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        12,
    )
    h, w = binary.shape

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(35, int(h * 0.45))))
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(45, int(w * 0.2)), 1))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

    v_proj = vertical.sum(axis=0) / 255
    h_proj = horizontal.sum(axis=1) / 255

    v_lines = [i for i, value in enumerate(v_proj) if value >= max(25, h * 0.35)]
    h_lines = [i for i, value in enumerate(h_proj) if value >= max(45, w * 0.40)]
    v_centers = [int((a + b) / 2) for a, b in group_positions(v_lines)]
    h_centers = [int((a + b) / 2) for a, b in group_positions(h_lines)]

    # Expected vertical lines in this candidate:
    # outer left, label/value separator, value/曾用名 separator.
    if len(v_centers) >= 3:
        left = v_centers[1]
        right = v_centers[2]
        method = "line"
    elif len(v_centers) >= 2:
        left = v_centers[0]
        right = v_centers[1]
        method = "line_partial"
    else:
        left = int(w * 0.36)
        right = int(w * 0.86)
        method = "fallback"

    if len(h_centers) >= 2:
        top = h_centers[0]
        bottom = h_centers[-1]
        h_method = "line_pair"
    elif len(h_centers) == 1:
        # The only strong horizontal line is usually the top border of the
        # table row. Crop the name-value cell below it and ignore text above.
        top = h_centers[0]
        bottom = min(h - 1, top + int(h * 0.52))
        h_method = "single_top_line"
    else:
        top = int(h * 0.34)
        bottom = int(h * 0.90)
        h_method = "fallback"

    inset_x = max(8, int(RENDER_SCALE * 2))
    inset_y = max(4, int(RENDER_SCALE * 1.2))
    left = min(max(left + inset_x, 0), w - 2)
    right = max(min(right - inset_x, w), left + 2)
    top = min(max(top + inset_y, 0), h - 2)
    bottom = max(min(bottom - inset_y, h), top + 2)

    debug = {
        "image_size": [w, h],
        "v_centers": v_centers,
        "h_centers": h_centers,
        "method": method,
        "h_method": h_method,
    }
    return left, top, right, bottom, debug


def process_one(pdf_path: Path, out_dir: Path) -> dict:
    candidate, rect = render_candidate(pdf_path)
    left, top, right, bottom, debug = find_name_cell_bounds(candidate)

    name_png = out_dir / f"{pdf_path.stem}__name.png"
    detected_png = out_dir / f"{pdf_path.stem}__name_detected.png"

    detected = candidate.copy()
    draw = ImageDraw.Draw(detected)
    draw.rectangle((left, top, right, bottom), outline=(40, 110, 230), width=5)
    detected.save(detected_png, optimize=True)

    name_img = candidate.crop((left, top, right, bottom))
    name_img.save(name_png, optimize=True)

    width, height = name_img.size
    ratio = width / max(height, 1)
    warnings = []
    if height < 50 or width < 80 or ratio > 5 or ratio < 0.8:
        warnings.append("size_suspicious")

    return {
        "source_pdf": str(pdf_path),
        "source_stem": pdf_path.stem,
        "candidate_rect": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
        "name_png": str(name_png),
        "detected_png": str(detected_png),
        "bounds_px": [left, top, right, bottom],
        "image_size": [width, height],
        "ratio": round(ratio, 3),
        "file_size": name_png.stat().st_size,
        "debug": debug,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop name value cell by detecting table lines.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=0, help="Use 0 for all files.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    out_dir = batch_dir / "_name_line_crop_check"
    manifest_path = out_dir / "name_line_crop_manifest.json"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    clear_dir(out_dir)

    records = []
    for index, pdf_path in enumerate(pdf_files, 1):
        try:
            record = process_one(pdf_path, out_dir)
        except Exception as exc:
            record = {
                "source_pdf": str(pdf_path),
                "source_stem": pdf_path.stem,
                "warnings": [f"{type(exc).__name__}: {exc}"],
            }
        records.append(record)
        if index % 25 == 0 or index == len(pdf_files):
            print(f"name line crop {index}/{len(pdf_files)}")

    manifest = {
        "batch": args.batch,
        "scan_dir": str(scan_dir),
        "out_dir": str(out_dir),
        "render_scale": RENDER_SCALE,
        "candidate_rect": [round(CANDIDATE_RECT.x0, 2), round(CANDIDATE_RECT.y0, 2), round(CANDIDATE_RECT.x1, 2), round(CANDIDATE_RECT.y1, 2)],
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
