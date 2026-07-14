"""Parse correction text into conservative review fields."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .normalize import normalize_field_name, normalize_text

DATE_PATTERN = r"\d{4}\s*\u5e74(?:\s*\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*\u65e5)?)?"

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
    "性别",
]

_FIELD_PATTERN = re.compile(r"(?P<label>[\u4e00-\u9fff/、]+)\s*:\s*")


FIELD_SACRIFICE_TIME = "牺牲时间"
FIELD_SACRIFICE_PLACE = "牺牲地点"
FIELD_SACRIFICE_REASON = "牺牲原因"
FIELD_STORY = "事迹"
FIELD_BURIAL = "安葬地"


@dataclass(frozen=True)
class CorrectionItem:
    raw_label: str
    field: str
    value: str
    reason: str
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "raw_label": self.raw_label,
            "field": self.field,
            "value": self.value,
            "reason": self.reason,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class ParseResult:
    fields: dict[str, str]
    normalized_text: str
    items: list[CorrectionItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "fields": self.fields,
            "normalized_text": self.normalized_text,
            "items": [item.to_json() for item in self.items],
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
    items, item_warnings = _parse_completion_items(text, fields)
    warnings.extend(item_warnings)
    if items:
        return ParseResult(fields=fields, normalized_text=normalized, items=items, warnings=warnings)

    matches = list(_FIELD_PATTERN.finditer(normalized))

    recognized: list[tuple[str, int, int]] = []
    for match in matches:
        label = normalize_field_name(match.group("label"))
        if label in fields:
            recognized.append((label, match.start(), match.end()))

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

    if normalized and not recognized:
        fields, warnings = _parse_unlabeled_text(normalized, fields, warnings)

    return ParseResult(fields=fields, normalized_text=normalized, warnings=warnings)


_COMPLETION_START = re.compile(r"(?m)^(?P<label>[^\n]{1,48}?)\s*补充完善为")


def _parse_completion_items(text: str, fields: dict[str, str]) -> tuple[list[CorrectionItem], list[str]]:
    line_text = text.replace("\r\n", "\n").replace("\r", "\n")
    starts = list(_COMPLETION_START.finditer(line_text))
    if not starts:
        return [], []

    items: list[CorrectionItem] = []
    warnings: list[str] = []
    for index, match in enumerate(starts):
        raw_label = _clean_completion_label(match.group("label"))
        canonical = normalize_field_name(raw_label)
        chunk_end = starts[index + 1].start() if index + 1 < len(starts) else len(line_text)
        chunk = line_text[match.end():chunk_end]
        value, reason, item_warnings = _split_completion_value_reason(chunk)
        if canonical != raw_label:
            item_warnings.append(f"field_label_normalized:{raw_label}->{canonical}")
        if canonical not in fields:
            reason_field = _field_from_reason(reason)
            if reason_field:
                canonical = reason_field
                field_name = canonical
                item_warnings.append(f"field_inferred_from_reason:{canonical}")
                warnings.append(f"field_inferred_from_reason:{canonical}")
                if not value:
                    item_warnings.append("empty_value")
                    warnings.append(f"{canonical}:empty_value")
                elif fields[canonical] and fields[canonical] != value:
                    item_warnings.append("multiple_values")
                    warnings.append(f"{canonical}:multiple_values")
                    fields[canonical] = f"{fields[canonical]} | {value}"
                else:
                    fields[canonical] = value
            else:
                item_warnings.append("unrecognized_correction_field")
                warnings.append(f"unrecognized_correction_field:{raw_label}")
                field_name = ""
        else:
            field_name = canonical
            if not value:
                item_warnings.append("empty_value")
                warnings.append(f"{canonical}:empty_value")
            elif fields[canonical] and fields[canonical] != value:
                item_warnings.append("multiple_values")
                warnings.append(f"{canonical}:multiple_values")
                fields[canonical] = f"{fields[canonical]} | {value}"
            else:
                fields[canonical] = value
        items.append(
            CorrectionItem(
                raw_label=raw_label,
                field=field_name,
                value=value,
                reason=reason,
                warnings=_dedupe(item_warnings),
            )
        )
    if items:
        warnings.append("structured_correction_items_parsed")
    return items, _dedupe(warnings)


def _clean_completion_label(value: str) -> str:
    value = re.sub(r"^[\s•·|丨\d.、]+", "", value)
    return re.sub(r"\s+", "", value).strip(" ;；,，。")


def _split_completion_value_reason(chunk: str) -> tuple[str, str, list[str]]:
    normalized = re.sub(r"[ \t\u3000]+", " ", chunk).strip()
    reason_match = re.search(r"理由\s*[:：]", normalized)
    warnings: list[str] = []
    if reason_match:
        value_text = normalized[:reason_match.start()]
        reason_text = normalized[reason_match.end():]
    else:
        value_text = normalized
        reason_text = ""
        warnings.append("reason_marker_missing")
    value = _clean_quoted_value(value_text)
    reason = _clean_value(reason_text)
    return value, reason, warnings


def _clean_quoted_value(value: str) -> str:
    value = _clean_value(value)
    value = value.strip('“”"\'')
    return value.strip(" ;；,，。")


def _field_from_reason(reason: str) -> str:
    compact = re.sub(r"\s+", "", reason)
    hints = {
        "籍贯": ("原籍贯",),
        "出生时间": ("原出生时间",),
        "参加革命/工作时间": ("原参加革命", "原参加工作"),
        "政治面貌": ("原政治面貌",),
        "民族": ("原民族",),
        "生前单位及曾任职务": ("原生前", "原单位及职务"),
        "曾任职务": ("原曾任职务",),
        "牺牲时间": ("原牺牲时间",),
        "牺牲地点": ("原牺牲地点",),
        "牺牲原因": ("原牺牲原因",),
        "事迹": ("原事迹",),
        "安葬地": ("原安葬地",),
    }
    matched = [
        field_name
        for field_name, needles in hints.items()
        if any(needle in compact for needle in needles)
    ]
    return matched[0] if len(matched) == 1 else ""


def _parse_unlabeled_text(text: str, fields: dict[str, str], warnings: list[str]) -> tuple[dict[str, str], list[str]]:
    inferred: list[str] = []
    dates = _date_candidates(text)
    if len(dates) > 1:
        warnings.append("multiple_date_candidates")

    sacrifice = _find_sacrifice_clause(text)
    if sacrifice:
        if len(dates) <= 1 and sacrifice.get("time"):
            fields[FIELD_SACRIFICE_TIME] = sacrifice["time"]
            warnings.append("sacrifice_time_inferred")
            inferred.append(FIELD_SACRIFICE_TIME)
        if sacrifice.get("place"):
            fields[FIELD_SACRIFICE_PLACE] = sacrifice["place"]
            warnings.append("sacrifice_place_inferred")
            inferred.append(FIELD_SACRIFICE_PLACE)
        if sacrifice.get("reason"):
            fields[FIELD_SACRIFICE_REASON] = sacrifice["reason"]
            warnings.append("sacrifice_reason_inferred")
            inferred.append(FIELD_SACRIFICE_REASON)
        if sacrifice.get("story"):
            fields[FIELD_STORY] = sacrifice["story"]
            warnings.append("brief_deed_from_unlabeled_text")
            inferred.append(FIELD_STORY)

    burial = _find_burial_place(text)
    if burial:
        fields[FIELD_BURIAL] = burial
        warnings.append("burial_place_inferred")
        inferred.append(FIELD_BURIAL)

    if inferred:
        warnings.append("unlabeled_text_parsed")
        warnings.append("needs_human_review")
    else:
        warnings.append("no_labeled_fields_found")
    return fields, warnings


def _date_candidates(text: str) -> list[str]:
    dates = [_compact_date(match.group(0)) for match in re.finditer(DATE_PATTERN, text)]
    return _dedupe(dates)


def _find_sacrifice_clause(text: str) -> dict[str, str]:
    sentence = _first_sentence_with(text, "\u727a\u7272")
    if not sentence:
        return {}

    time = ""
    date_match = re.search(DATE_PATTERN, sentence)
    if date_match:
        time = _compact_date(date_match.group(0))

    place = _extract_sacrifice_place(sentence, date_match.end() if date_match else 0)
    reason = _extract_sacrifice_reason(sentence)
    story = _clean_value(sentence)
    return {"time": time, "place": place, "reason": reason, "story": story}


def _extract_sacrifice_place(sentence: str, start: int) -> str:
    tail = sentence[start:]
    patterns = [
        r"(?:\u727a\u7272\u4e8e|\u727a\u7272\u5728)(?P<place>[^，。；;\n]{1,30})",
        r"(?:\u4e8e|\u5728)(?P<place>[^，。；;\n]{1,30}?)(?:\u6218\u6597|\u4f5c\u6218|\u6597\u4e89|\u6267\u884c\u4efb\u52a1|\u53cd\u626b\u8361|\u7a81\u56f4|\u6218\u5f79)?\u4e2d?\u727a\u7272",
    ]
    for pattern in patterns:
        match = re.search(pattern, tail)
        if match:
            return _clean_place(match.group("place"))
    return ""


def _extract_sacrifice_reason(sentence: str) -> str:
    match = re.search(r"\u56e0(?P<reason>[^，。；;\n]{1,30}?)\u727a\u7272", sentence)
    if match:
        return _clean_value(match.group("reason"))
    match = re.search(r"(?P<reason>\u6218\u6597|\u4f5c\u6218|\u6597\u4e89|\u6267\u884c\u4efb\u52a1|\u53cd\u626b\u8361|\u7a81\u56f4|\u6218\u5f79)\u4e2d?\u727a\u7272", sentence)
    if match:
        return _clean_value(match.group("reason"))
    return ""


def _find_burial_place(text: str) -> str:
    match = re.search(r"(?:\u5b89\u846c\u4e8e|\u5b89\u846c\u5728|\u846c\u4e8e)(?P<place>[^，。；;\n]{1,40})", text)
    if not match:
        return ""
    return _clean_place(match.group("place"))


def _first_sentence_with(text: str, needle: str) -> str:
    for sentence in re.split(r"[。；;\n]+", text):
        if needle in sentence:
            return sentence.strip()
    return ""


def _clean_place(value: str) -> str:
    value = _clean_value(value)
    value = re.sub(r"(?:\u6218\u6597|\u4f5c\u6218|\u6597\u4e89|\u6267\u884c\u4efb\u52a1|\u53cd\u626b\u8361|\u7a81\u56f4|\u6218\u5f79)?\u4e2d?$", "", value)
    return value.strip(" ,，。；;")


def _compact_date(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _clean_value(value: str) -> str:
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ;；,，。")
