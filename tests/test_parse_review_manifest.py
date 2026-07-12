from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.parse.correction_text import FIELD_NAMES, parse_correction_text
from lieshi_ocr.pipeline.build_review_manifest import build_review_manifest, write_review_outputs


def _write_text_manifest(path: Path, correction_text: str, code_text: str = "QX-0001", name_text: str = "张三") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch": "20260626",
        "crop_manifest": "data/work/20260626/crop/crop_manifest.json",
        "out_dir": "data/work/20260626/text",
        "total": 3,
        "records": [
            {
                "batch": "20260626",
                "source_pdf": "data/scan/20260626/sample.pdf",
                "source_stem": "sample",
                "region": "code",
                "crop_pdf": "data/work/20260626/crop/sample__code.pdf",
                "engine": "fake",
                "text": code_text,
                "confidence": 1.0,
                "warnings": [],
                "text_source": "",
            },
            {
                "batch": "20260626",
                "source_pdf": "data/scan/20260626/sample.pdf",
                "source_stem": "sample",
                "region": "name",
                "crop_pdf": "data/work/20260626/crop/sample__name.pdf",
                "engine": "fake",
                "text": name_text,
                "confidence": 1.0,
                "warnings": [],
                "text_source": "",
            },
            {
                "batch": "20260626",
                "source_pdf": "data/scan/20260626/sample.pdf",
                "source_stem": "sample",
                "region": "correction",
                "crop_pdf": "data/work/20260626/crop/sample__correction.pdf",
                "engine": "fake",
                "text": correction_text,
                "confidence": 1.0,
                "warnings": [],
                "text_source": "data/work/20260626/mineru/sample.md",
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ParseReviewManifestTests(unittest.TestCase):
    def test_parse_correction_text_normalizes_common_labels_and_line_breaks(self) -> None:
        result = parse_correction_text(
            "编号：QX-0001\n"
            "姓名 ： 张三\n"
            "籍贯: 山西祁县\n"
            "栖牲原因：战斗\n"
            "事迹：第一段\n"
            "第二段\n"
            "安葬地：祁县烈士陵园"
        )

        self.assertEqual(result.fields["编号"], "QX-0001")
        self.assertEqual(result.fields["姓名"], "张三")
        self.assertEqual(result.fields["牺牲原因"], "战斗")
        self.assertEqual(result.fields["事迹"], "第一段第二段")
        self.assertEqual(result.fields["安葬地"], "祁县烈士陵园")
        self.assertEqual(result.warnings, [])

    def test_labeled_fields_take_priority_over_unlabeled_patterns(self) -> None:
        result = parse_correction_text(
            "\u727a\u7272\u65f6\u95f4: 1937\u5e748\u6708\n"
            "\u4e8b\u8ff9: 1937\u5e748\u6708\u5728\u67d0\u5730\u6218\u6597\u4e2d\u727a\u7272"
        )

        self.assertEqual(result.fields[FIELD_NAMES[9]], "1937\u5e748\u6708")
        self.assertEqual(result.fields[FIELD_NAMES[12]], "1937\u5e748\u6708\u5728\u67d0\u5730\u6218\u6597\u4e2d\u727a\u7272")
        self.assertNotIn("unlabeled_text_parsed", result.warnings)

    def test_unlabeled_sacrifice_sentence_infers_review_candidates(self) -> None:
        result = parse_correction_text(
            "1937\u5e748\u6708\u5728\u592a\u884c\u5c71\u6218\u6597\u4e2d\u727a\u7272\u3002"
            "\u5b89\u846c\u4e8e\u7941\u53bf\u70c8\u58eb\u9675\u56ed\u3002"
        )

        self.assertEqual(result.fields[FIELD_NAMES[9]], "1937\u5e748\u6708")
        self.assertEqual(result.fields[FIELD_NAMES[10]], "\u592a\u884c\u5c71")
        self.assertEqual(result.fields[FIELD_NAMES[11]], "\u6218\u6597")
        self.assertEqual(result.fields[FIELD_NAMES[13]], "\u7941\u53bf\u70c8\u58eb\u9675\u56ed")
        self.assertIn("unlabeled_text_parsed", result.warnings)
        self.assertIn("sacrifice_time_inferred", result.warnings)
        self.assertIn("sacrifice_place_inferred", result.warnings)
        self.assertIn("brief_deed_from_unlabeled_text", result.warnings)
        self.assertIn("burial_place_inferred", result.warnings)
        self.assertIn("needs_human_review", result.warnings)

    def test_unlabeled_burial_only_is_review_candidate(self) -> None:
        result = parse_correction_text("\u540e\u7531\u4eb2\u5c5e\u6536\u6b93\uff0c\u5b89\u846c\u5728\u67d0\u6751\u897f\u5c71\u3002")

        self.assertEqual(result.fields[FIELD_NAMES[13]], "\u67d0\u6751\u897f\u5c71")
        self.assertIn("burial_place_inferred", result.warnings)
        self.assertIn("needs_human_review", result.warnings)

    def test_unlabeled_text_without_clear_pattern_does_not_guess(self) -> None:
        result = parse_correction_text("\u53c2\u52a0\u5730\u65b9\u5de5\u4f5c\uff0c\u8868\u73b0\u79ef\u6781\u3002")

        self.assertFalse(any(result.fields.values()))
        self.assertEqual(result.warnings, ["no_labeled_fields_found"])

    def test_multiple_dates_do_not_force_sacrifice_time_choice(self) -> None:
        result = parse_correction_text(
            "1920\u5e74\u51fa\u751f\u30021937\u5e748\u6708\u5728\u592a\u884c\u5c71\u727a\u7272\u3002"
        )

        self.assertEqual(result.fields[FIELD_NAMES[9]], "")
        self.assertEqual(result.fields[FIELD_NAMES[10]], "\u592a\u884c\u5c71")
        self.assertIn("multiple_date_candidates", result.warnings)
        self.assertIn("needs_human_review", result.warnings)

    def test_build_review_manifest_merges_regions_and_prefers_region_code_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_manifest = root / "text_manifest.json"
            correction = (
                "编号：QX-9999\n"
                "姓名：李四\n"
                "籍贯：山西祁县\n"
                "出生时间：1920年\n"
                "参加革命时间：1938年\n"
                "政治面貌：党员\n"
                "民族：汉族\n"
                "生前单位及职务：某部战士\n"
                "牺牲时间：1942年\n"
                "牺牲地点：太行山\n"
                "牺牲原因：战斗牺牲\n"
                "事迹：参加抗日斗争\n"
                "安葬地：祁县"
            )
            _write_text_manifest(text_manifest, correction)

            manifest = build_review_manifest(text_manifest, root / "review")
            record = manifest.records[0]

            self.assertEqual(record.code, "QX-0001")
            self.assertEqual(record.name, "张三")
            self.assertEqual(record.fields["编号"], "QX-0001")
            self.assertEqual(record.fields["姓名"], "张三")
            self.assertEqual(record.fields["参加革命/工作时间"], "1938年")
            self.assertEqual(record.fields["牺牲地点"], "太行山")
            self.assertEqual(record.regions["correction"].text_source, "data/work/20260626/mineru/sample.md")
            self.assertIn("code_conflict", record.warnings)
            self.assertIn("name_conflict", record.warnings)

    def test_missing_code_name_are_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_manifest = root / "text_manifest.json"
            _write_text_manifest(text_manifest, "事迹：无编号姓名文本", code_text="", name_text="")

            manifest = build_review_manifest(text_manifest, root / "review")
            record = manifest.records[0]

            self.assertIn("code_missing", record.warnings)
            self.assertIn("name_missing", record.warnings)

    def test_write_review_outputs_to_explicit_temp_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_manifest = root / "text_manifest.json"
            records_path = root / "review" / "correction_records.json"
            report_path = root / "review" / "review_report.md"
            _write_text_manifest(text_manifest, "编号：QX-0001\n姓名：张三\n事迹：测试")

            manifest = build_review_manifest(text_manifest, root / "review")
            write_review_outputs(manifest, records_path, report_path)
            payload = json.loads(records_path.read_text(encoding="utf-8"))
            report = report_path.read_text(encoding="utf-8")

            self.assertEqual(payload["total"], 1)
            self.assertIn("QX-0001 / 张三", report)
            self.assertIn("| 事迹 | 测试 |", report)

    def test_unlabeled_inference_is_written_to_records_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_manifest = root / "text_manifest.json"
            records_path = root / "review" / "correction_records.json"
            report_path = root / "review" / "review_report.md"
            correction = "1937\u5e748\u6708\u5728\u592a\u884c\u5c71\u6218\u6597\u4e2d\u727a\u7272\u3002"
            _write_text_manifest(text_manifest, correction)

            manifest = build_review_manifest(text_manifest, root / "review")
            write_review_outputs(manifest, records_path, report_path)
            payload = json.loads(records_path.read_text(encoding="utf-8"))
            report = report_path.read_text(encoding="utf-8")
            record = payload["records"][0]

            self.assertEqual(record["fields"][FIELD_NAMES[10]], "\u592a\u884c\u5c71")
            self.assertIn("unlabeled_text_parsed", record["warnings"])
            self.assertIn("needs_human_review", record["warnings"])
            self.assertIn("- unlabeled inference: yes", report)

    def test_cli_build_review_writes_default_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            text_manifest = root / "data" / "work" / "20260626" / "text" / "text_manifest.json"
            records_path = root / "data" / "work" / "20260626" / "review" / "correction_records.json"
            report_path = root / "data" / "work" / "20260626" / "review" / "review_report.md"
            _write_text_manifest(text_manifest, "编号：QX-0001\n姓名：张三\n事迹：CLI测试")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lieshi_ocr.cli",
                    "build-review",
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

            self.assertTrue(records_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn('"total": 1', result.stdout)


if __name__ == "__main__":
    unittest.main()
