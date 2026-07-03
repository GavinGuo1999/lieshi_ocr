#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Full region-based batch pipeline for scanned review forms.

Outputs:
- data/<batch>/cut_paddle/<code>_<name>__<source_stem>.pdf
- data/<batch>/extracted_paddle/<code>_<name>__<source_stem>.json
- data/<batch>/extracted_paddle/region_manifest.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import time
from collections import Counter
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image, ImageOps
from rapidocr_onnxruntime import RapidOCR

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover - exercised when dependency is missing.
    PaddleOCR = None


BASE_DIR = Path(r"D:\ying_min_mineru")
DEFAULT_BATCH = "20260626"

CODE_SCALE = 4.0
NAME_SCALE = 5.0
CORRECTION_SCALE = 3.0
OCR_SCALE = 4.0

PREFIX = "晋祁县"
UNKNOWN_NAME = "未识别姓名"
FAILED_WARNINGS = {"code_not_found", "name_not_found", "correction_text_empty"}
NEW_SCAN_STEMS = {f"2026-06-2617_41_100{i}" for i in range(238, 244)}

FIELD_PATTERN = (
    r"姓名|籍贯|出生时间|入党/入团时间|入党时间|入团时间|"
    r"参加革命（工作）时间|参加革命\(工作\)时间|参加革命时间|参加工作时间|"
    r"政治面貌|民族|生前（部队）单位及曾任职务|生前\(部队\)单位及曾任职务|"
    r"生前部队单位及曾任职务|生前单位及曾任职务|曾任职务|"
    r"牺牲时间|牺牲地点|牺牲原因|栖牲原因|事迹|安葬地|安葬地点"
)

# PDF point coordinates on the original scan page.
CODE_RECT = fitz.Rect(365, 35, 560, 105)
NAME_CANDIDATE_RECT = fitz.Rect(55, 112, 230, 158)
CORRECTION_CANDIDATE_RECT = fitz.Rect(35, 280, 560, 545)


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


def render_clip(page: fitz.Page, rect: fitz.Rect, scale: float) -> tuple[Image.Image, fitz.Rect]:
    rect = rect & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    return image, rect


def px_bounds_to_pdf_rect(bounds: tuple[int, int, int, int], image: Image.Image, rect: fitz.Rect) -> fitz.Rect:
    left, top, right, bottom = bounds
    w, h = image.size
    return fitz.Rect(
        rect.x0 + rect.width * left / w,
        rect.y0 + rect.height * top / h,
        rect.x0 + rect.width * right / w,
        rect.y0 + rect.height * bottom / h,
    )


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
        top = h_centers[0]
        bottom = min(h - 1, top + int(h * 0.52))
        h_method = "single_top_line"
    else:
        top = int(h * 0.34)
        bottom = int(h * 0.90)
        h_method = "fallback"

    inset_x = max(8, int(NAME_SCALE * 2))
    inset_y = max(4, int(NAME_SCALE * 1.2))
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


def find_correction_cell_bounds(image: Image.Image) -> tuple[int, int, int, int, dict]:
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

    h_centers = [int((a + b) / 2) for a, b in group_positions(h_lines, max_gap=4)]
    v_centers = [int((a + b) / 2) for a, b in group_positions(v_lines, max_gap=4)]

    used_fallback_bottom = False
    if len(h_centers) >= 3:
        top = h_centers[1]
        bottom = h_centers[-1]
    elif len(h_centers) >= 2:
        top = h_centers[-1]
        bottom = int(h * 0.94)
        used_fallback_bottom = True
    else:
        top = int(h * 0.08)
        bottom = int(h * 0.82)
        used_fallback_bottom = True

    if len(v_centers) >= 3:
        left = v_centers[1]
        right = v_centers[-1]
        v_method = "line"
    elif len(v_centers) >= 2:
        left = v_centers[0]
        right = v_centers[-1]
        v_method = "line_partial"
    else:
        left = int(w * 0.10)
        right = int(w * 0.98)
        v_method = "fallback"

    inset = max(6, int(CORRECTION_SCALE * 2))
    top_inset = max(1, int(CORRECTION_SCALE * 0.7))
    left = min(max(left + inset, 0), w - 2)
    right = max(min(right - inset, w), left + 2)
    top = min(max(top + top_inset, 0), h - 2)
    bottom = max(min(bottom - inset, h), top + 2)

    crop_w = right - left
    crop_h = bottom - top
    if crop_h < int(h * 0.45) or (crop_w / max(crop_h, 1)) > 5.0:
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
        "v_method": v_method,
        "used_fallback_bottom": used_fallback_bottom,
    }
    return left, top, right, bottom, debug


def ocr_image(ocr: RapidOCR, image: Image.Image) -> list[dict]:
    result, _ = ocr(image, return_img=False)
    rows = []
    for item in result or []:
        rows.append({"text": str(item[1]), "score": float(item[2])})
    return rows


def ocr_paddle_image(ocr, image: Image.Image) -> list[dict]:
    arr = np.array(image.convert("RGB"))
    try:
        result = ocr.ocr(arr, cls=True)
    except TypeError:
        result = ocr.ocr(arr)
    return normalize_paddle_result(result)


def normalize_paddle_result(result) -> list[dict]:
    rows = []
    if not result:
        return rows

    candidates = result
    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
        candidates = result[0]

    for item in candidates or []:
        text = ""
        score = 0.0
        box = None
        if isinstance(item, dict):
            text = item.get("text") or item.get("rec_text") or ""
            score = item.get("score") or item.get("rec_score") or 0.0
            box = item.get("box") or item.get("dt_polys")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            box = item[0]
            payload = item[1]
            if isinstance(payload, (list, tuple)) and payload:
                text = payload[0]
                score = payload[1] if len(payload) > 1 else 0.0
            else:
                text = payload
        if str(text).strip():
            rows.append({"text": str(text), "score": float(score or 0.0), "box": box})
    return rows


def pad_for_ocr(image: Image.Image, border: int = 24) -> Image.Image:
    return ImageOps.expand(image, border=border, fill="white")


def join_text(rows: list[dict], sep: str = "\n") -> str:
    return sep.join(row["text"].strip() for row in rows if row["text"].strip())


def extract_code(text: str) -> str:
    compact = re.sub(r"\s+", "", text or "")
    match = re.search(r"晋?祁?县?(\d{4,6})", compact)
    if match:
        return PREFIX + match.group(1).zfill(6)
    return ""


def clean_name(text: str) -> str:
    text = re.sub(r"\s+", "", text or "")
    text = re.sub(r"(姓名|填表人|曾用名|王娴|审核|意见)", "", text)
    text = re.sub(r"[^\u4e00-\u9fff·]", "", text)
    if 2 <= len(text) <= 5:
        return text
    return ""


def extract_name(name_text: str, correction_text: str) -> str:
    for line in name_text.splitlines():
        name = clean_name(line)
        if name:
            return name

    match = re.search(r"姓名补充完善为[“\"']?([\u4e00-\u9fff·]{2,5})", correction_text or "")
    if match:
        name = clean_name(match.group(1))
        if name:
            return name

    for match in re.finditer(r"([\u4e00-\u9fff·]{2,5})烈士", correction_text or ""):
        name = clean_name(match.group(1))
        if name:
            return name
    return ""


def clean_correction_text(text: str) -> str:
    text = (text or "").replace("\r", "\n")
    text = re.sub(r"[ \t]+", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = text.replace("：", ":")
    return text.strip()


def trim_to_first_correction_item(text: str) -> str:
    match = re.search(rf"({FIELD_PATTERN})补充完善为", text or "")
    if not match:
        return text
    return text[match.start() :].strip()


def choose_correction_text(primary_text: str, fallback_text: str) -> tuple[str, str]:
    primary = clean_correction_text(primary_text)
    fallback = clean_correction_text(fallback_text)
    primary_signal = primary.count("补充完善为") + primary.count("理由")
    fallback_signal = fallback.count("补充完善为") + fallback.count("理由")
    if len(primary) >= 20 and primary_signal > 0:
        return primary, "paddle_clean_region"
    if fallback and (len(primary) < 20 or fallback_signal > primary_signal):
        return fallback, "paddle_extended_region"
    return primary, "paddle_clean_region"


def classify_quality(warnings: list[str]) -> str:
    if any(warning.startswith("process_error:") or warning in FAILED_WARNINGS for warning in warnings):
        return "failed"
    if warnings:
        return "review_needed"
    return "ok"


def create_paddle_ocr():
    attempts = [
        {
            "lang": "ch",
            "ocr_version": "PP-OCRv5",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "lang": "ch",
            "ocr_version": "PP-OCRv4",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {"lang": "ch", "use_textline_orientation": True},
        {"lang": "ch", "use_angle_cls": True},
        {"lang": "ch"},
    ]
    last_exc = None
    for kwargs in attempts:
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError) as exc:
            last_exc = exc
    raise RuntimeError(f"Failed to initialize PaddleOCR: {last_exc}") from last_exc


def parse_correction_items(text: str) -> dict:
    clean = clean_correction_text(text).replace("\n", "")
    pattern = re.compile(
        rf"(?P<field>{FIELD_PATTERN})补充完善为[“\"']?"
        r"(?P<value>.*?)[”\"']?理由[:：]"
        rf"(?P<reason>.*?)(?=(?:{FIELD_PATTERN})补充完善为|$)"
    )
    items = {}
    for match in pattern.finditer(clean):
        field = match.group("field").strip("。；;，,、")
        if field == "栖牲原因":
            field = "牺牲原因"
        value = match.group("value").strip("。；;，,")
        reason = match.group("reason").strip("。；;，,")
        if field and (value or reason):
            items[field] = {"value": value, "reason": reason}
    return items


def save_pdf_region(src_doc: fitz.Document, rect: fitz.Rect, out_pdf: Path) -> None:
    out_doc = fitz.open()
    out_page = out_doc.new_page(width=rect.width, height=rect.height)
    out_page.show_pdf_page(out_page.rect, src_doc, 0, clip=rect)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc.save(out_pdf, garbage=4, deflate=True)
    out_doc.close()


def unique_output_paths(cut_dir: Path, extracted_dir: Path, base: str) -> tuple[Path, Path, str]:
    candidate = base
    suffix = 2
    while True:
        cut_pdf = cut_dir / f"{candidate}.pdf"
        json_path = extracted_dir / f"{candidate}.json"
        if not cut_pdf.exists() and not json_path.exists():
            return cut_pdf, json_path, candidate
        candidate = f"{base}__dup{suffix}"
        suffix += 1


def process_one(rapid_ocr: RapidOCR, paddle_ocr, src_pdf: Path, cut_dir: Path, extracted_dir: Path) -> dict:
    src_doc = fitz.open(src_pdf)
    try:
        if src_doc.page_count != 1:
            raise ValueError(f"Expected 1 page, got {src_doc.page_count}: {src_pdf}")

        page = src_doc[0]
        warnings = []

        code_image, code_rect = render_clip(page, CODE_RECT, CODE_SCALE)
        code_rows = ocr_image(rapid_ocr, pad_for_ocr(code_image, border=12))
        code_text = join_text(code_rows)
        code = extract_code(code_text)
        if not code:
            warnings.append("code_not_found")
            code = src_pdf.stem

        name_candidate, name_candidate_rect = render_clip(page, NAME_CANDIDATE_RECT, NAME_SCALE)
        name_bounds = find_name_cell_bounds(name_candidate)
        name_left, name_top, name_right, name_bottom, name_debug = name_bounds
        name_image = name_candidate.crop((name_left, name_top, name_right, name_bottom))
        name_rect = px_bounds_to_pdf_rect((name_left, name_top, name_right, name_bottom), name_candidate, name_candidate_rect)
        name_rows = ocr_image(rapid_ocr, pad_for_ocr(name_image, border=12))
        name_text = join_text(name_rows)

        correction_candidate, correction_candidate_rect = render_clip(page, CORRECTION_CANDIDATE_RECT, CORRECTION_SCALE)
        correction_bounds = find_correction_cell_bounds(correction_candidate)
        corr_left, corr_top, corr_right, corr_bottom, correction_debug = correction_bounds
        correction_image = correction_candidate.crop((corr_left, corr_top, corr_right, corr_bottom))
        ocr_top = corr_top
        h_centers = correction_debug.get("h_centers", [])
        if len(h_centers) >= 3:
            ocr_top = max(0, h_centers[0] + max(1, int(CORRECTION_SCALE * 0.7)))
        correction_ocr_image = correction_candidate.crop((corr_left, ocr_top, corr_right, corr_bottom))
        correction_rect = px_bounds_to_pdf_rect(
            (corr_left, corr_top, corr_right, corr_bottom),
            correction_candidate,
            correction_candidate_rect,
        )
        correction_rows_clean = ocr_paddle_image(paddle_ocr, pad_for_ocr(correction_image, border=28))
        correction_rows_extended = []
        correction_text_extended = ""
        correction_text_clean_region = join_text(correction_rows_clean)
        correction_text_raw, correction_ocr_source = choose_correction_text(correction_text_clean_region, "")
        if len(correction_text_raw) < 20:
            correction_rows_extended = ocr_paddle_image(paddle_ocr, pad_for_ocr(correction_ocr_image, border=28))
            correction_text_extended = join_text(correction_rows_extended)
            correction_text_raw, correction_ocr_source = choose_correction_text(
                correction_text_clean_region,
                correction_text_extended,
            )
        correction_rows = correction_rows_clean if correction_ocr_source == "paddle_clean_region" else correction_rows_extended
        correction_text_clean = trim_to_first_correction_item(clean_correction_text(correction_text_raw))

        name = extract_name(name_text, correction_text_clean)
        if not name:
            warnings.append("name_not_found")
            name = UNKNOWN_NAME
        elif name == "王娴":
            warnings.append("name_suspicious")

        correction_items = parse_correction_items(correction_text_clean)
        item_marker_count = correction_text_clean.count("补充完善为")
        reason_marker_count = correction_text_clean.count("理由")
        if not correction_text_clean:
            warnings.append("correction_text_empty")
        elif len(correction_text_clean) < 20:
            warnings.append("correction_text_too_short")
        for keyword, warning in (("补充", "correction_missing_buchong"), ("理由", "correction_missing_reason"), ("依据", "correction_missing_yiju")):
            if keyword not in correction_text_clean:
                warnings.append(warning)
        if not correction_items:
            warnings.append("parse_no_items")
        if (
            item_marker_count > len(correction_items)
            or reason_marker_count > len(correction_items) + 1
            or "。”理由" in correction_text_clean
            or "。”理由:" in correction_text_clean
        ):
            warnings.append("parse_low_confidence")

        corr_w, corr_h = correction_image.size
        if corr_h < 250 or corr_w < 900 or (corr_w / max(corr_h, 1)) > 5:
            warnings.append("correction_crop_suspicious")

        base = safe_filename(f"{code}_{name}__{src_pdf.stem}")
        cut_pdf, json_path, output_stem = unique_output_paths(cut_dir, extracted_dir, base)
        if output_stem != base:
            warnings.append("duplicate_output_name")

        save_pdf_region(src_doc, correction_rect, cut_pdf)

        quality = classify_quality(warnings)
        record = {
            "source_pdf": str(src_pdf),
            "source_stem": src_pdf.stem,
            "code": code,
            "name": name,
            "quality": quality,
            "cut_pdf": str(cut_pdf),
            "json": str(json_path),
            "ocr": {
                "code_text": code_text,
                "name_text": name_text,
                "correction_text_raw": correction_text_raw,
                "correction_ocr_engine": "paddleocr",
                "correction_ocr_source": correction_ocr_source,
                "correction_text_extended": correction_text_extended,
                "correction_text_clean_region": correction_text_clean_region,
                "correction_text_clean": correction_text_clean,
                "code_rows": code_rows,
                "name_rows": name_rows,
                "correction_rows": correction_rows,
                "correction_rows_extended": correction_rows_extended,
                "correction_rows_clean_region": correction_rows_clean,
            },
            "correction_items": correction_items,
            "regions": {
                "code": {
                    "rect_pdf_points": rect_to_list(code_rect),
                    "image_size": list(code_image.size),
                },
                "name": {
                    "candidate_rect_pdf_points": rect_to_list(name_candidate_rect),
                    "detected_rect_pdf_points": rect_to_list(name_rect),
                    "detected_bounds_px": [name_left, name_top, name_right, name_bottom],
                    "image_size": list(name_image.size),
                    "debug": name_debug,
                },
                "correction": {
                    "candidate_rect_pdf_points": rect_to_list(correction_candidate_rect),
                    "detected_rect_pdf_points": rect_to_list(correction_rect),
                    "detected_bounds_px": [corr_left, corr_top, corr_right, corr_bottom],
                    "ocr_bounds_px": [corr_left, ocr_top, corr_right, corr_bottom],
                    "image_size": list(correction_image.size),
                    "ocr_image_size": list(correction_ocr_image.size),
                    "debug": correction_debug,
                },
            },
            "warnings": warnings,
            "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        extracted_dir.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "source_pdf": str(src_pdf),
            "source_stem": src_pdf.stem,
            "code": code,
            "name": name,
            "quality": quality,
            "cut_pdf": str(cut_pdf),
            "json": str(json_path),
            "warnings": warnings,
        }
    finally:
        src_doc.close()


def rect_to_list(rect: fitz.Rect) -> list[float]:
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def write_summary(
    summary_path: Path,
    manifest: dict,
    quality_counts: Counter,
    warning_counts: Counter,
    new_scan_records: list[dict],
) -> None:
    failed = [record for record in manifest["records"] if record.get("quality") == "failed"]
    review_needed = [record for record in manifest["records"] if record.get("quality") == "review_needed"]
    lines = [
        "# 20260626 PaddleOCR 稳定版流水线汇总",
        "",
        f"- 生成时间：{manifest['generated_at']}",
        f"- 输入目录：`{manifest['scan_dir']}`",
        f"- 裁剪输出：`{manifest['cut_dir']}`",
        f"- JSON 输出：`{manifest['extracted_dir']}`",
        f"- 总页数：{manifest['total']}",
        f"- ok：{quality_counts.get('ok', 0)}",
        f"- review_needed：{quality_counts.get('review_needed', 0)}",
        f"- failed：{quality_counts.get('failed', 0)}",
        "",
        "## Warning Counts",
        "",
    ]
    if warning_counts:
        for warning, count in sorted(warning_counts.items()):
            lines.append(f"- `{warning}`：{count}")
    else:
        lines.append("- 无")

    lines.extend(["", "## 新增 6 页", ""])
    if new_scan_records:
        lines.append("| source_stem | code | name | quality | warnings |")
        lines.append("| --- | --- | --- | --- | --- |")
        for record in sorted(new_scan_records, key=lambda item: item.get("source_stem", "")):
            warnings = ", ".join(record.get("warnings", []))
            lines.append(
                f"| `{record.get('source_stem', '')}` | `{record.get('code', '')}` | "
                f"{record.get('name', '')} | `{record.get('quality', '')}` | {warnings or '无'} |"
            )
    else:
        lines.append("- 本次运行范围未包含 `100238`-`100243`。")

    lines.extend(["", "## Failed Pages", ""])
    if failed:
        for record in failed:
            lines.append(f"- `{record.get('source_stem')}` `{record.get('code', '')}` {record.get('name', '')}: {', '.join(record.get('warnings', []))}")
    else:
        lines.append("- 无")

    lines.extend(["", "## Review Needed Pages", ""])
    if review_needed:
        for record in review_needed[:80]:
            lines.append(f"- `{record.get('source_stem')}` `{record.get('code', '')}` {record.get('name', '')}: {', '.join(record.get('warnings', []))}")
        if len(review_needed) > 80:
            lines.append(f"- 其余 {len(review_needed) - 80} 条见 `region_manifest.json`。")
    else:
        lines.append("- 无")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full region-based batch pipeline.")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=0, help="Use 0 for all files.")
    parser.add_argument("--clear-output", action="store_true", help="Clear cut/extracted before running.")
    parser.add_argument("--cut-dir-name", default="cut_paddle", help="Output PDF directory under the batch directory.")
    parser.add_argument("--extracted-dir-name", default="extracted_paddle", help="Output JSON directory under the batch directory.")
    parser.add_argument("--summary-name", default="paddle_run_summary.md", help="Summary markdown name under extracted dir.")
    args = parser.parse_args()

    batch_dir = BASE_DIR / "data" / args.batch
    scan_dir = batch_dir / "scan"
    cut_dir = batch_dir / args.cut_dir_name
    extracted_dir = batch_dir / args.extracted_dir_name

    pdf_files = sorted(scan_dir.glob("*.pdf"))
    if args.limit > 0:
        pdf_files = pdf_files[: args.limit]
    if not pdf_files:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")

    if args.clear_output:
        clear_dir(cut_dir)
        clear_dir(extracted_dir)
    else:
        cut_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)

    if PaddleOCR is None:
        raise RuntimeError(
            "PaddleOCR is not installed in this Python environment. "
            "Install it with: python -m pip install paddlepaddle paddleocr"
        )

    rapid_ocr = RapidOCR()
    paddle_ocr = create_paddle_ocr()
    records = []
    for index, src_pdf in enumerate(pdf_files, 1):
        print(f"[{index}/{len(pdf_files)}] {src_pdf.name}")
        try:
            record = process_one(rapid_ocr, paddle_ocr, src_pdf, cut_dir, extracted_dir)
        except Exception as exc:
            warnings = [f"process_error:{type(exc).__name__}:{exc}"]
            record = {
                "source_pdf": str(src_pdf),
                "source_stem": src_pdf.stem,
                "code": "",
                "name": "",
                "quality": "failed",
                "cut_pdf": "",
                "json": "",
                "warnings": warnings,
            }
        records.append(record)
        status = record.get("quality", "failed").upper()
        if record["warnings"]:
            status += ":" + ",".join(record["warnings"])
        print(f"  {status} {record.get('code', '')} {record.get('name', '')}")

    warning_counts = Counter(warning for record in records for warning in record.get("warnings", []))
    quality_counts = Counter(record.get("quality", "failed") for record in records)
    code_counts = Counter(record["code"] for record in records if record.get("code"))
    duplicate_codes = sorted(code for code, count in code_counts.items() if count > 1)
    new_scan_records = [record for record in records if record.get("source_stem") in NEW_SCAN_STEMS]

    manifest = {
        "batch": args.batch,
        "limit": args.limit,
        "scan_dir": str(scan_dir),
        "cut_dir": str(cut_dir),
        "extracted_dir": str(extracted_dir),
        "total": len(records),
        "ok": quality_counts.get("ok", 0),
        "quality_counts": dict(sorted(quality_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "duplicate_codes": duplicate_codes,
        "new_scan_records": new_scan_records,
        "records": records,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    manifest_path = extracted_dir / "region_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = extracted_dir / args.summary_name
    write_summary(summary_path, manifest, quality_counts, warning_counts, new_scan_records)
    print(f"manifest: {manifest_path}")
    print(f"summary: {summary_path}")
    print(
        f"total={manifest['total']} ok={quality_counts.get('ok', 0)} "
        f"review_needed={quality_counts.get('review_needed', 0)} "
        f"failed={quality_counts.get('failed', 0)} warnings={sum(warning_counts.values())}"
    )
    if warning_counts:
        print("warning_counts:")
        for warning, count in sorted(warning_counts.items()):
            print(f"  {warning}: {count}")
    if duplicate_codes:
        print("duplicate_codes:")
        for code in duplicate_codes:
            print(f"  {code}: {code_counts[code]}")


if __name__ == "__main__":
    main()
