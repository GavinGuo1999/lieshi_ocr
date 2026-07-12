from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import fitz
from PIL import Image

from lieshi_ocr.ocr.rapidocr_engine import _normalize_rapidocr_output, _rapidocr_input


class RapidOcrEngineTests(unittest.TestCase):
    def test_normalizes_current_dataclass_output(self) -> None:
        output = SimpleNamespace(txts=(" QX-0001 ", "张某"), scores=(0.98, 0.92))

        texts, scores = _normalize_rapidocr_output(output)

        self.assertEqual(texts, ["QX-0001", "张某"])
        self.assertEqual(scores, [0.98, 0.92])

    def test_normalizes_legacy_tuple_output(self) -> None:
        rows = [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], " QX-0001 ", 0.96],
            [[[0, 0], [1, 0], [1, 1], [0, 1]], "张某", 0.90],
        ]

        texts, scores = _normalize_rapidocr_output((rows, [0.01, 0.02, 0.03]))

        self.assertEqual(texts, ["QX-0001", "张某"])
        self.assertEqual(scores, [0.96, 0.90])

    def test_rapidocr_input_renders_pdf_first_page_to_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "crop.pdf"
            document = fitz.open()
            page = document.new_page(width=120, height=60)
            page.insert_text((10, 30), "QX-0001")
            document.save(pdf_path)
            document.close()

            image = _rapidocr_input(pdf_path)

            self.assertIsInstance(image, Image.Image)
            self.assertGreater(image.width, 0)
            self.assertGreater(image.height, 0)

    def test_rapidocr_input_keeps_non_pdf_as_path_string(self) -> None:
        self.assertEqual(_rapidocr_input("crop.png"), "crop.png")


if __name__ == "__main__":
    unittest.main()
