from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.crop import PdfRect, plan_pdf_crop, read_pdf_page_rect, save_pdf_crop


def _write_tiny_pdf(path: Path, width: float = 200, height: float = 100) -> None:
    with fitz.open() as doc:
        page = doc.new_page(width=width, height=height)
        page.insert_text((20, 40), "fixture")
        doc.save(path)


class PdfCropAdapterTests(unittest.TestCase):
    def test_read_pdf_page_rect_from_temp_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "fixture.pdf"
            _write_tiny_pdf(pdf_path, width=200, height=100)

            rect = read_pdf_page_rect(pdf_path)

            self.assertEqual(rect.to_list(), [0, 0, 200, 100])

    def test_plan_pdf_crop_is_dry_run_and_clips_to_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "fixture.pdf"
            out_path = root / "out.pdf"
            _write_tiny_pdf(pdf_path, width=200, height=100)

            plan = plan_pdf_crop(pdf_path, PdfRect(50, 20, 250, 150), output_pdf=out_path)
            payload = plan.to_json()

            self.assertEqual(payload["page_rect"], [0, 0, 200, 100])
            self.assertEqual(payload["requested_rect"], [50, 20, 250, 150])
            self.assertEqual(payload["clip_rect"], [50, 20, 200, 100])
            self.assertTrue(payload["would_write"])
            self.assertEqual(payload["warnings"], ["clip_rect_clipped_to_page"])
            self.assertFalse(out_path.exists())

    def test_save_pdf_crop_writes_only_explicit_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "fixture.pdf"
            out_path = root / "cropped.pdf"
            _write_tiny_pdf(pdf_path, width=200, height=100)

            plan = save_pdf_crop(pdf_path, out_path, PdfRect(50, 20, 150, 90))

            self.assertTrue(out_path.exists())
            self.assertEqual(plan.clip_rect.size_list(), [100, 70])
            self.assertEqual(read_pdf_page_rect(out_path).to_list(), [0, 0, 100, 70])

    def test_save_pdf_crop_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "fixture.pdf"
            out_path = root / "cropped.pdf"
            _write_tiny_pdf(pdf_path)
            _write_tiny_pdf(out_path)

            with self.assertRaises(FileExistsError):
                save_pdf_crop(pdf_path, out_path, PdfRect(10, 10, 50, 50))


if __name__ == "__main__":
    unittest.main()
