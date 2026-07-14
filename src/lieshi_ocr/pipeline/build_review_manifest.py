"""Build review records from text manifests without touching Excel."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from lieshi_ocr.parse.correction_text import CorrectionItem, FIELD_NAMES, empty_fields, parse_correction_text
from lieshi_ocr.parse.normalize import normalize_text

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class RegionText:
    region: str
    text: str
    engine: str
    confidence: float
    crop_pdf: str
    warnings: list[str] = field(default_factory=list)
    text_source: str = ""

    def to_json(self) -> JsonDict:
        return {
            "region": self.region,
            "text": self.text,
            "engine": self.engine,
            "confidence": self.confidence,
            "crop_pdf": self.crop_pdf,
            "warnings": self.warnings,
            "text_source": self.text_source,
        }


@dataclass(frozen=True)
class CorrectionRecord:
    batch: str
    source_pdf: str
    source_stem: str
    code: str
    name: str
    fields: dict[str, str]
    raw_text: str
    normalized_text: str
    items: list[CorrectionItem]
    regions: dict[str, RegionText]
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "source_pdf": self.source_pdf,
            "source_stem": self.source_stem,
            "code": self.code,
            "name": self.name,
            "fields": self.fields,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "items": [item.to_json() for item in self.items],
            "regions": {name: region.to_json() for name, region in self.regions.items()},
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class ReviewManifest:
    batch: str
    text_manifest: str
    out_dir: str
    records: list[CorrectionRecord]

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "text_manifest": self.text_manifest,
            "out_dir": self.out_dir,
            "total": len(self.records),
            "records": [record.to_json() for record in self.records],
        }


def build_review_manifest(text_manifest_path: str | Path, out_dir: str | Path) -> ReviewManifest:
    """Read text_manifest.json and return review records."""

    manifest_path = Path(text_manifest_path)
    text_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    batch = str(text_manifest.get("batch", ""))
    grouped = _group_records(text_manifest.get("records", []))
    records = [_build_record(batch=batch, source_key=key, source_records=items) for key, items in grouped.items()]
    return ReviewManifest(
        batch=batch,
        text_manifest=manifest_path.as_posix(),
        out_dir=Path(out_dir).as_posix(),
        records=records,
    )


def write_review_outputs(manifest: ReviewManifest, records_path: str | Path, report_path: str | Path) -> None:
    records_target = Path(records_path)
    report_target = Path(report_path)
    records_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    records_target.write_text(json.dumps(manifest.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_target.write_text(render_review_report(manifest), encoding="utf-8")


def render_review_report(manifest: ReviewManifest) -> str:
    lines = [
        f"# Review Report - {manifest.batch}",
        "",
        f"- text_manifest: `{manifest.text_manifest}`",
        f"- total records: {len(manifest.records)}",
        "",
    ]
    for record in manifest.records:
        title_code = record.code or "MISSING_CODE"
        title_name = record.name or "MISSING_NAME"
        lines.extend(
            [
                f"## {title_code} / {title_name}",
                "",
                f"- source: `{record.source_pdf}`",
                f"- source_stem: `{record.source_stem}`",
                f"- warnings: {', '.join(record.warnings) if record.warnings else 'none'}",
                f"- unlabeled inference: {'yes' if _has_unlabeled_inference(record.warnings) else 'no'}",
                "",
                "| Field | Value |",
                "| --- | --- |",
            ]
        )
        for field_name in FIELD_NAMES:
            lines.append(f"| {field_name} | {_escape_table(record.fields.get(field_name, ''))} |")
        lines.extend(["", "### Correction Text", "", record.raw_text or "_empty_", ""])
    return "\n".join(lines).rstrip() + "\n"


def _group_records(records: Any) -> dict[str, list[JsonDict]]:
    grouped: dict[str, list[JsonDict]] = {}
    if not isinstance(records, list):
        return grouped
    for record in records:
        if not isinstance(record, dict):
            continue
        source_pdf = str(record.get("source_pdf", ""))
        source_stem = str(record.get("source_stem", Path(source_pdf).stem))
        key = source_stem or source_pdf or f"record_{len(grouped)}"
        grouped.setdefault(key, []).append(record)
    return grouped


def _build_record(batch: str, source_key: str, source_records: list[JsonDict]) -> CorrectionRecord:
    warnings: list[str] = []
    regions: dict[str, RegionText] = {}
    source_pdf = ""
    source_stem = source_key

    for item in source_records:
        source_pdf = source_pdf or str(item.get("source_pdf", ""))
        source_stem = str(item.get("source_stem", source_stem)) or source_stem
        region = str(item.get("region", ""))
        if not region:
            warnings.append("region_missing")
            continue
        if region in regions:
            warnings.append(f"{region}:duplicate_region")
            continue
        region_warnings = [str(warning) for warning in item.get("warnings", []) if isinstance(warning, str)]
        warnings.extend(f"{region}:{warning}" for warning in region_warnings)
        regions[region] = RegionText(
            region=region,
            text=str(item.get("text", "")),
            engine=str(item.get("engine", "")),
            confidence=float(item.get("confidence", 0.0) or 0.0),
            crop_pdf=str(item.get("crop_pdf", "")),
            warnings=region_warnings,
            text_source=str(item.get("text_source", "")),
        )

    correction_text = regions.get("correction").text if "correction" in regions else ""
    parse_result = parse_correction_text(correction_text)
    fields = empty_fields()
    fields.update(parse_result.fields)
    warnings.extend(parse_result.warnings)
    if "correction" not in regions or not correction_text.strip():
        warnings.append("correction_text_missing")

    code_from_region = _clean_region_value(regions.get("code").text if "code" in regions else "", ("编号",))
    name_from_region = _clean_region_value(regions.get("name").text if "name" in regions else "", ("姓名",))
    parsed_code = fields.get("编号", "")
    parsed_name = fields.get("姓名", "")

    code = code_from_region or parsed_code
    name = name_from_region or parsed_name
    if code_from_region and parsed_code and code_from_region != parsed_code:
        warnings.append("code_conflict")
    if name_from_region and parsed_name and name_from_region != parsed_name:
        warnings.append("name_conflict")
    if not code:
        warnings.append("code_missing")
    if not name:
        warnings.append("name_missing")

    fields["编号"] = code
    fields["姓名"] = name

    return CorrectionRecord(
        batch=batch,
        source_pdf=source_pdf,
        source_stem=source_stem,
        code=code,
        name=name,
        fields=fields,
        raw_text=correction_text,
        normalized_text=normalize_text(correction_text),
        items=parse_result.items,
        regions=regions,
        warnings=_dedupe(warnings),
    )


def _clean_region_value(text: str, labels: tuple[str, ...]) -> str:
    value = normalize_text(text).replace("\n", " ")
    for label in labels:
        value = re.sub(rf"^{re.escape(label)}\s*:\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ;；,，。")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _has_unlabeled_inference(warnings: list[str]) -> bool:
    return any(
        warning in {
            "unlabeled_text_parsed",
            "sacrifice_time_inferred",
            "sacrifice_place_inferred",
            "sacrifice_reason_inferred",
            "brief_deed_from_unlabeled_text",
            "burial_place_inferred",
        }
        for warning in warnings
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
