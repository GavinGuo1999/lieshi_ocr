from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.crop.batch import build_crop_manifest, discover_batch_pdfs, write_crop_manifest


def _write_tiny_pdf(path: Path, width: float = 600, height: float = 700) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as doc:
        page = doc.new_page(width=width, height=height)
        page.insert_text((40, 60), path.stem)
        doc.save(path)


class CropBatchPipelineTests(unittest.TestCase):
    def test_discover_batch_pdfs_sorted_and_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scan = Path(tmp) / "data" / "scan" / "20260626"
            _write_tiny_pdf(scan / "b.pdf")
            _write_tiny_pdf(scan / "a.pdf")
            (scan / "ignored.txt").write_text("x", encoding="utf-8")

            pdfs = discover_batch_pdfs(scan, limit=1)

            self.assertEqual([path.name for path in pdfs], ["a.pdf"])

    def test_build_crop_manifest_dry_run_does_not_write_crops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scan = root / "data" / "scan" / "20260626"
            out_dir = root / "data" / "work" / "20260626" / "crop"
            source_pdf = scan / "sample.pdf"
            _write_tiny_pdf(source_pdf)

            manifest = build_crop_manifest(
                batch="20260626",
                source_pdfs=[source_pdf],
                scan_dir=scan,
                out_dir=out_dir,
                write_crops=False,
            )
            payload = manifest.to_json()

            self.assertEqual(payload["total"], 1)
            self.assertFalse(payload["write_crops"])
            self.assertEqual([region["region"] for region in payload["records"][0]["regions"]], ["code", "name", "correction"])
            self.assertFalse(out_dir.exists())

    def test_write_crop_manifest_and_crops_use_explicit_temp_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scan = root / "data" / "scan" / "20260626"
            out_dir = root / "data" / "work" / "20260626" / "crop"
            source_pdf = scan / "sample.pdf"
            manifest_path = out_dir / "crop_manifest.json"
            _write_tiny_pdf(source_pdf)

            manifest = build_crop_manifest(
                batch="20260626",
                source_pdfs=[source_pdf],
                scan_dir=scan,
                out_dir=out_dir,
                write_crops=True,
            )
            write_crop_manifest(manifest, manifest_path)
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(manifest_path.exists())
            self.assertTrue((out_dir / "sample__code.pdf").exists())
            self.assertTrue((out_dir / "sample__name.pdf").exists())
            self.assertTrue((out_dir / "sample__correction.pdf").exists())
            self.assertTrue(payload["write_crops"])

    def test_cli_crop_batch_dry_run_writes_manifest_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            scan = root / "data" / "scan" / "20260626"
            out_dir = root / "data" / "work" / "20260626" / "crop"
            _write_tiny_pdf(scan / "sample.pdf")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "crop-batch",
                    "--batch",
                    "20260626",
                    "--dry-run",
                    "--root",
                    str(root),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn('"total": 1', result.stdout)
            self.assertTrue((out_dir / "crop_manifest.json").exists())
            self.assertFalse((out_dir / "sample__code.pdf").exists())

    def test_cli_crop_one_dry_run_uses_explicit_pdf_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            explicit_pdf = root / "input" / "one.pdf"
            out_dir = root / "out"
            _write_tiny_pdf(explicit_pdf)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "crop-one",
                    "--pdf",
                    str(explicit_pdf),
                    "--batch",
                    "20260626",
                    "--root",
                    str(root),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn('"total": 1', result.stdout)
            self.assertIn((root / "input").as_posix(), result.stdout)
            self.assertTrue((out_dir / "crop_manifest.json").exists())
            self.assertFalse((out_dir / "one__code.pdf").exists())


if __name__ == "__main__":
    unittest.main()
