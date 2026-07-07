"""Conservative OCR text normalization for field parsing."""

from __future__ import annotations

import re

FIELD_ALIASES = {
    "栖牲原因": "牺牲原因",
    "牺牲原困": "牺牲原因",
    "参加革命时间": "参加革命/工作时间",
    "参加工作时间": "参加革命/工作时间",
    "参加革命工作时间": "参加革命/工作时间",
    "参加革命、工作时间": "参加革命/工作时间",
    "生前单位及职务": "生前单位及曾任职务",
    "单位及职务": "生前单位及曾任职务",
}


def normalize_field_name(name: str) -> str:
    compact = re.sub(r"\s+", "", name.strip())
    return FIELD_ALIASES.get(compact, compact)


def normalize_text(text: str) -> str:
    """Normalize spacing and known field-label OCR noise without guessing values."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("：", ":")
    normalized = re.sub(r"[ \t\u3000]+", " ", normalized)
    normalized = re.sub(r" *: *", ": ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    normalized = _normalize_known_labels(normalized)
    return _merge_continuation_lines(normalized)


def _normalize_known_labels(text: str) -> str:
    for alias, canonical in FIELD_ALIASES.items():
        pattern = re.compile(rf"(?<!\S){re.escape(alias)}\s*:")
        text = pattern.sub(f"{canonical}:", text)
    return text


def _merge_continuation_lines(text: str) -> str:
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    merged: list[str] = []
    for line in lines:
        if _looks_like_field_start(line) or not merged:
            merged.append(line)
        else:
            previous = merged[-1]
            separator = "" if _ends_with_cjk(previous) or _starts_with_cjk(line) else " "
            merged[-1] = f"{previous}{separator}{line}"
    return "\n".join(merged)


def _looks_like_field_start(line: str) -> bool:
    label = line.split(":", 1)[0]
    return normalize_field_name(label) in {
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
    }


def _ends_with_cjk(text: str) -> bool:
    return bool(text and "\u4e00" <= text[-1] <= "\u9fff")


def _starts_with_cjk(text: str) -> bool:
    return bool(text and "\u4e00" <= text[0] <= "\u9fff")
