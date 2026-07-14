"""Formatting rules for the reviewed v6 candidate workbook."""

from __future__ import annotations

import re

from .rules import cell_text

TOWNS = ["昭馀镇", "古县镇", "峪口乡", "来远镇", "东观镇", "贾令镇", "城赵镇", "西六支乡", "麓台城区", "城区"]

ROLE_SUFFIXES = [
    "地下工作人员",
    "一般工作人员",
    "工作人员",
    "民兵指导员",
    "武委会副主任",
    "财粮主任",
    "财政主任",
    "副村长",
    "副主任",
    "副科长",
    "副部长",
    "副连长",
    "副排长",
    "副班长",
    "指导员",
    "通讯员",
    "通信员",
    "交通员",
    "情报员",
    "宣传员",
    "管理员",
    "采购员",
    "工作员",
    "看护员",
    "卫生员",
    "侦察员",
    "炊事员",
    "中医师",
    "司号员",
    "小队长",
    "大队长",
    "支队长",
    "书记",
    "主任",
    "科长",
    "区长",
    "部长",
    "连长",
    "排长",
    "班长",
    "队长",
    "村长",
    "处长",
    "干部",
    "战士",
    "队员",
    "民工",
    "民兵",
    "团员",
    "参谋",
    "文书",
    "医师",
    "村民",
]

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_v6_date(value: object) -> str | None:
    """Return the agreed unpadded date text, or None when it is ambiguous."""

    text = cell_text(value).translate(_FULLWIDTH_DIGITS)
    text = re.sub(r"\s+", "", text)
    if not text:
        return ""
    if text == "0":
        return "0"

    patterns = (
        (r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})日?", 3),
        (r"(\d{4})[年./-](\d{1,2})月?", 2),
        (r"(\d{4})年?", 1),
    )
    for pattern, parts in patterns:
        match = re.fullmatch(pattern, text)
        if not match:
            continue
        values = [str(int(part)) for part in match.groups()[:parts]]
        if parts >= 2 and not 1 <= int(values[1]) <= 12:
            return None
        if parts == 3 and not 1 <= int(values[2]) <= 31:
            return None
        return "-".join(values)

    before = re.fullmatch(r"(\d{4})年?前", text)
    if before:
        return f"{before.group(1)}-前"
    return None


def format_v6_origin(value: object) -> str:
    """Format Qixian origins like the trusted v4 and reviewed Jia workbook."""

    text = re.sub(r"\s+", "", cell_text(value))
    if not text:
        return ""
    prefix = "山西省晋中市祁县"
    if not text.startswith(prefix):
        return text
    rest = text[len(prefix):].strip("- ")
    if not rest:
        return prefix
    for town in sorted(TOWNS, key=len, reverse=True):
        if rest.startswith(town):
            village = rest[len(town):].strip("- ")
            return f"{prefix}\n{town}-{village}" if village else f"{prefix}\n{town}"
    return f"{prefix}\n{rest}"


def format_v6_unit_role(value: object) -> str:
    """Add the v4 unit/role separator without rewriting OCR business text."""

    text = re.sub(r"\s+", "", cell_text(value)).strip("/ ")
    if not text or "/" in text:
        return text
    parenthesized = re.fullmatch(r"(.+?)[(（]([^()（）]+)[)）]", text)
    if parenthesized:
        return f"{parenthesized.group(1).strip()}/{parenthesized.group(2).strip()}"
    for role in sorted(ROLE_SUFFIXES, key=len, reverse=True):
        if text.endswith(role) and len(text) > len(role):
            return f"{text[:-len(role)].strip()}/{role}"
    return text


def format_v6_story(value: object) -> str:
    """Keep the complete reviewed story while normalizing layout punctuation."""

    text = re.sub(r"\s+", "", cell_text(value))
    text = text.replace(",", "，").replace(";", "；")
    text = text.strip("，；。 ")
    return f"{text}。" if text else ""
