"""Parse correction text into conservative review fields."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .normalize import normalize_field_name, normalize_text

FIELD_NAMES = [
    "编号",
    "姓名",
    "籍贯",
    "出生时间",
    "参加革命/工作时间",
    "政治面貌",
    "民族",
    "生前单位及曾任职务",
    "曾任职务",
    "牺牲时间",
    "牺牲地点",
    "牺牲原因",
    "事迹",
    "安葬地",
]

_FIELD_PATTERN = re.compile(r"(?P<label>[\u4e00-\u9fff/、]+)\s*:\s*")


@dataclass(frozen=True)
class ParseResult:
    fields: dict[str, str]
    normalized_text: str
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "fields": self.fields,
            "normalized_text": self.normalized_text,
            "warnings": self.warnings,
        }


def empty_fields() -> dict[str, str]:
    return {name: "" for name in FIELD_NAMES}


def parse_correction_text(text: str) -> ParseResult:
    """Extract explicitly labelled fields from correction text.

    The parser is intentionally conservative: values are only extracted when a
    recognized field label is present. Ambiguous or repeated labels become
    warnings instead of inferred data.
    """

    normalized = normalize_text(text)
    fields = empty_fields()
    warnings: list[str] = []
    matches = list(_FIELD_PATTERN.finditer(normalized))

    recognized: list[tuple[str, int, int]] = []
    for match in matches:
        label = normalize_field_name(match.group("label"))
        if label in fields:
            recognized.append((label, match.start(), match.end()))

    if normalized and not recognized:
        warnings.append("no_labeled_fields_found")

    for index, (label, _start, value_start) in enumerate(recognized):
        value_end = recognized[index + 1][1] if index + 1 < len(recognized) else len(normalized)
        value = _clean_value(normalized[value_start:value_end])
        if not value:
            warnings.append(f"{label}:empty_value")
            continue
        if fields[label] and fields[label] != value:
            warnings.append(f"{label}:multiple_values")
            fields[label] = f"{fields[label]} | {value}"
            continue
        fields[label] = value

    return ParseResult(fields=fields, normalized_text=normalized, warnings=warnings)


def _clean_value(value: str) -> str:
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ;；,，。")
