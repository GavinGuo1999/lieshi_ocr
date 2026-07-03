"""Naming helpers for crop output files."""

from __future__ import annotations

from pathlib import Path
import re


def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|：？“”《》|]', "_", value or "")
    value = re.sub(r"\s+", "", value).strip("._ ")
    return value or "unknown"


def unique_output_paths(cut_dir: Path, extracted_dir: Path, base: str) -> tuple[Path, Path, str]:
    """Return non-conflicting PDF/JSON paths for a base output stem."""

    safe_base = safe_filename(base)
    for index in range(10_000):
        candidate = safe_base if index == 0 else f"{safe_base}_{index:03d}"
        cut_pdf = cut_dir / f"{candidate}.pdf"
        json_path = extracted_dir / f"{candidate}.json"
        if not cut_pdf.exists() and not json_path.exists():
            return cut_pdf, json_path, candidate
    raise RuntimeError(f"Could not find available output name for {safe_base}")
