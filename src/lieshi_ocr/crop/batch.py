"""Batch crop planning and explicit crop writing.

This module is allowed to read caller-selected PDFs and, when explicitly
requested, write crop PDFs and a manifest. It does not run OCR, call MinerU, or
read/write Excel workbooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable

from .geometry import PdfRect
from .layouts import CropLayout, REGION_PIPELINE_LAYOUT
from .pdf_adapter import plan_pdf_crop, save_pdf_crop

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CropRegionPlan:
    region: str
    requested_rect: PdfRect
    clip_rect: PdfRect
    output_pdf: str
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "region": self.region,
            "requested_rect": self.requested_rect.to_list(),
            "clip_rect": self.clip_rect.to_list(),
            "size": self.clip_rect.size_list(),
            "output_pdf": self.output_pdf,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class CropSourcePlan:
    source_pdf: str
    source_stem: str
    page_index: int
    page_rect: PdfRect
    regions: list[CropRegionPlan]
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "source_pdf": self.source_pdf,
            "source_stem": self.source_stem,
            "page_index": self.page_index,
            "page_rect": self.page_rect.to_list(),
            "regions": [region.to_json() for region in self.regions],
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class CropBatchManifest:
    batch: str
    scan_dir: str
    out_dir: str
    layout: str
    write_crops: bool
    records: list[CropSourcePlan]

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "scan_dir": self.scan_dir,
            "out_dir": self.out_dir,
            "layout": self.layout,
            "write_crops": self.write_crops,
            "total": len(self.records),
            "records": [record.to_json() for record in self.records],
        }


def discover_batch_pdfs(scan_dir: str | Path, limit: int = 0) -> list[Path]:
    """Return sorted PDFs from an explicit scan directory."""

    pdfs = sorted(Path(scan_dir).glob("*.pdf"))
    if limit > 0:
        return pdfs[:limit]
    return pdfs


def default_crop_out_dir(work_dir: str | Path) -> Path:
    return Path(work_dir) / "crop"


def plan_crop_one(
    source_pdf: str | Path,
    batch: str,
    out_dir: str | Path,
    layout: CropLayout = REGION_PIPELINE_LAYOUT,
    page_index: int = 0,
) -> CropSourcePlan:
    """Plan code/name/correction crops for one explicit PDF."""

    source_path = Path(source_pdf)
    resolved_out_dir = Path(out_dir)
    regions: list[CropRegionPlan] = []
    record_warnings: list[str] = []
    page_rect: PdfRect | None = None

    for region in layout.regions:
        output_pdf = resolved_out_dir / f"{source_path.stem}__{region.name}.pdf"
        pdf_plan = plan_pdf_crop(source_path, region.rect, page_index=page_index)
        if page_rect is None:
            page_rect = pdf_plan.page_rect
        warnings = list(pdf_plan.warnings)
        if pdf_plan.clip_rect.is_empty:
            record_warnings.append(f"{region.name}_empty")
        regions.append(
            CropRegionPlan(
                region=region.name,
                requested_rect=region.rect,
                clip_rect=pdf_plan.clip_rect,
                output_pdf=output_pdf.as_posix(),
                warnings=warnings,
            )
        )

    if page_rect is None:
        raise ValueError("No crop regions configured.")

    return CropSourcePlan(
        source_pdf=source_path.as_posix(),
        source_stem=source_path.stem,
        page_index=page_index,
        page_rect=page_rect,
        regions=regions,
        warnings=record_warnings,
    )


def build_crop_manifest(
    batch: str,
    source_pdfs: Iterable[str | Path],
    scan_dir: str | Path,
    out_dir: str | Path,
    layout: CropLayout = REGION_PIPELINE_LAYOUT,
    page_index: int = 0,
    write_crops: bool = False,
) -> CropBatchManifest:
    """Plan a batch and optionally write crop PDFs to the explicit out_dir."""

    resolved_out_dir = Path(out_dir)
    records = [
        plan_crop_one(source_pdf, batch=batch, out_dir=resolved_out_dir, layout=layout, page_index=page_index)
        for source_pdf in source_pdfs
    ]

    if write_crops:
        for record in records:
            for region in record.regions:
                save_pdf_crop(
                    record.source_pdf,
                    region.output_pdf,
                    region.clip_rect,
                    page_index=record.page_index,
                    overwrite=True,
                    create_parents=True,
                )

    return CropBatchManifest(
        batch=batch,
        scan_dir=Path(scan_dir).as_posix(),
        out_dir=resolved_out_dir.as_posix(),
        layout=layout.name,
        write_crops=write_crops,
        records=records,
    )


def write_crop_manifest(manifest: CropBatchManifest, manifest_path: str | Path) -> None:
    """Write crop manifest JSON to an explicit path."""

    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
