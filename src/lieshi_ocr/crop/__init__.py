"""Crop planning helpers for review-form PDFs."""

from .geometry import PdfRect
from .layouts import REGION_PIPELINE_LAYOUT, REVIEW_FORM_SPLIT_LAYOUT, USEFUL_AREA_LAYOUT
from .layouts import CropLayout, RegionSpec
from .line_rules import (
    CellBounds,
    PixelBounds,
    bounds_to_pdf_rect,
    correction_cell_bounds_from_lines,
    group_centers,
    group_positions,
    legacy_region_stem,
    name_cell_bounds_from_lines,
    region_output_names,
)
from .naming import safe_filename, unique_output_paths
from .pdf_adapter import PdfCropPlan, plan_pdf_crop, read_pdf_page_rect, save_pdf_crop
from .precheck import build_crop_precheck_manifest
from .records import CropManifest, CropRecord, RegionRecord

__all__ = [
    "CellBounds",
    "CropManifest",
    "CropLayout",
    "CropRecord",
    "PdfRect",
    "PdfCropPlan",
    "PixelBounds",
    "REGION_PIPELINE_LAYOUT",
    "REVIEW_FORM_SPLIT_LAYOUT",
    "RegionRecord",
    "RegionSpec",
    "USEFUL_AREA_LAYOUT",
    "bounds_to_pdf_rect",
    "build_crop_precheck_manifest",
    "correction_cell_bounds_from_lines",
    "group_centers",
    "group_positions",
    "legacy_region_stem",
    "name_cell_bounds_from_lines",
    "plan_pdf_crop",
    "read_pdf_page_rect",
    "region_output_names",
    "safe_filename",
    "save_pdf_crop",
    "unique_output_paths",
]
