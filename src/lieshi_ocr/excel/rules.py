"""Column mapping and conservative Excel update rules."""

from __future__ import annotations

import re

COL_CODE = 2
COL_NAME = 4
COL_ORIGIN = 6
COL_BIRTH = 7
COL_JOIN = 8
COL_POLITICAL = 9
COL_UNIT_ROLE = 10
COL_STORY = 11
COL_REVIEW = 14
COL_STORY_BACKUP = 20

RED_FONT = "FFFF0000"

TARGET_FIELDS = {
    "籍贯": COL_ORIGIN,
    "出生时间": COL_BIRTH,
    "参加革命/工作时间": COL_JOIN,
    "政治面貌": COL_POLITICAL,
    "生前单位及曾任职务": COL_UNIT_ROLE,
}

COLUMN_LABELS = {
    COL_CODE: "编号",
    COL_NAME: "姓名",
    COL_ORIGIN: "籍贯",
    COL_BIRTH: "出生时间",
    COL_JOIN: "参加革命/工作时间",
    COL_POLITICAL: "政治面貌",
    COL_UNIT_ROLE: "生前单位及曾任职务",
    COL_STORY: "牺牲时间地点简要事迹",
    COL_REVIEW: "审稿意见",
    COL_STORY_BACKUP: "旧K备份",
}


def cell_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def comparable(value: object) -> str:
    text = cell_text(value)
    text = text.replace("：", ":").replace("，", ",").replace("；", ";").replace("。", "")
    return re.sub(r"\s+", "", text)


def normalize_unit_role(unit_role: str, role: str = "") -> str:
    unit = cell_text(unit_role).strip("/ ")
    role = cell_text(role).strip("/ ")
    if unit and role and "/" not in unit:
        return f"{unit}/{role}"
    return unit or role


def build_story(fields: dict[str, str]) -> str:
    sacrifice_time = cell_text(fields.get("牺牲时间"))
    sacrifice_place = cell_text(fields.get("牺牲地点"))
    sacrifice_reason = cell_text(fields.get("牺牲原因"))
    story = cell_text(fields.get("事迹"))

    parts: list[str] = []
    if sacrifice_time:
        parts.append(sacrifice_time)
    if sacrifice_place:
        parts.append(f"在{sacrifice_place}")
    if sacrifice_reason:
        parts.append(sacrifice_reason)
    if parts:
        sentence = "".join(parts)
    else:
        sentence = story
    return _ensure_period(sentence)


def build_review_note(record_warnings: list[str], record_fields: dict[str, str]) -> str:
    notes: list[str] = []
    if record_warnings:
        notes.append("需人工复核: " + ", ".join(record_warnings))
    burial = cell_text(record_fields.get("安葬地"))
    ethnicity = cell_text(record_fields.get("民族"))
    if burial:
        notes.append(f"安葬地: {burial}")
    if ethnicity:
        notes.append(f"民族: {ethnicity}")
    return "\n".join(notes)


def append_review_note(old_note: str, new_note: str) -> str:
    """Append review notes without overwriting or duplicating existing notes."""

    old = cell_text(old_note)
    new = cell_text(new_note)
    if not new:
        return old
    if not old:
        return new
    if new in old:
        return old
    return f"{old}\n{new}"


def _ensure_period(text: str) -> str:
    text = cell_text(text).strip("。；;，, ")
    if not text:
        return ""
    return text if text.endswith("。") else f"{text}。"
