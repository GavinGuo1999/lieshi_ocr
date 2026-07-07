from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.crop import (
    REGION_PIPELINE_LAYOUT,
    PdfRect,
    PixelBounds,
    bounds_to_pdf_rect,
    correction_cell_bounds_from_lines,
    group_centers,
    group_positions,
    legacy_region_stem,
    name_cell_bounds_from_lines,
    region_output_names,
)


class CropGeometryRuleTests(unittest.TestCase):
    def test_group_positions_and_centers_are_pure(self) -> None:
        groups = group_positions([10, 11, 12, 30, 35, 36], max_gap=2)

        self.assertEqual(groups, ((10, 12), (30, 30), (35, 36)))
        self.assertEqual(group_centers(groups), (11, 30, 35))

    def test_name_cell_bounds_from_simulated_lines(self) -> None:
        detected = name_cell_bounds_from_lines(
            image_size=(875, 230),
            vertical_centers=(0, 310, 690),
            horizontal_centers=(40, 195),
            scale=5.0,
        )

        self.assertEqual(detected.bounds, PixelBounds(320, 46, 680, 189))
        self.assertEqual(detected.debug["method"], "line")
        self.assertEqual(detected.debug["h_method"], "line_pair")

    def test_name_cell_bounds_uses_single_top_line_fallback(self) -> None:
        detected = name_cell_bounds_from_lines(
            image_size=(875, 230),
            vertical_centers=(310, 690),
            horizontal_centers=(40,),
            scale=5.0,
        )

        self.assertEqual(detected.bounds.to_tuple(), (320, 46, 680, 153))
        self.assertEqual(detected.debug["method"], "line_partial")
        self.assertEqual(detected.debug["h_method"], "single_top_line")

    def test_correction_cell_bounds_from_simulated_lines(self) -> None:
        detected = correction_cell_bounds_from_lines(
            image_size=(1575, 795),
            horizontal_centers=(30, 170, 720),
            vertical_centers=(0, 110, 1500),
            scale=3.0,
        )

        self.assertEqual(detected.bounds, PixelBounds(116, 172, 1494, 714))
        self.assertFalse(detected.debug["used_fallback_bottom"])
        self.assertEqual(detected.debug["v_method"], "line")

    def test_correction_cell_bounds_rejects_extreme_aspect_ratio(self) -> None:
        detected = correction_cell_bounds_from_lines(
            image_size=(1575, 795),
            horizontal_centers=(30, 170, 250),
            vertical_centers=(0, 110, 1500),
            scale=3.0,
        )

        self.assertEqual(detected.bounds.top, 256)
        self.assertEqual(detected.bounds.bottom, 741)
        self.assertTrue(detected.debug["used_fallback_bottom"])

    def test_pixel_bounds_map_back_to_pdf_rect(self) -> None:
        rect = bounds_to_pdf_rect(
            PixelBounds(100, 50, 500, 350),
            image_size=(1000, 500),
            candidate_rect=PdfRect(35, 280, 560, 545),
        )

        self.assertEqual(rect.to_list(), [87.5, 306.5, 297.5, 465.5])

    def test_layout_regions_clip_to_page_rect(self) -> None:
        regions = REGION_PIPELINE_LAYOUT.clipped_regions(PdfRect(0, 0, 500, 500))

        self.assertEqual(regions["code"].to_list(), [365, 35, 500, 105])
        self.assertEqual(regions["correction"].to_list(), [35, 280, 500, 500])

    def test_legacy_region_output_names_do_not_touch_disk(self) -> None:
        stem = legacy_region_stem("晋祁县000001", "张 三", "scan-001")
        names = region_output_names(stem)

        self.assertEqual(stem, "晋祁县000001_张三__scan-001")
        self.assertEqual(
            names,
            {
                "code": "晋祁县000001_张三__scan-001__code.pdf",
                "name": "晋祁县000001_张三__scan-001__name.pdf",
                "correction": "晋祁县000001_张三__scan-001__correction.pdf",
            },
        )


if __name__ == "__main__":
    unittest.main()
