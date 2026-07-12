"""Optional OpenCV adapter for refining the name-value cell crop."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz

from .geometry import PdfRect
from .line_rules import bounds_to_pdf_rect, group_centers, group_positions, name_cell_bounds_from_lines

DEFAULT_RENDER_SCALE = 5.0


@dataclass(frozen=True)
class NameCellDetection:
    candidate_rect: PdfRect
    final_rect: PdfRect
    image_size: tuple[int, int]
    vertical_centers: tuple[int, ...]
    horizontal_centers: tuple[int, ...]
    crop_method: str
    warnings: tuple[str, ...] = ()
    debug_overlay: str = ""
    debug: dict[str, Any] = field(default_factory=dict)

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "crop_method": self.crop_method,
            "candidate_rect": self.candidate_rect.to_list(),
            "final_rect": self.final_rect.to_list(),
            "vertical_centers": list(self.vertical_centers),
            "horizontal_centers": list(self.horizontal_centers),
            "debug_overlay": self.debug_overlay,
        }


def detect_name_cell(
    pdf_path: str | Path,
    candidate_rect: PdfRect,
    page_index: int = 0,
    scale: float = DEFAULT_RENDER_SCALE,
    debug_output: str | Path | None = None,
) -> NameCellDetection:
    """Render a candidate area, detect table lines, and return a narrower PDF rect."""

    image, rendered_rect = _render_candidate(pdf_path, candidate_rect, page_index, scale)
    vertical_centers, horizontal_centers = detect_table_line_centers(image)
    detection_succeeded = len(vertical_centers) >= 3 and len(horizontal_centers) >= 1
    if detection_succeeded:
        cell = name_cell_bounds_from_lines(
            image_size=(image.shape[1], image.shape[0]),
            vertical_centers=vertical_centers,
            horizontal_centers=horizontal_centers,
            scale=scale,
        )
        crop_method = "name_cell_lines"
        warnings: tuple[str, ...] = ()
    else:
        cell = name_cell_bounds_from_lines(
            image_size=(image.shape[1], image.shape[0]),
            vertical_centers=(),
            horizontal_centers=(),
            scale=scale,
        )
        crop_method = "name_cell_fallback"
        warnings = ("name_cell_detection_fallback",)

    final_rect = bounds_to_pdf_rect(cell.bounds, (image.shape[1], image.shape[0]), rendered_rect)
    if final_rect.width >= rendered_rect.width or final_rect.height >= rendered_rect.height:
        raise ValueError("Refined name crop must be smaller than its candidate rectangle")

    overlay_path = ""
    if debug_output is not None:
        overlay_path = _write_debug_overlay(
            image,
            cell.bounds.to_tuple(),
            vertical_centers,
            horizontal_centers,
            debug_output,
        )

    return NameCellDetection(
        candidate_rect=rendered_rect,
        final_rect=final_rect,
        image_size=(image.shape[1], image.shape[0]),
        vertical_centers=vertical_centers,
        horizontal_centers=horizontal_centers,
        crop_method=crop_method,
        warnings=warnings,
        debug_overlay=overlay_path,
        debug=cell.debug,
    )


def detect_table_line_centers(image: Any) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return vertical and horizontal table-line centers from an RGB image array."""

    cv2, numpy = _vision_modules()
    if image is None or not hasattr(image, "shape") or len(image.shape) not in {2, 3}:
        raise ValueError("Expected a grayscale or RGB image array")
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = numpy.asarray(image)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        12,
    )
    height, width = binary.shape
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(35, int(height * 0.45))))
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(45, int(width * 0.2)), 1))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

    vertical_projection = vertical.sum(axis=0) / 255
    horizontal_projection = horizontal.sum(axis=1) / 255
    vertical_positions = [
        index for index, value in enumerate(vertical_projection) if value >= max(25, height * 0.35)
    ]
    horizontal_positions = [
        index for index, value in enumerate(horizontal_projection) if value >= max(45, width * 0.40)
    ]
    return (
        group_centers(group_positions(vertical_positions, max_gap=5)),
        group_centers(group_positions(horizontal_positions, max_gap=5)),
    )


def _render_candidate(
    pdf_path: str | Path,
    candidate_rect: PdfRect,
    page_index: int,
    scale: float,
) -> tuple[Any, PdfRect]:
    _, numpy = _vision_modules()
    with fitz.open(pdf_path) as document:
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError(f"PDF page index out of range: {page_index}; page_count={document.page_count}")
        page = document[page_index]
        page_rect = PdfRect(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1)
        rendered_rect = candidate_rect.clip_to(page_rect)
        if rendered_rect.is_empty:
            raise ValueError(f"Name candidate rectangle is empty: {rendered_rect}")
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            clip=fitz.Rect(rendered_rect.x0, rendered_rect.y0, rendered_rect.x1, rendered_rect.y1),
            alpha=False,
        )
        image = numpy.frombuffer(pixmap.samples, dtype=numpy.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
        if pixmap.n == 4:
            image = image[:, :, :3]
        return image.copy(), rendered_rect


def _write_debug_overlay(
    image: Any,
    bounds: tuple[int, int, int, int],
    vertical_centers: tuple[int, ...],
    horizontal_centers: tuple[int, ...],
    output_path: str | Path,
) -> str:
    cv2, _ = _vision_modules()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    overlay = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    height, width = overlay.shape[:2]
    for center in vertical_centers:
        cv2.line(overlay, (center, 0), (center, height - 1), (0, 180, 255), 1)
    for center in horizontal_centers:
        cv2.line(overlay, (0, center), (width - 1, center), (0, 180, 255), 1)
    left, top, right, bottom = bounds
    cv2.rectangle(overlay, (left, top), (right, bottom), (255, 80, 40), 3)
    if not cv2.imwrite(str(target), overlay):
        raise OSError(f"Failed to write debug overlay: {target}")
    return target.as_posix()


def _vision_modules() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy
    except ImportError as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError('Name-cell refinement requires: python -m pip install -e ".[vision]"') from exc
    return cv2, numpy
