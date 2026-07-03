#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test line-based correction-cell crop on the first 3 PDFs.

Workflow:
1. Render the source PDF page.
2. Take a generous candidate area around correction content.
3. Detect table black lines inside the candidate area.
4. Crop inside the detected correction cell, removing outside content.

Outputs:
- data/<batch>/_line_crop_test/<source_stem>__candidate.png
- data/<batch>/_line_crop_test/<source_stem>__detected.png
- data/<batch>/_line_crop_test/<source_stem>__content.png
- data/<batch>/_line_crop_test/<source_stem>__content.pdf
- data/<batch>/_line_crop_test/line_crop_manifest.json
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
DEFAULT_LIMIT = 3
RENDER_SCALE = 3.0

# Generous area around "修正内容及理由" on the original PDF page.
CANDIDATE_RECT = fitz.Rect(35, 280, 560, 545)


def clear_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def render_clip(page: fitz.Page, rect: fitz.Rect) -> tuple[Image.Image, fitz.Rect]:
    rect = rect & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE), clip=rect, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return image, rect


def find_line_bounds(image: Image.Image) -> tuple[int, int, int, int, dict]:
    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Invert so dark table lines become white foreground.
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        12,
    )

    h, w = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(45, w // 8), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(35, h // 8)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

    h_proj = horizontal.sum(axis=1) / 255
    v_proj = vertical.sum(axis=0) / 255

    h_threshold = max(80, int(w * 0.45))
    v_threshold = max(35, int(h * 0.25))
    h_lines = [i for i, value in enumerate(h_proj) if value >= h_threshold]
    v_lines = [i for i, value in enumerate(v_proj) if value >= v_threshold]

    h_groups = group_positions(h_lines)
    v_groups = group_positions(v_lines)
    h_centers = [int((a + b) / 2) for a, b in h_groups]
    v_centers = [int((a + b) / 2) for a, b in v_groups]

    used_fallback_bottom = False
    if len(h_centers) >= 3:
        # In the generous candidate area the first horizontal line is usually
        # the row above correction content; the second line is the real top
        # border of the correction-content cell.
        top = h_centers[1]
        bottom = h_centers[-1]
    elif len(h_centers) >= 2:
        # Some pages have a faint lower border, so only the upper row lines are
        # detected. Keep the real top as the second line and use the expected
        # lower part of the candidate as a safe bottom fallback.
        top = h_centers[-1]
        bottom = int(h * 0.94)
        used_fallback_bottom = True
    else:
        top = int(h * 0.08)
        bottom = int(h * 0.82)
        used_fallback_bottom = True

    # Candidate includes left label column. Use the second vertical line when present:
    # first line = outer left table edge, second line = text cell left edge.
    if len(v_centers) >= 3:
        left = v_centers[1]
        right = v_centers[-1]
    elif len(v_centers) >= 2:
        left = v_centers[0]
        right = v_centers[-1]
    else:
        left = int(w * 0.10)
        right = int(w * 0.98)

    # Crop just inside the detected borders to remove black lines.
    inset = max(6, int(RENDER_SCALE * 2))
    left = min(max(left + inset, 0), w - 2)
    right = max(min(right - inset, w), left + 2)
    top = min(max(top + inset, 0), h - 2)
    bottom = max(min(bottom - inset, h), top + 2)

    crop_w = right - left
    crop_h = bottom - top
    if crop_h < int(h * 0.45) or (crop_w / max(crop_h, 1)) > 5.0:
        # Last-resort guard against accepting the row above correction content
        # as the whole crop. This is easy to spot by its extreme aspect ratio.
        if h_centers:
            top = min(max(h_centers[-1] + inset, 0), h - 2)
        else:
            top = int(h * 0.16)
        bottom = int(h * 0.94) - inset
        bottom = max(min(bottom, h), top + 2)
        used_fallback_bottom = True

    debug = {
        "h_centers": h_centers,
        "v_centers": v_centers,
        "image_size": [w, h],
        "thresholds": {"horizontal": h_threshold, "vertical": v_threshold},
        "used_fallback_bottom": used_fallback_bottom,
    }
    return left, top, right, bottom, debug


def group_positions(values: list[int], max_gap: int = 4) -> list[tuple[int, int]]:
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


def image_to_pdf(image: Image.Image, out_pdf: Path) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    width, height = image.size
    page = doc.new_page(width=width, height=height)
    png_bytes = io.BytesIO()
    image.save(png_bytes, format="PNG")
    page.insert_image(page.rect, stream=png_bytes.getvalue())
    doc.save(out_pdf, garbage=4, deflate=True)
    doc.close()


def process_pdf(pdf_path: Path, out_dir: Path, write_pdf: bool = True) -> dict:
    doc = fitz.open(pdf_path)
    if doc.page_count != 1:
        doc.close()
        raise ValueError(f"Expected 1 page, got {doc.page_count}: {pdf_path}")
    page = doc[0]

    candidate, candidate_rect = render_clip(page, CANDIDATE_RECT)
    bounds = find_line_bounds(candidate)
    left, top, right, bottom, debug = bounds

    stem = pdf_path.stem
    candidate_png = out_dir / f"{stem}__candidate.png"
    detected_png = out_dir / f"{stem}__detected.png"
    content_png = out_dir / f"{stem}__content.png"
    content_pdf = out_dir / f"{stem}__content.pdf" if write_pdf else None

    candidate.save(candidate_png, optimize=True)

    detected = candidate.copy()
    draw = ImageDraw.Draw(detected)
    draw.rectangle((left, top, right, bottom), outline=(30, 150, 80), width=6)
    detected.save(detected_png, optimize=True)

    content = candidate.crop((left, top, right, bottom))
    content.save(content_png, optimize=True)
    if content_pdf is not None:
        image_to_pdf(content, content_pdf)

    doc.close()
    return {
        "source_pdf": str(pdf_path),
        "candidate_rect_pdf_points": [round(candidate_rect.x0, 2), round(candidate_rect.y0, 2), round(candidate_rect.x1, 2), round(candidate_rect.y1, 2)],
        "detected_bounds_px": [left, top, right, bottom],
        "candidate_png": str(candidate_png),
        "detected_png": str(detected_png),
        "content_png": str(content_png),
        "content_pdf": str(content_pdf) if content_pdf is not None else "",
        "debug": debug,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Test line-based correction-cell cropping.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--png-only", action="store_true", help="Only write PNG previews, not content PDFs.")
    parser.add_argument("--out-dir-name", default="_line_crop_test", help="Output directory name under the batch directory.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    out_dir = batch_dir / args.out_dir_name
    manifest_path = out_dir / "line_crop_manifest.json"

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    clear_dir(out_dir)

    records = []
    for index, pdf_path in enumerate(pdf_files, 1):
        print(f"[{index}/{len(pdf_files)}] {pdf_path.name}")
        records.append(process_pdf(pdf_path, out_dir, write_pdf=not args.png_only))

    manifest = {
        "batch": args.batch,
        "scan_dir": str(scan_dir),
        "out_dir": str(out_dir),
        "render_scale": RENDER_SCALE,
        "png_only": args.png_only,
        "candidate_rect": [round(CANDIDATE_RECT.x0, 2), round(CANDIDATE_RECT.y0, 2), round(CANDIDATE_RECT.x1, 2), round(CANDIDATE_RECT.y1, 2)],
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
