"""Pipeline wrappers for Excel dry-run and approved apply."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lieshi_ocr.excel.apply_changes import apply_approved_changes
from lieshi_ocr.excel.dry_run import build_excel_dry_run, write_dry_run_outputs
from lieshi_ocr.excel.v6 import build_v6_dry_run, write_v6_dry_run


def run_excel_dry_run(base_xlsx: str | Path, records_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    target_dir = Path(out_dir)
    json_path = target_dir / "dry_run_report.json"
    markdown_path = target_dir / "dry_run_report.md"
    report = build_excel_dry_run(base_xlsx=base_xlsx, records_path=records_path)
    write_dry_run_outputs(report, json_path=json_path, markdown_path=markdown_path)
    return {
        "base_xlsx": Path(base_xlsx).as_posix(),
        "records": Path(records_path).as_posix(),
        "out_dir": target_dir.as_posix(),
        "dry_run_json": json_path.as_posix(),
        "dry_run_markdown": markdown_path.as_posix(),
        "change_count": len(report.proposed_changes),
        "blocked_count": len(report.blocked_changes),
        "record_count": len(report.record_results),
    }


def run_v6_dry_run(base_xlsx: str | Path, records_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    target_dir = Path(out_dir)
    json_path = target_dir / "v6_dry_run_report.json"
    markdown_path = target_dir / "v6_dry_run_report.md"
    report = build_v6_dry_run(base_xlsx=base_xlsx, records_path=records_path)
    write_v6_dry_run(report, json_path=json_path, markdown_path=markdown_path)
    return {
        "base_xlsx": Path(base_xlsx).as_posix(),
        "records": Path(records_path).as_posix(),
        "out_dir": target_dir.as_posix(),
        "dry_run_json": json_path.as_posix(),
        "dry_run_markdown": markdown_path.as_posix(),
        **report["summary"],
    }


def run_excel_apply(
    base_xlsx: str | Path,
    dry_run_path: str | Path,
    approved_path: str | Path,
    out_xlsx: str | Path,
    apply_report_path: str | Path | None = None,
) -> dict[str, Any]:
    report_path = Path(apply_report_path) if apply_report_path else Path(out_xlsx).with_suffix(".apply_report.json")
    return apply_approved_changes(
        base_xlsx=base_xlsx,
        dry_run_path=dry_run_path,
        approved_path=approved_path,
        out_xlsx=out_xlsx,
        apply_report_path=report_path,
    )
