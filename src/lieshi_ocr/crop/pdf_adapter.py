"""Minimal PyMuPDF adapter for explicit PDF crop operations.

Planning functions read only PDF metadata and return data structures. The only
function that writes a file is `save_pdf_crop`, and it requires an explicit
output path from the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from .geometry import PdfRect

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class PdfCropPlan:
    """A dry-run description of one PDF crop operation."""

    source_pdf: str
    page_index: int
    page_rect: PdfRect
    requested_rect: PdfRect
    clip_rect: PdfRect
    output_pdf: str = ""
    warnings: tuple[str, ...] = ()

    @property
    def would_write(self) -> bool:
        return bool(self.output_pdf)

    def to_json(self) -> JsonDict:
        return {
            "source_pdf": self.source_pdf,
            "page_index": self.page_index,
            "page_rect": self.page_rect.to_list(),
            "requested_rect": self.requested_rect.to_list(),
            "clip_rect": self.clip_rect.to_list(),
            "output_pdf": self.output_pdf,
            "would_write": self.would_write,
            "warnings": list(self.warnings),
        }


def read_pdf_page_rect(pdf_path: str | Path, page_index: int = 0) -> PdfRect:
    """Read one page size from a PDF without writing any files."""

    with fitz.open(pdf_path) as doc:
        page = _get_page(doc, page_index)
        rect = page.rect
        return PdfRect(rect.x0, rect.y0, rect.x1, rect.y1)


def plan_pdf_crop(
    source_pdf: str | Path,
    clip_rect: PdfRect,
    page_index: int = 0,
    output_pdf: str | Path | None = None,
) -> PdfCropPlan:
    """Return a dry-run crop plan, clipping the requested rect to the page."""

    source_path = Path(source_pdf)
    page_rect = read_pdf_page_rect(source_path, page_index=page_index)
    clipped = clip_rect.clip_to(page_rect)
    warnings: list[str] = []
    if clipped.is_empty:
        warnings.append("clip_rect_empty")
    elif clipped != clip_rect:
        warnings.append("clip_rect_clipped_to_page")

    return PdfCropPlan(
        source_pdf=source_path.as_posix(),
        page_index=page_index,
        page_rect=page_rect,
        requested_rect=clip_rect,
        clip_rect=clipped,
        output_pdf="" if output_pdf is None else Path(output_pdf).as_posix(),
        warnings=tuple(warnings),
    )


def save_pdf_crop(
    source_pdf: str | Path,
    output_pdf: str | Path,
    clip_rect: PdfRect,
    page_index: int = 0,
    overwrite: bool = False,
    create_parents: bool = False,
) -> PdfCropPlan:
    """Write one cropped PDF to an explicit output path."""

    source_path = Path(source_pdf)
    output_path = Path(output_pdf)
    plan = plan_pdf_crop(source_path, clip_rect, page_index=page_index, output_pdf=output_path)
    if plan.clip_rect.is_empty:
        raise ValueError(f"Cannot save empty crop rect: {plan.clip_rect}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output PDF already exists: {output_path}")
    if create_parents:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(source_path) as src_doc:
        page = _get_page(src_doc, page_index)
        with fitz.open() as out_doc:
            width = plan.clip_rect.width
            height = plan.clip_rect.height
            out_page = out_doc.new_page(width=width, height=height)
            out_page.show_pdf_page(out_page.rect, src_doc, page.number, clip=_to_fitz_rect(plan.clip_rect))
            out_doc.save(output_path, garbage=4, deflate=True)

    return plan


def _get_page(doc: fitz.Document, page_index: int) -> fitz.Page:
    if page_index < 0 or page_index >= doc.page_count:
        raise IndexError(f"PDF page index out of range: {page_index}; page_count={doc.page_count}")
    return doc[page_index]


def _to_fitz_rect(rect: PdfRect) -> fitz.Rect:
    return fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
