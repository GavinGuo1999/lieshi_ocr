from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.config import ENV_PROJECT_ROOT
from lieshi_ocr.paths import ProjectPaths, find_project_root


class PathConventionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_root = os.environ.pop(ENV_PROJECT_ROOT, None)

    def tearDown(self) -> None:
        if self.previous_root is not None:
            os.environ[ENV_PROJECT_ROOT] = self.previous_root
        else:
            os.environ.pop(ENV_PROJECT_ROOT, None)

    def test_find_project_root_from_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# marker\n", encoding="utf-8")
            child = root / "nested" / "dir"
            child.mkdir(parents=True)

            self.assertEqual(find_project_root(child), root.resolve())

    def test_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[ENV_PROJECT_ROOT] = tmp

            self.assertEqual(find_project_root(), Path(tmp).resolve())

    def test_batch_paths_follow_convention_without_creating_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()

            paths = ProjectPaths.discover(root)
            batch = paths.batch("20260626")

            self.assertEqual(batch.scan, root.resolve() / "data" / "scan" / "20260626")
            self.assertEqual(batch.work, root.resolve() / "data" / "work" / "20260626")
            self.assertEqual(batch.output, root.resolve() / "data" / "output" / "20260626")
            self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
