from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.crop import REGION_PIPELINE_LAYOUT, PdfRect, build_crop_precheck_manifest, safe_filename, unique_output_paths
from lieshi_ocr.crop.records import CropManifest, CropRecord, RegionRecord


class CropModuleTests(unittest.TestCase):
    def test_pdf_rect_clip_and_scaled_bounds(self) -> None:
        rect = PdfRect(10, 20, 110, 220)
        clipped = rect.clip_to(PdfRect(0, 30, 80, 500))

        self.assertEqual(clipped.to_list(), [10, 30, 80, 220])
        self.assertEqual(clipped.size_list(), [70, 190])
        self.assertEqual(PdfRect(1.2, 2.4, 3.6, 4.8).scaled_bounds(2), (2, 5, 7, 10))

    def test_px_bounds_to_pdf_rect(self) -> None:
        candidate = PdfRect(100, 200, 300, 600)

        detected = candidate.px_bounds_to_pdf_rect((10, 20, 90, 180), (100, 200))

        self.assertEqual(detected.to_list(), [120, 240, 280, 560])

    def test_safe_filename_matches_legacy_intent(self) -> None:
        self.assertEqual(safe_filename(" 晋祁县000001 / 张 三 ： test "), "晋祁县000001_张三_test")
        self.assertEqual(safe_filename(""), "unknown")

    def test_unique_output_paths_avoids_existing_pdf_or_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cut_dir = root / "cut"
            extracted_dir = root / "extracted"
            cut_dir.mkdir()
            extracted_dir.mkdir()
            (cut_dir / "晋祁县000001_测试.pdf").write_text("", encoding="utf-8")
            (extracted_dir / "晋祁县000001_测试_001.json").write_text("", encoding="utf-8")

            cut_pdf, json_path, stem = unique_output_paths(cut_dir, extracted_dir, "晋祁县000001_测试")

            self.assertEqual(stem, "晋祁县000001_测试_002")
            self.assertEqual(cut_pdf.name, "晋祁县000001_测试_002.pdf")
            self.assertEqual(json_path.name, "晋祁县000001_测试_002.json")

    def test_layout_regions_are_manifest_ready(self) -> None:
        regions = REGION_PIPELINE_LAYOUT.as_manifest_regions()

        self.assertEqual(regions["code"], [365, 35, 560, 105])
        self.assertEqual(REGION_PIPELINE_LAYOUT.region("correction").rect.to_list(), [35, 280, 560, 545])

    def test_crop_manifest_json(self) -> None:
        manifest = CropManifest(
            batch="20260626",
            scan_dir="data/scan/20260626",
            out_dir="data/work/20260626/cut_parts",
            layout="review_form_split",
            regions={"code": PdfRect(1, 2, 3, 4)},
            records=[
                CropRecord(
                    source_pdf="a.pdf",
                    source_stem="a",
                    regions=[RegionRecord(region="code", pdf="a__code.pdf", clip_rect=PdfRect(1, 2, 3, 4))],
                )
            ],
        )

        payload = manifest.to_json()

        self.assertEqual(payload["regions"]["code"], [1, 2, 3, 4])
        self.assertEqual(payload["records"][0]["regions"][0]["size"], [2, 2])

    def test_crop_precheck_manifest_is_read_only_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "scan" / "example.pdf"

            manifest = build_crop_precheck_manifest("20260626", [source])
            payload = manifest.to_json()

            self.assertEqual(payload["batch"], "20260626")
            self.assertEqual(payload["scan_dir"], "data/scan/20260626")
            self.assertEqual(payload["out_dir"], "data/work/20260626/crop_precheck")
            self.assertEqual(payload["layout"], "review_form_split")
            self.assertEqual(payload["regions"]["code"], [395, 45, 545, 90])
            self.assertEqual(payload["records"][0]["source_stem"], "example")
            self.assertEqual(payload["records"][0]["regions"][0]["pdf"], "data/work/20260626/crop_precheck/example__code.pdf")
            self.assertFalse(source.exists())
            self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
