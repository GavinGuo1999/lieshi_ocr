"""Manifest record models for crop outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .geometry import PdfRect

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class RegionRecord:
    region: str
    pdf: str
    clip_rect: PdfRect
    preview_png: str = ""

    def to_json(self) -> JsonDict:
        return {
            "region": self.region,
            "pdf": self.pdf,
            "preview_png": self.preview_png,
            "clip_rect": self.clip_rect.to_list(),
            "size": self.clip_rect.size_list(),
        }


@dataclass(frozen=True)
class CropRecord:
    source_pdf: str
    source_stem: str
    regions: list[RegionRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "source_pdf": self.source_pdf,
            "source_stem": self.source_stem,
            "regions": [region.to_json() for region in self.regions],
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class CropManifest:
    batch: str
    scan_dir: str
    out_dir: str
    layout: str
    regions: dict[str, PdfRect]
    records: list[CropRecord] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "scan_dir": self.scan_dir,
            "out_dir": self.out_dir,
            "layout": self.layout,
            "regions": {name: rect.to_list() for name, rect in self.regions.items()},
            "records": [record.to_json() for record in self.records],
        }
