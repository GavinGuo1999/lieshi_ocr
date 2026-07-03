from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lieshi_ocr.schemas import BatchManifest, DryRunReport, OcrRecord, SchemaError


class SchemaTests(unittest.TestCase):
    def test_ocr_record_accepts_region_payload(self) -> None:
        record = OcrRecord.from_mapping(
            {
                "source_pdf": "data/scan/a.pdf",
                "source_stem": "a",
                "code": "晋祁县000001",
                "name": "测试",
                "quality": "review_needed",
                "cut_pdf": "data/work/a.pdf",
                "json": "data/work/a.json",
                "warnings": ["parse_low_confidence"],
                "ocr": {"correction_text_clean": "籍贯补充完善为..."},
                "correction_items": {
                    "籍贯": {"value": "山西省晋中市祁县", "reason": "依据英名录"}
                },
                "regions": {"code": {"image_size": [100, 20]}},
            }
        )

        self.assertEqual(record.quality, "review_needed")
        self.assertIn("籍贯", record.correction_items)
        self.assertEqual(record.to_manifest_entry()["code"], "晋祁县000001")

    def test_batch_manifest_total_must_match_records(self) -> None:
        with self.assertRaises(SchemaError):
            BatchManifest.from_mapping(
                {
                    "batch": "20260626",
                    "total": 2,
                    "records": [
                        {
                            "source_stem": "a",
                            "code": "晋祁县000001",
                            "name": "测试",
                            "json": "a.json",
                            "quality": "ok",
                        }
                    ],
                }
            )

    def test_invalid_quality_is_rejected(self) -> None:
        with self.assertRaises(SchemaError):
            OcrRecord.from_mapping({"source_stem": "a", "quality": "maybe"})

    def test_dry_run_report_parses_changes(self) -> None:
        report = DryRunReport.from_mapping(
            {
                "generated_at": "2026-07-01T12:00:00",
                "input": {"v4_xlsx": "v4.xlsx"},
                "summary": {"proposed_changes": 1},
                "proposed_changes": [
                    {
                        "row": 2,
                        "code": "晋祁县000001",
                        "name": "测试",
                        "column": 6,
                        "target": "origin",
                        "field": "籍贯",
                        "old": "",
                        "new": "山西省晋中市祁县",
                        "reason": "依据英名录",
                        "source_stem": "scan001",
                    }
                ],
            }
        )

        self.assertEqual(report.proposed_changes[0].target, "origin")


if __name__ == "__main__":
    unittest.main()
