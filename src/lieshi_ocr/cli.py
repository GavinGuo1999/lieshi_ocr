"""Command line entry points for lieshi_ocr."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DEFAULT_BATCH
from .crop.batch import build_crop_manifest, default_crop_out_dir, discover_batch_pdfs, write_crop_manifest
from .paths import ProjectPaths


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

    args = parser.parse_args(argv)
    if args.command == "crop-one":
        return _crop_one(args)
    if args.command == "crop-batch":
        return _crop_batch(args)
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
