"""Typed contracts for OCR manifests, correction items, and dry-run reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
import json

JsonDict = dict[str, Any]

QUALITY_OK = "ok"
QUALITY_REVIEW_NEEDED = "review_needed"
QUALITY_FAILED = "failed"
VALID_QUALITIES = {QUALITY_OK, QUALITY_REVIEW_NEEDED, QUALITY_FAILED}


class SchemaError(ValueError):
    """Raised when a JSON payload does not match the project contract."""


def load_json(path: str | Path) -> JsonDict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaError(f"Expected JSON object in {path}")
    return data


def dump_json(data: Mapping[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _require_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise SchemaError(f"Expected string field: {key}")
    return value


def _optional_str(data: Mapping[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise SchemaError(f"Expected string field: {key}")
    return value


def _optional_int(data: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"Expected integer field: {key}")
    return value


def _optional_list(data: Mapping[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise SchemaError(f"Expected list field: {key}")
    return value


def _optional_dict(data: Mapping[str, Any], key: str) -> JsonDict:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SchemaError(f"Expected object field: {key}")
    return dict(value)


def _extra(data: Mapping[str, Any], known: set[str]) -> JsonDict:
    return {key: value for key, value in data.items() if key not in known}


def validate_quality(value: str) -> str:
    if value not in VALID_QUALITIES:
        raise SchemaError(f"Invalid quality: {value}")
    return value


@dataclass(frozen=True)
class CorrectionItem:
    field: str
    value: str
    reason: str = ""
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, field_name: str, data: Mapping[str, Any]) -> "CorrectionItem":
        if not isinstance(field_name, str) or not field_name:
            raise SchemaError("Correction item field name must be a non-empty string")
        known = {"value", "reason"}
        return cls(
            field=field_name,
            value=_optional_str(data, "value"),
            reason=_optional_str(data, "reason"),
            extra=_extra(data, known),
        )

    def to_json(self) -> JsonDict:
        payload = {"value": self.value, "reason": self.reason}
        payload.update(self.extra)
        return payload


@dataclass(frozen=True)
class OcrRecord:
    source_pdf: str
    source_stem: str
    code: str
    name: str
    quality: str
    cut_pdf: str
    json_path: str
    warnings: list[str] = field(default_factory=list)
    ocr: JsonDict = field(default_factory=dict)
    correction_items: dict[str, CorrectionItem] = field(default_factory=dict)
    regions: JsonDict = field(default_factory=dict)
    mineru: JsonDict = field(default_factory=dict)
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "OcrRecord":
        known = {
            "source_pdf",
            "source_stem",
            "code",
            "name",
            "quality",
            "cut_pdf",
            "json",
            "warnings",
            "ocr",
            "correction_items",
            "regions",
            "mineru",
        }
        warnings = _optional_list(data, "warnings")
        if not all(isinstance(item, str) for item in warnings):
            raise SchemaError("warnings must contain only strings")

        raw_items = _optional_dict(data, "correction_items")
        correction_items = {
            key: CorrectionItem.from_mapping(key, value)
            for key, value in raw_items.items()
            if isinstance(value, Mapping)
        }
        if len(correction_items) != len(raw_items):
            raise SchemaError("correction_items values must be objects")

        return cls(
            source_pdf=_optional_str(data, "source_pdf"),
            source_stem=_require_str(data, "source_stem"),
            code=_optional_str(data, "code"),
            name=_optional_str(data, "name"),
            quality=validate_quality(_optional_str(data, "quality", QUALITY_FAILED)),
            cut_pdf=_optional_str(data, "cut_pdf"),
            json_path=_optional_str(data, "json"),
            warnings=list(warnings),
            ocr=_optional_dict(data, "ocr"),
            correction_items=correction_items,
            regions=_optional_dict(data, "regions"),
            mineru=_optional_dict(data, "mineru"),
            extra=_extra(data, known),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "OcrRecord":
        return cls.from_mapping(load_json(path))

    def to_manifest_entry(self) -> JsonDict:
        return {
            "source_pdf": self.source_pdf,
            "source_stem": self.source_stem,
            "code": self.code,
            "name": self.name,
            "quality": self.quality,
            "cut_pdf": self.cut_pdf,
            "json": self.json_path,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class ManifestRecord:
    source_stem: str
    code: str
    name: str
    json_path: str
    quality: str
    warnings: list[str] = field(default_factory=list)
    source_pdf: str = ""
    cut_pdf: str = ""
    mineru_item_count: int = 0
    mineru_marker_count: int = 0
    mineru_reason_count: int = 0
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ManifestRecord":
        known = {
            "source_stem",
            "code",
            "name",
            "json",
            "quality",
            "warnings",
            "source_pdf",
            "cut_pdf",
            "mineru_item_count",
            "mineru_marker_count",
            "mineru_reason_count",
        }
        warnings = _optional_list(data, "warnings")
        if not all(isinstance(item, str) for item in warnings):
            raise SchemaError("warnings must contain only strings")

        return cls(
            source_stem=_require_str(data, "source_stem"),
            code=_optional_str(data, "code"),
            name=_optional_str(data, "name"),
            json_path=_optional_str(data, "json"),
            quality=validate_quality(_optional_str(data, "quality", QUALITY_FAILED)),
            warnings=list(warnings),
            source_pdf=_optional_str(data, "source_pdf"),
            cut_pdf=_optional_str(data, "cut_pdf"),
            mineru_item_count=_optional_int(data, "mineru_item_count"),
            mineru_marker_count=_optional_int(data, "mineru_marker_count"),
            mineru_reason_count=_optional_int(data, "mineru_reason_count"),
            extra=_extra(data, known),
        )


@dataclass(frozen=True)
class BatchManifest:
    batch: str
    records: list[ManifestRecord]
    total: int = 0
    quality_counts: JsonDict = field(default_factory=dict)
    warning_counts: JsonDict = field(default_factory=dict)
    generated_at: str = ""
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "BatchManifest":
        known = {"batch", "records", "total", "quality_counts", "warning_counts", "generated_at"}
        raw_records = _optional_list(data, "records")
        records = [
            ManifestRecord.from_mapping(record)
            for record in raw_records
            if isinstance(record, Mapping)
        ]
        if len(records) != len(raw_records):
            raise SchemaError("records must contain only objects")

        total = _optional_int(data, "total", len(records))
        if total != len(records):
            raise SchemaError(f"Manifest total {total} does not match records length {len(records)}")

        return cls(
            batch=_require_str(data, "batch"),
            records=records,
            total=total,
            quality_counts=_optional_dict(data, "quality_counts"),
            warning_counts=_optional_dict(data, "warning_counts"),
            generated_at=_optional_str(data, "generated_at"),
            extra=_extra(data, known),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "BatchManifest":
        return cls.from_mapping(load_json(path))


@dataclass(frozen=True)
class ProposedChange:
    row: int
    code: str
    name: str
    column: int
    target: str
    field: str
    old: str
    new: str
    reason: str
    source_stem: str = ""
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProposedChange":
        known = {"row", "code", "name", "column", "target", "field", "old", "new", "reason", "source_stem"}
        return cls(
            row=_optional_int(data, "row"),
            code=_require_str(data, "code"),
            name=_optional_str(data, "name"),
            column=_optional_int(data, "column"),
            target=_require_str(data, "target"),
            field=_require_str(data, "field"),
            old=_optional_str(data, "old"),
            new=_optional_str(data, "new"),
            reason=_optional_str(data, "reason"),
            source_stem=_optional_str(data, "source_stem"),
            extra=_extra(data, known),
        )

    def to_json(self) -> JsonDict:
        payload = {
            "row": self.row,
            "code": self.code,
            "name": self.name,
            "column": self.column,
            "target": self.target,
            "field": self.field,
            "old": self.old,
            "new": self.new,
            "reason": self.reason,
            "source_stem": self.source_stem,
        }
        payload.update(self.extra)
        return payload


@dataclass(frozen=True)
class DryRunReport:
    generated_at: str
    input: JsonDict
    summary: JsonDict
    proposed_changes: list[ProposedChange]
    rows_not_found: list[JsonDict] = field(default_factory=list)
    name_mismatches: list[JsonDict] = field(default_factory=list)
    review_needed: list[JsonDict] = field(default_factory=list)
    unmapped_items: list[JsonDict] = field(default_factory=list)
    skipped_low_confidence_changes: list[JsonDict] = field(default_factory=list)
    extra: JsonDict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DryRunReport":
        known = {
            "generated_at",
            "input",
            "summary",
            "proposed_changes",
            "rows_not_found",
            "name_mismatches",
            "review_needed",
            "unmapped_items",
            "skipped_low_confidence_changes",
        }
        raw_changes = _optional_list(data, "proposed_changes")
        changes = [
            ProposedChange.from_mapping(change)
            for change in raw_changes
            if isinstance(change, Mapping)
        ]
        if len(changes) != len(raw_changes):
            raise SchemaError("proposed_changes must contain only objects")

        return cls(
            generated_at=_require_str(data, "generated_at"),
            input=_optional_dict(data, "input"),
            summary=_optional_dict(data, "summary"),
            proposed_changes=changes,
            rows_not_found=list(_optional_list(data, "rows_not_found")),
            name_mismatches=list(_optional_list(data, "name_mismatches")),
            review_needed=list(_optional_list(data, "review_needed")),
            unmapped_items=list(_optional_list(data, "unmapped_items")),
            skipped_low_confidence_changes=list(_optional_list(data, "skipped_low_confidence_changes")),
            extra=_extra(data, known),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "DryRunReport":
        return cls.from_mapping(load_json(path))
