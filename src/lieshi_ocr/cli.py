"""Command line entry points for lieshi_ocr."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DEFAULT_BATCH
from .crop.batch import build_crop_manifest, default_crop_out_dir, discover_batch_pdfs, write_crop_manifest
from .ocr.rapidocr_engine import create_ocr_engine
from .paths import ProjectPaths
from .pipeline.build_review_manifest import build_review_manifest, write_review_outputs
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
    batch.add_argument("--limit", type=int, default=0)
    batch.add_argument("--out-dir", default="", help="Output directory. Defaults to data/work/{batch}/crop.")
    batch.add_argument("--manifest", default="", help="Manifest path. Defaults to <out-dir>/crop_manifest.json.")
    batch.add_argument("--write-crops", action="store_true", help="Write crop PDFs to --out-dir.")
    batch.add_argument("--dry-run", action="store_true", help="Compatibility flag; dry-run is the default.")
    batch.add_argument("--root", default="", help="Project root override.")

    text = subparsers.add_parser("extract-text", help="Build text_manifest.json from crop_manifest.json.")
    text.add_argument("--batch", default=DEFAULT_BATCH)
    text.add_argument("--crop-manifest", default="", help="Defaults to data/work/{batch}/crop/crop_manifest.json.")
    text.add_argument("--out-dir", default="", help="Defaults to data/work/{batch}/text.")
    text.add_argument("--manifest", default="", help="Defaults to <out-dir>/text_manifest.json.")
    text.add_argument("--engine", default="none", choices=["none", "rapidocr"], help="Real OCR runs only when explicitly set.")
    text.add_argument("--mineru-text-dir", default="", help="Optional explicit MinerU markdown/text directory.")
    text.add_argument("--root", default="", help="Project root override.")

    review = subparsers.add_parser("build-review", help="Build correction_records.json and review_report.md.")
    review.add_argument("--batch", default=DEFAULT_BATCH)
    review.add_argument("--text-manifest", default="", help="Defaults to data/work/{batch}/text/text_manifest.json.")
    review.add_argument("--out-dir", default="", help="Defaults to data/work/{batch}/review.")
    review.add_argument("--records", default="", help="Defaults to <out-dir>/correction_records.json.")
    review.add_argument("--report", default="", help="Defaults to <out-dir>/review_report.md.")
    review.add_argument("--root", default="", help="Project root override.")

    args = parser.parse_args(argv)
    if args.command == "crop-one":
        return _crop_one(args)
    if args.command == "crop-batch":
        return _crop_batch(args)
    if args.command == "extract-text":
        return _extract_text(args)
    if args.command == "build-review":
        return _build_review(args)
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
    source_pdfs = discover_batch_pdfs(batch_paths.scan, limit=args.limit)
    if not source_pdfs:
        raise FileNotFoundError(f"No PDFs found in {batch_paths.scan}")

    manifest = build_crop_manifest(
        batch=args.batch,
        source_pdfs=source_pdfs,
        scan_dir=batch_paths.scan,
        out_dir=out_dir,
        write_crops=args.write_crops,
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
    engine = create_ocr_engine(args.engine)
    text_manifest = extract_text_manifest(
        crop_manifest_path=crop_manifest,
        out_dir=out_dir,
        ocr_engine=engine,
        mineru_text_dir=args.mineru_text_dir or None,
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
                "total": len(text_manifest.records),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


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


def _print_summary(payload: dict, manifest_path: Path) -> None:
    summary = {
        "batch": payload["batch"],
        "scan_dir": payload["scan_dir"],
        "out_dir": payload["out_dir"],
        "manifest": manifest_path.as_posix(),
        "write_crops": payload["write_crops"],
        "total": payload["total"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
