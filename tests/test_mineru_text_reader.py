from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.ocr.mineru_text_reader import read_mineru_text


class MineruTextReaderTests(unittest.TestCase):
    def test_top_level_exact_match_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.md").write_text("top-level", encoding="utf-8")
            nested = root / "sample" / "ocr"
            nested.mkdir(parents=True)
            (nested / "sample.md").write_text("nested", encoding="utf-8")

            result = read_mineru_text(root, source_stem="sample", region="correction")

            self.assertEqual(result.text, "top-level")
            self.assertEqual(result.warnings, ())

    def test_nested_ocr_markdown_can_be_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "sample" / "ocr"
            nested.mkdir(parents=True)
            (nested / "sample.md").write_text("nested text", encoding="utf-8")

            result = read_mineru_text(root, source_stem="sample", region="correction")

            self.assertEqual(result.text, "nested text")
            self.assertEqual(result.warnings, ())

    def test_parent_directory_can_match_source_stem_when_file_name_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "prefix_sample_suffix" / "ocr"
            nested.mkdir(parents=True)
            (nested / "content.md").write_text("body text", encoding="utf-8")

            result = read_mineru_text(root, source_stem="sample", region="correction")

            self.assertEqual(result.text, "body text")
            self.assertEqual(result.warnings, ())

    def test_multiple_recursive_candidates_emit_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "sample_a" / "ocr"
            second = root / "sample_b" / "ocr"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "one.md").write_text("one", encoding="utf-8")
            (second / "two.md").write_text("two", encoding="utf-8")

            result = read_mineru_text(root, source_stem="sample", region="correction")

            self.assertIn(result.text, {"one", "two"})
            self.assertEqual(result.warnings, ("mineru_text_multiple_candidates",))

    def test_missing_text_warning_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = read_mineru_text(tmp, source_stem="missing", region="correction")

            self.assertEqual(result.text, "")
            self.assertEqual(result.warnings, ("mineru_text_not_found",))


if __name__ == "__main__":
    unittest.main()
