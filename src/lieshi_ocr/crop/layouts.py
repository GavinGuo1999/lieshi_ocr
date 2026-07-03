"""Stable crop-layout definitions for the current review-form scans."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import PdfRect


@dataclass(frozen=True)
class RegionSpec:
    name: str
    rect: PdfRect
    description: str = ""


@dataclass(frozen=True)
class CropLayout:
    name: str
    regions: tuple[RegionSpec, ...]
    coordinate_space: str = "original scan page PDF points"

    def region(self, name: str) -> RegionSpec:
        for region in self.regions:
            if region.name == name:
                return region
        raise KeyError(f"Unknown crop region: {name}")

    def as_manifest_regions(self) -> dict[str, list[float]]:
        return {region.name: region.rect.to_list() for region in self.regions}


USEFUL_AREA_LAYOUT = CropLayout(
    name="useful_area",
    regions=(
        RegionSpec("useful_area", PdfRect(35, 45, 545, 520), "Header, table, correction content and reason."),
    ),
)

REVIEW_FORM_SPLIT_LAYOUT = CropLayout(
    name="review_form_split",
    regions=(
        RegionSpec("code", PdfRect(395, 45, 545, 90), "Top-right form code area."),
        RegionSpec("table", PdfRect(35, 45, 545, 325), "Original information table."),
        RegionSpec("correction", PdfRect(70, 305, 545, 520), "Correction body without left vertical label."),
    ),
)

REGION_PIPELINE_LAYOUT = CropLayout(
    name="region_pipeline",
    regions=(
        RegionSpec("code", PdfRect(365, 35, 560, 105), "Candidate code OCR region."),
        RegionSpec("name", PdfRect(55, 112, 230, 158), "Candidate name table cell."),
        RegionSpec("correction", PdfRect(35, 280, 560, 545), "Candidate correction text area."),
    ),
)
