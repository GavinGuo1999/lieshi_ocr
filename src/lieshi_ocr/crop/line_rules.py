"""Pure crop-geometry rules derived from legacy line-based scripts.

The functions in this module accept already-detected line positions or manual
test coordinates. They do not render PDFs, inspect images, run OpenCV/OCR, or
read/write files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .geometry import PdfRect
from .naming import safe_filename

ImageSize = tuple[int, int]
LineGroup = tuple[int, int]


@dataclass(frozen=True)
class PixelBounds:
    """Pixel-space crop bounds: left, top, right, bottom."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)

    def to_list(self) -> list[int]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass(frozen=True)
class CellBounds:
    """A derived crop cell plus diagnostic metadata."""

    bounds: PixelBounds
    debug: dict[str, Any]


def group_positions(values: Sequence[int], max_gap: int = 4) -> tuple[LineGroup, ...]:
    """Group adjacent pixel positions into inclusive line runs."""

    if not values:
        return ()
    ordered = sorted(int(value) for value in values)
    groups: list[LineGroup] = []
    start = prev = ordered[0]
    for value in ordered[1:]:
        if value - prev <= max_gap:
            prev = value
        else:
            groups.append((start, prev))
            start = prev = value
    groups.append((start, prev))
    return tuple(groups)


def group_centers(groups: Sequence[LineGroup]) -> tuple[int, ...]:
    """Return integer centers for inclusive line runs."""

    return tuple(int((start + end) / 2) for start, end in groups)


def bounds_to_pdf_rect(bounds: PixelBounds, image_size: ImageSize, candidate_rect: PdfRect) -> PdfRect:
    """Map pixel bounds inside a rendered candidate image back to PDF points."""

    return candidate_rect.px_bounds_to_pdf_rect(bounds.to_tuple(), image_size)


def legacy_region_stem(code: str, name: str, source_stem: str) -> str:
    """Return the stable legacy output stem for region crops."""

    return safe_filename(f"{code}_{name}__{source_stem}")


def region_output_names(stem: str, regions: Sequence[str] = ("code", "name", "correction")) -> dict[str, str]:
    """Return deterministic per-region output PDF names without checking disk."""

    safe_stem = safe_filename(stem)
    return {region: f"{safe_stem}__{safe_filename(region)}.pdf" for region in regions}


def name_cell_bounds_from_lines(
    image_size: ImageSize,
    vertical_centers: Sequence[int],
    horizontal_centers: Sequence[int],
    scale: float = 5.0,
) -> CellBounds:
    """Derive the name-value cell bounds from simulated table-line centers."""

    width, height = _validate_image_size(image_size)
    v_centers = tuple(int(value) for value in vertical_centers)
    h_centers = tuple(int(value) for value in horizontal_centers)

    if len(v_centers) >= 3:
        left = v_centers[1]
        right = v_centers[2]
        method = "line"
    elif len(v_centers) >= 2:
        left = v_centers[0]
        right = v_centers[1]
        method = "line_partial"
    else:
        left = int(width * 0.36)
        right = int(width * 0.86)
        method = "fallback"

    if len(h_centers) >= 2:
        top = h_centers[0]
        bottom = h_centers[-1]
        h_method = "line_pair"
    elif len(h_centers) == 1:
        top = h_centers[0]
        bottom = min(height - 1, top + int(height * 0.52))
        h_method = "single_top_line"
    else:
        top = int(height * 0.34)
        bottom = int(height * 0.90)
        h_method = "fallback"

    bounds = _inset_and_clamp(
        image_size=(width, height),
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        inset_x=max(8, int(scale * 2)),
        inset_y=max(4, int(scale * 1.2)),
    )
    return CellBounds(
        bounds=bounds,
        debug={
            "image_size": [width, height],
            "v_centers": list(v_centers),
            "h_centers": list(h_centers),
            "method": method,
            "h_method": h_method,
        },
    )


def correction_cell_bounds_from_lines(
    image_size: ImageSize,
    horizontal_centers: Sequence[int],
    vertical_centers: Sequence[int],
    scale: float = 3.0,
) -> CellBounds:
    """Derive correction-content cell bounds from simulated table-line centers."""

    width, height = _validate_image_size(image_size)
    h_centers = tuple(int(value) for value in horizontal_centers)
    v_centers = tuple(int(value) for value in vertical_centers)

    used_fallback_bottom = False
    if len(h_centers) >= 3:
        top = h_centers[1]
        bottom = h_centers[-1]
    elif len(h_centers) >= 2:
        top = h_centers[-1]
        bottom = int(height * 0.94)
        used_fallback_bottom = True
    else:
        top = int(height * 0.08)
        bottom = int(height * 0.82)
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
        left = int(width * 0.10)
        right = int(width * 0.98)
        v_method = "fallback"

    inset = max(6, int(scale * 2))
    top_inset = max(1, int(scale * 0.7))
    bounds = _inset_and_clamp(
        image_size=(width, height),
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        inset_x=inset,
        inset_y=inset,
        top_inset=top_inset,
    )

    if bounds.height < int(height * 0.45) or (bounds.width / max(bounds.height, 1)) > 5.0:
        if h_centers:
            top = min(max(h_centers[-1] + inset, 0), height - 2)
        else:
            top = int(height * 0.16)
        bottom = int(height * 0.94) - inset
        bottom = max(min(bottom, height), top + 2)
        bounds = PixelBounds(bounds.left, top, bounds.right, bottom)
        used_fallback_bottom = True

    return CellBounds(
        bounds=bounds,
        debug={
            "h_centers": list(h_centers),
            "v_centers": list(v_centers),
            "image_size": [width, height],
            "v_method": v_method,
            "used_fallback_bottom": used_fallback_bottom,
        },
    )


def _validate_image_size(image_size: ImageSize) -> ImageSize:
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image size: {image_size}")
    return int(width), int(height)


def _inset_and_clamp(
    image_size: ImageSize,
    left: int,
    top: int,
    right: int,
    bottom: int,
    inset_x: int,
    inset_y: int,
    top_inset: int | None = None,
) -> PixelBounds:
    width, height = image_size
    actual_top_inset = inset_y if top_inset is None else top_inset
    left = min(max(left + inset_x, 0), width - 2)
    right = max(min(right - inset_x, width), left + 2)
    top = min(max(top + actual_top_inset, 0), height - 2)
    bottom = max(min(bottom - inset_y, height), top + 2)
    return PixelBounds(left=left, top=top, right=right, bottom=bottom)
