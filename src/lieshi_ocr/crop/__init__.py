"""Crop planning helpers for review-form PDFs."""

from .geometry import PdfRect
from .layouts import REGION_PIPELINE_LAYOUT, REVIEW_FORM_SPLIT_LAYOUT, USEFUL_AREA_LAYOUT
from .naming import safe_filename, unique_output_paths
from .records import CropManifest, CropRecord, RegionRecord

__all__ = [
    "CropManifest",
    "CropRecord",
    "PdfRect",
    "REGION_PIPELINE_LAYOUT",
    "REVIEW_FORM_SPLIT_LAYOUT",
    "RegionRecord",
    "USEFUL_AREA_LAYOUT",
    "safe_filename",
    "unique_output_paths",
]
