"""Command line entry points for lieshi_ocr."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DEFAULT_BATCH
from .crop.batch import build_crop_manifest, default_crop_out_dir, discover_batch_pdfs, write_crop_manifest
from .ocr.rapidocr_engine import TextOcrEngine, create_ocr_engine
from .paths import ProjectPaths
from .pipeline.audit_ocr import build_ocr_audit, write_ocr_audit_outputs
from .pipeline.build_review_manifest import build_review_manifest, write_review_outputs
from .pipeline.excel_update import run_excel_apply, run_excel_dry_run
from .pipeline.extract_text import extract_text_manifest, write_text_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lieshi_ocr.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    one = subparsers.add_parser("crop-one", help="Plan or write crops for one explicit PDF.")
    one.add_argument("--pdf", required=True, help="Explicit source PDF path.")
    one.add_argument("--batch", default=DEFAULT_BATCH)
    one.add_argument("--out-dir", default="", help="Output directory. Defaults to data/work/{batch}/crop.")
    one.add_argument("--manifest", default="", help="Manifest path. Defaults to <out-dir>/crop_manifest.json.")
    one.add_argument("--write-crops", action="store_true", help="Write crop PDFs to --out-dir.")
    one.add_argument("--root", default="", help="Project root override for default output paths.")

    batch = subparsers.add_parser("crop-batch", help="Plan or write crops for data/scan/{batch}.")
    batch.add_argument("--batch", default=DEFAULT_BATCH)
    batch.add_argument("--scan-dir", default="", help="Scan directory override. Defaults to data/scan/{batch}.")
    batch.add_argument("--limit", type=int, default=0)
    batch.add_argument("--out-dir", default="", help="Output directory. Defaults to data/work/{batch}/crop.")
    batch.add_argument("--manifest", default="", help="Manifest path. Defaults to <out-dir>/crop_manifest.json.")
    batch.add_argument("--write-crops", action="store_true", help="Write crop PDFs to --out-dir.")
    batch.add_argument(
        "--refine-name-cell",
        action="store_true",
        help="Refine only the name crop using optional table-line detection.",
    )
    batch.add_argument(
        "--write-debug",
        action="store_true",
        help="Write name-cell debug overlays; requires --refine-name-cell.",
    )
    batch.add_argument("--dry-run", action="store_true", help="Compatibility flag; dry-run is the default.")
    batch.add_argument("--root", default="", help="Project root override.")

    text = subparsers.add_parser("extract-text", help="Build text_manifest.json from crop_manifest.json.")
    text.add_argument("--batch", default=DEFAULT_BATCH)
    text.add_argument("--crop-manifest", default="", help="Defaults to data/work/{batch}/crop/crop_manifest.json.")
    text.add_argument("--out-dir", default="", help="Defaults to data/work/{batch}/text.")
    text.add_argument("--manifest", default="", help="Defaults to <out-dir>/text_manifest.json.")
    text.add_argument("--engine", default="none", choices=["none", "rapidocr"], help="Real OCR runs only when explicitly set.")
    text.add_argument(
        "--code-name-engine",
        default="",
        metavar="{none,rapidocr}",
        help="Engine for code/name regions. Defaults to --engine.",
    )
    text.add_argument(
        "--correction-engine",
        default="",
        metavar="{none,mineru,rapidocr}",
        help="Engine for correction region. Defaults to mineru when --mineru-text-dir is set, otherwise --engine.",
    )
    text.add_argument("--mineru-text-dir", default="", help="Optional explicit MinerU markdown/text directory.")
    text.add_argument("--root", default="", help="Project root override.")

    review = subparsers.add_parser("build-review", help="Build correction_records.json and review_report.md.")
    review.add_argument("--batch", default=DEFAULT_BATCH)
    review.add_argument("--text-manifest", default="", help="Defaults to data/work/{batch}/text/text_manifest.json.")
    review.add_argument("--out-dir", default="", help="Defaults to data/work/{batch}/review.")
    review.add_argument("--records", default="", help="Defaults to <out-dir>/correction_records.json.")
    review.add_argument("--report", default="", help="Defaults to <out-dir>/review_report.md.")
    review.add_argument("--root", default="", help="Project root override.")

    audit = subparsers.add_parser("audit-ocr", help="Build read-only OCR audit JSON and HTML reports.")
    audit.add_argument("--text-manifest", required=True, help="text_manifest.json path.")
    audit.add_argument("--records", required=True, help="correction_records.json path.")
    audit.add_argument("--base-xlsx", required=True, help="Explicit trusted v4 baseline workbook.")
    audit.add_argument("--out-dir", required=True, help="Directory for ocr_audit_report.json/html.")

    dry_run = subparsers.add_parser("excel-dry-run", help="Build Excel dry-run JSON and Markdown reports.")
    dry_run.add_argument("--base-xlsx", required=True, help="Explicit trusted v4 baseline workbook.")
    dry_run.add_argument("--records", required=True, help="correction_records.json path.")
    dry_run.add_argument("--out-dir", required=True, help="Directory for dry_run_report.json/md.")

    apply = subparsers.add_parser("excel-apply", help="Apply approved Excel changes to a candidate workbook.")
    apply.add_argument("--base-xlsx", required=True, help="Explicit trusted v4 baseline workbook.")
    apply.add_argument("--dry-run", required=True, help="dry_run_report.json path.")
    apply.add_argument("--approved", required=True, help="approved_changes.json path.")
    apply.add_argument("--out-xlsx", required=True, help="Candidate workbook output path.")
    apply.add_argument("--apply-report", default="", help="Defaults to <out-xlsx>.apply_report.json.")

    args = parser.parse_args(argv)
    if args.command == "crop-one":
        return _crop_one(args)
    if args.command == "crop-batch":
        return _crop_batch(args)
    if args.command == "extract-text":
        return _extract_text(args)
    if args.command == "build-review":
        return _build_review(args)
    if args.command == "audit-ocr":
        return _audit_ocr(args)
    if args.command == "excel-dry-run":
        return _excel_dry_run(args)
    if args.command == "excel-apply":
        return _excel_apply(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _project_paths(root: str) -> ProjectPaths:
    return ProjectPaths.discover(root or None)


def _out_dir(paths: ProjectPaths, batch: str, out_dir: str) -> Path:
    if out_dir:
        return Path(out_dir)
    return default_crop_out_dir(paths.batch(batch).work)


def _manifest_path(out_dir: Path, manifest: str) -> Path:
    return Path(manifest) if manifest else out_dir / "crop_manifest.json"


def _text_out_dir(paths: ProjectPaths, batch: str, out_dir: str) -> Path:
    if out_dir:
        return Path(out_dir)
    return paths.batch(batch).work / "text"


def _text_manifest_path(out_dir: Path, manifest: str) -> Path:
    return Path(manifest) if manifest else out_dir / "text_manifest.json"


def _review_out_dir(paths: ProjectPaths, batch: str, out_dir: str) -> Path:
    if out_dir:
        return Path(out_dir)
    return paths.batch(batch).work / "review"


def _review_records_path(out_dir: Path, records: str) -> Path:
    return Path(records) if records else out_dir / "correction_records.json"


def _review_report_path(out_dir: Path, report: str) -> Path:
    return Path(report) if report else out_dir / "review_report.md"


def _crop_one(args: argparse.Namespace) -> int:
    paths = _project_paths(args.root)
    out_dir = _out_dir(paths, args.batch, args.out_dir)
    manifest_path = _manifest_path(out_dir, args.manifest)
    source_pdf = Path(args.pdf)

    manifest = build_crop_manifest(
        batch=args.batch,
        source_pdfs=[source_pdf],
        scan_dir=source_pdf.parent,
        out_dir=out_dir,
        write_crops=args.write_crops,
    )
    write_crop_manifest(manifest, manifest_path)
    _print_summary(manifest.to_json(), manifest_path)
    return 0


def _crop_batch(args: argparse.Namespace) -> int:
    paths = _project_paths(args.root)
    batch_paths = paths.batch(args.batch)
    out_dir = _out_dir(paths, args.batch, args.out_dir)
    manifest_path = _manifest_path(out_dir, args.manifest)
    scan_dir = Path(args.scan_dir) if args.scan_dir else batch_paths.scan
    source_pdfs = discover_batch_pdfs(scan_dir, limit=args.limit)
    if not source_pdfs:
        raise FileNotFoundError(f"No PDFs found in {scan_dir}")
    if args.write_debug and not args.refine_name_cell:
        raise ValueError("--write-debug requires --refine-name-cell")

    manifest = build_crop_manifest(
        batch=args.batch,
        source_pdfs=source_pdfs,
        scan_dir=scan_dir,
        out_dir=out_dir,
        write_crops=args.write_crops,
        refine_name_cell=args.refine_name_cell,
        write_debug=args.write_debug,
    )
    write_crop_manifest(manifest, manifest_path)
    _print_summary(manifest.to_json(), manifest_path)
    return 0


def _extract_text(args: argparse.Namespace) -> int:
    paths = _project_paths(args.root)
    batch_paths = paths.batch(args.batch)
    crop_manifest = Path(args.crop_manifest) if args.crop_manifest else batch_paths.work / "crop" / "crop_manifest.json"
    out_dir = _text_out_dir(paths, args.batch, args.out_dir)
    manifest_path = _text_manifest_path(out_dir, args.manifest)
    engine_names = _text_engine_names(args)
    engines = _text_engines(engine_names)
    text_manifest = extract_text_manifest(
        crop_manifest_path=crop_manifest,
        out_dir=out_dir,
        ocr_engine=engines["default"],
        code_name_ocr_engine=engines["code_name"],
        correction_ocr_engine=engines["correction"],
        mineru_text_dir=args.mineru_text_dir or None,
        use_mineru_correction=engine_names["correction"] == "mineru",
    )
    write_text_manifest(text_manifest, manifest_path)
    print(
        json.dumps(
            {
                "batch": text_manifest.batch,
                "crop_manifest": crop_manifest.as_posix(),
                "out_dir": out_dir.as_posix(),
                "manifest": manifest_path.as_posix(),
                "engine": args.engine,
                "code_name_engine": engine_names["code_name"],
                "correction_engine": engine_names["correction"],
                "total": len(text_manifest.records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _text_engine_names(args: argparse.Namespace) -> dict[str, str]:
    code_name = args.code_name_engine or args.engine
    if args.correction_engine:
        correction = args.correction_engine
    elif args.mineru_text_dir:
        correction = "mineru"
    else:
        correction = args.engine
    if code_name not in {"none", "rapidocr"}:
        raise ValueError("--code-name-engine must be one of: none, rapidocr")
    if correction not in {"none", "mineru", "rapidocr"}:
        raise ValueError("--correction-engine must be one of: none, mineru, rapidocr")
    if correction == "mineru" and not args.mineru_text_dir:
        raise ValueError("--correction-engine mineru requires --mineru-text-dir")
    return {"default": args.engine, "code_name": code_name, "correction": correction}


def _text_engines(names: dict[str, str]) -> dict[str, TextOcrEngine]:
    created: dict[str, TextOcrEngine] = {}

    def engine_for(name: str) -> TextOcrEngine:
        if name == "mineru":
            name = "none"
        if name not in created:
            created[name] = create_ocr_engine(name)
        return created[name]

    return {
        "default": engine_for(names["default"]),
        "code_name": engine_for(names["code_name"]),
        "correction": engine_for(names["correction"]),
    }


def _build_review(args: argparse.Namespace) -> int:
    paths = _project_paths(args.root)
    batch_paths = paths.batch(args.batch)
    text_manifest = Path(args.text_manifest) if args.text_manifest else batch_paths.work / "text" / "text_manifest.json"
    out_dir = _review_out_dir(paths, args.batch, args.out_dir)
    records_path = _review_records_path(out_dir, args.records)
    report_path = _review_report_path(out_dir, args.report)
    review_manifest = build_review_manifest(text_manifest_path=text_manifest, out_dir=out_dir)
    write_review_outputs(review_manifest, records_path, report_path)
    print(
        json.dumps(
            {
                "batch": review_manifest.batch,
                "text_manifest": text_manifest.as_posix(),
                "out_dir": out_dir.as_posix(),
                "records": records_path.as_posix(),
                "report": report_path.as_posix(),
                "total": len(review_manifest.records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _excel_dry_run(args: argparse.Namespace) -> int:
    summary = run_excel_dry_run(base_xlsx=args.base_xlsx, records_path=args.records, out_dir=args.out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _audit_ocr(args: argparse.Namespace) -> int:
    report = build_ocr_audit(
        text_manifest_path=args.text_manifest,
        records_path=args.records,
        base_xlsx=args.base_xlsx,
    )
    json_path, html_path = write_ocr_audit_outputs(report, args.out_dir)
    print(
        json.dumps(
            {
                "out_dir": Path(args.out_dir).as_posix(),
                "json": json_path.as_posix(),
                "html": html_path.as_posix(),
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _excel_apply(args: argparse.Namespace) -> int:
    summary = run_excel_apply(
        base_xlsx=args.base_xlsx,
        dry_run_path=args.dry_run,
        approved_path=args.approved,
        out_xlsx=args.out_xlsx,
        apply_report_path=args.apply_report or None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _print_summary(payload: dict, manifest_path: Path) -> None:
    summary = {
        "batch": payload["batch"],
        "scan_dir": payload["scan_dir"],
        "out_dir": payload["out_dir"],
        "manifest": manifest_path.as_posix(),
        "write_crops": payload["write_crops"],
        "refine_name_cell": payload.get("refine_name_cell", False),
        "write_debug": payload.get("write_debug", False),
        "total": payload["total"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
