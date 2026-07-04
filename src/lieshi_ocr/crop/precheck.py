"""Read-only crop precheck planning.

This module builds manifest data from known layouts and caller-provided PDF
paths. It does not open PDFs, create directories, write files, run OCR, or
touch Excel workbooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .layouts import CropLayout, REVIEW_FORM_SPLIT_LAYOUT
from .records import CropManifest, CropRecord, RegionRecord


def _display_path(path: str | Path) -> str:
    return Path(path).as_posix()


def _default_scan_dir(batch: str) -> Path:
    return Path("data") / "scan" / batch


def _default_out_dir(batch: str) -> Path:
    return Path("data") / "work" / batch / "crop_precheck"


def build_crop_precheck_manifest(
    batch: str,
    source_pdfs: Iterable[str | Path],
    layout: CropLayout = REVIEW_FORM_SPLIT_LAYOUT,
    scan_dir: str | Path | None = None,
    out_dir: str | Path | None = None,
) -> CropManifest:
    """Return a planned crop manifest without reading or writing files."""

    resolved_scan_dir = _default_scan_dir(batch) if scan_dir is None else Path(scan_dir)
    resolved_out_dir = _default_out_dir(batch) if out_dir is None else Path(out_dir)
    records: list[CropRecord] = []

    for source_pdf in source_pdfs:
        source_path = Path(source_pdf)
        source_stem = source_path.stem
        regions = [
            RegionRecord(
                region=region.name,
                pdf=_display_path(resolved_out_dir / f"{source_stem}__{region.name}.pdf"),
                clip_rect=region.rect,
                preview_png=_display_path(resolved_out_dir / "_preview" / f"{source_stem}__{region.name}.png"),
            )
            for region in layout.regions
        ]
        records.append(
            CropRecord(
                source_pdf=_display_path(source_path),
                source_stem=source_stem,
                regions=regions,
            )
        )

    return CropManifest(
        batch=batch,
        scan_dir=_display_path(resolved_scan_dir),
        out_dir=_display_path(resolved_out_dir),
        layout=layout.name,
        regions={region.name: region.rect for region in layout.regions},
        records=records,
    )
