from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.crop.batch import build_crop_manifest
from lieshi_ocr.crop.layouts import REGION_PIPELINE_LAYOUT
from lieshi_ocr.crop.name_cell_detector import detect_name_cell, detect_table_line_centers


def _write_name_table_pdf(path: Path, include_lines: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as document:
        page = document.new_page(width=600, height=700)
        if include_lines:
            for x in (57, 117, 193):
                page.draw_line(fitz.Point(x, 112), fitz.Point(x, 158), color=(0, 0, 0), width=0.8)
            for y in (120, 151):
                page.draw_line(fitz.Point(55, y), fitz.Point(230, y), color=(0, 0, 0), width=0.8)
            page.insert_text((126, 140), "Test", fontsize=9)
        document.save(path)


class NameCellDetectionTests(unittest.TestCase):
    def test_detects_centers_from_synthetic_table_image(self) -> None:
        image = np.full((230, 875, 3), 255, dtype=np.uint8)
        for x in (10, 310, 690):
            cv2.line(image, (x, 0), (x, 229), (0, 0, 0), 3)
        for y in (40, 195):
            cv2.line(image, (0, y), (874, y), (0, 0, 0), 3)

        vertical, horizontal = detect_table_line_centers(image)

        self.assertEqual(len(vertical), 3)
        self.assertEqual(len(horizontal), 2)
        self.assertTrue(all(abs(actual - expected) <= 2 for actual, expected in zip(vertical, (10, 310, 690))))
        self.assertTrue(all(abs(actual - expected) <= 2 for actual, expected in zip(horizontal, (40, 195))))

    def test_pdf_detection_returns_narrower_name_cell_and_debug_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "sample.pdf"
            debug_path = root / "debug" / "name.png"
            candidate = REGION_PIPELINE_LAYOUT.region("name").rect
            _write_name_table_pdf(pdf_path)

            detection = detect_name_cell(pdf_path, candidate, debug_output=debug_path)

            self.assertEqual(detection.crop_method, "name_cell_lines")
            self.assertEqual(detection.warnings, ())
            self.assertGreaterEqual(len(detection.vertical_centers), 3)
            self.assertGreaterEqual(len(detection.horizontal_centers), 1)
            self.assertLess(detection.final_rect.width, candidate.width)
            self.assertLess(detection.final_rect.height, candidate.height)
            self.assertTrue(debug_path.exists())

    def test_detection_failure_uses_safe_inner_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "blank.pdf"
            candidate = REGION_PIPELINE_LAYOUT.region("name").rect
            _write_name_table_pdf(pdf_path, include_lines=False)

            detection = detect_name_cell(pdf_path, candidate)

            self.assertEqual(detection.crop_method, "name_cell_fallback")
            self.assertEqual(detection.warnings, ("name_cell_detection_fallback",))
            self.assertLess(detection.final_rect.width, candidate.width)
            self.assertLess(detection.final_rect.height, candidate.height)

    def test_batch_refines_only_name_region_and_records_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / "scan" / "sample.pdf"
            out_dir = root / "work" / "crop"
            _write_name_table_pdf(source_pdf)

            manifest = build_crop_manifest(
                batch="20260626",
                source_pdfs=[source_pdf],
                scan_dir=source_pdf.parent,
                out_dir=out_dir,
                write_crops=True,
                refine_name_cell=True,
                write_debug=True,
            )
            payload = manifest.to_json()
            regions = {region["region"]: region for region in payload["records"][0]["regions"]}

            self.assertEqual(regions["name"]["crop_method"], "name_cell_lines")
            self.assertLess(regions["name"]["size"][0], REGION_PIPELINE_LAYOUT.region("name").rect.width)
            self.assertEqual(regions["code"]["requested_rect"], REGION_PIPELINE_LAYOUT.region("code").rect.to_list())
            self.assertEqual(
                regions["correction"]["requested_rect"],
                REGION_PIPELINE_LAYOUT.region("correction").rect.to_list(),
            )
            self.assertTrue((out_dir / "sample__name.pdf").exists())
            self.assertTrue((out_dir.parent / "crop_debug" / "sample__name_detection.png").exists())

    def test_batch_keeps_legacy_name_rect_when_refinement_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / "scan" / "sample.pdf"
            out_dir = root / "work" / "crop"
            _write_name_table_pdf(source_pdf)

            manifest = build_crop_manifest(
                batch="20260626",
                source_pdfs=[source_pdf],
                scan_dir=source_pdf.parent,
                out_dir=out_dir,
            )
            name_region = next(
                region for region in manifest.to_json()["records"][0]["regions"] if region["region"] == "name"
            )

            self.assertEqual(name_region["requested_rect"], REGION_PIPELINE_LAYOUT.region("name").rect.to_list())
            self.assertNotIn("crop_method", name_region)
            self.assertFalse(out_dir.exists())

    def test_write_debug_requires_refinement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / "scan" / "sample.pdf"
            _write_name_table_pdf(source_pdf)

            with self.assertRaisesRegex(ValueError, "write_debug requires refine_name_cell"):
                build_crop_manifest(
                    batch="20260626",
                    source_pdfs=[source_pdf],
                    scan_dir=source_pdf.parent,
                    out_dir=root / "work" / "crop",
                    write_debug=True,
                )

    def test_batch_records_safe_fallback_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / "scan" / "blank.pdf"
            out_dir = root / "work" / "crop"
            _write_name_table_pdf(source_pdf, include_lines=False)

            manifest = build_crop_manifest(
                batch="20260626",
                source_pdfs=[source_pdf],
                scan_dir=source_pdf.parent,
                out_dir=out_dir,
                refine_name_cell=True,
            )
            name_region = next(
                region for region in manifest.to_json()["records"][0]["regions"] if region["region"] == "name"
            )

            self.assertEqual(name_region["crop_method"], "name_cell_fallback")
            self.assertIn("name_cell_detection_fallback", name_region["warnings"])
            self.assertLess(name_region["size"][0], REGION_PIPELINE_LAYOUT.region("name").rect.width)

    def test_cli_refines_name_cell_only_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            scan_dir = root / "data" / "scan" / "20260626" / "scan"
            source_pdf = scan_dir / "sample.pdf"
            _write_name_table_pdf(source_pdf)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "crop-batch",
                    "--batch",
                    "20260626",
                    "--scan-dir",
                    str(scan_dir),
                    "--limit",
                    "1",
                    "--write-crops",
                    "--refine-name-cell",
                    "--write-debug",
                    "--root",
                    str(root),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                text=True,
                capture_output=True,
                check=True,
            )
            manifest_path = root / "data" / "work" / "20260626" / "crop" / "crop_manifest.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            name_region = next(region for region in payload["records"][0]["regions"] if region["region"] == "name")

            self.assertIn('"refine_name_cell": true', result.stdout)
            self.assertTrue(payload["refine_name_cell"])
            self.assertTrue(payload["write_debug"])
            self.assertEqual(name_region["crop_method"], "name_cell_lines")


if __name__ == "__main__":
    unittest.main()
