from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class CliImportTests(unittest.TestCase):
    def test_cli_main_is_importable(self) -> None:
        from lieshi_ocr.cli import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
