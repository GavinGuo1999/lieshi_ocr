from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.ocr import FakeOcrEngine, NoOcrEngine
from lieshi_ocr.pipeline.extract_text import extract_text_manifest, write_text_manifest


def _write_crop_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch": "20260626",
        "scan_dir": "data/scan/20260626",
        "out_dir": "data/work/20260626/crop",
        "layout": "region_pipeline",
        "write_crops": True,
        "total": 1,
        "records": [
            {
                "source_pdf": "data/scan/20260626/sample.pdf",
                "source_stem": "sample",
                "page_index": 0,
                "page_rect": [0, 0, 600, 700],
                "regions": [
                    {"region": "code", "output_pdf": "data/work/20260626/crop/sample__code.pdf", "warnings": []},
                    {"region": "name", "output_pdf": "data/work/20260626/crop/sample__name.pdf", "warnings": []},
                    {"region": "correction", "output_pdf": "data/work/20260626/crop/sample__correction.pdf", "warnings": []},
                ],
                "warnings": [],
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ExtractTextPipelineTests(unittest.TestCase):
    def test_extract_text_manifest_uses_fake_ocr_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop_manifest = root / "crop_manifest.json"
            _write_crop_manifest(crop_manifest)
            engine = FakeOcrEngine(
                {
                    "sample__code.pdf": "晋祁县000001",
                    "sample__name.pdf": "张三",
                    "sample__correction.pdf": "张三烈士事迹文本",
                }
            )

            manifest = extract_text_manifest(crop_manifest, root / "text", ocr_engine=engine)
            payload = manifest.to_json()

            self.assertEqual(payload["batch"], "20260626")
            self.assertEqual(payload["total"], 3)
            self.assertEqual(payload["records"][0]["engine"], "fake")
            self.assertEqual(payload["records"][0]["text"], "晋祁县000001")
            self.assertEqual(payload["records"][0]["confidence"], 1.0)

    def test_mineru_text_dir_can_supply_correction_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop_manifest = root / "crop_manifest.json"
            mineru_dir = root / "mineru"
            _write_crop_manifest(crop_manifest)
            mineru_dir.mkdir()
            (mineru_dir / "sample__correction.md").write_text("MinerU 修正文段", encoding="utf-8")

            manifest = extract_text_manifest(
                crop_manifest,
                root / "text",
                ocr_engine=FakeOcrEngine({"sample__code.pdf": "code", "sample__name.pdf": "name"}),
                mineru_text_dir=mineru_dir,
            )
            records = {record.region: record for record in manifest.records}

            self.assertEqual(records["correction"].engine, "mineru_text")
            self.assertEqual(records["correction"].text, "MinerU 修正文段")
            self.assertEqual(records["correction"].confidence, 1.0)

    def test_code_name_engine_can_run_without_touching_correction_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop_manifest = root / "crop_manifest.json"
            mineru_dir = root / "mineru"
            _write_crop_manifest(crop_manifest)
            mineru_dir.mkdir()
            (mineru_dir / "sample__correction.md").write_text("MinerU correction text", encoding="utf-8")

            manifest = extract_text_manifest(
                crop_manifest,
                root / "text",
                code_name_ocr_engine=FakeOcrEngine(
                    {
                        "sample__code.pdf": "QX-0001",
                        "sample__name.pdf": "Test Name",
                    }
                ),
                correction_ocr_engine=NoOcrEngine(),
                mineru_text_dir=mineru_dir,
                use_mineru_correction=True,
            )
            records = {record.region: record for record in manifest.records}

            self.assertEqual(records["code"].engine, "fake")
            self.assertEqual(records["code"].text, "QX-0001")
            self.assertEqual(records["name"].engine, "fake")
            self.assertEqual(records["name"].text, "Test Name")
            self.assertEqual(records["correction"].engine, "mineru_text")
            self.assertEqual(records["correction"].text, "MinerU correction text")
            self.assertEqual(records["correction"].warnings, [])

    def test_write_text_manifest_to_explicit_temp_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop_manifest = root / "crop_manifest.json"
            out_path = root / "text" / "text_manifest.json"
            _write_crop_manifest(crop_manifest)

            manifest = extract_text_manifest(crop_manifest, root / "text", ocr_engine=FakeOcrEngine())
            write_text_manifest(manifest, out_path)
            payload = json.loads(out_path.read_text(encoding="utf-8"))

            self.assertTrue(out_path.exists())
            self.assertEqual(payload["total"], 3)
            self.assertEqual(payload["records"][0]["warnings"], ["fake_ocr_text_missing"])

    def test_cli_extract_text_reports_mixed_engine_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            crop_manifest = root / "data" / "work" / "20260626" / "crop" / "crop_manifest.json"
            text_manifest = root / "data" / "work" / "20260626" / "text" / "text_manifest.json"
            mineru_dir = root / "mineru"
            _write_crop_manifest(crop_manifest)
            mineru_dir.mkdir()
            (mineru_dir / "sample__correction.md").write_text("MinerU correction text", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "extract-text",
                    "--batch",
                    "20260626",
                    "--root",
                    str(root),
                    "--mineru-text-dir",
                    str(mineru_dir),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(text_manifest.read_text(encoding="utf-8"))
            records = {record["region"]: record for record in payload["records"]}

            self.assertIn('"code_name_engine": "none"', result.stdout)
            self.assertIn('"correction_engine": "mineru"', result.stdout)
            self.assertEqual(records["code"]["engine"], "none")
            self.assertEqual(records["correction"]["engine"], "mineru_text")

    def test_cli_extract_text_defaults_to_no_real_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            crop_manifest = root / "data" / "work" / "20260626" / "crop" / "crop_manifest.json"
            text_manifest = root / "data" / "work" / "20260626" / "text" / "text_manifest.json"
            _write_crop_manifest(crop_manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "extract-text",
                    "--batch",
                    "20260626",
                    "--root",
                    str(root),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(text_manifest.read_text(encoding="utf-8"))

            self.assertIn('"engine": "none"', result.stdout)
            self.assertTrue(text_manifest.exists())
            self.assertEqual(payload["records"][0]["engine"], "none")
            self.assertEqual(payload["records"][0]["warnings"], ["ocr_engine_not_selected"])


if __name__ == "__main__":
    unittest.main()
