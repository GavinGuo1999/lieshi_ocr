"""Apply approved dry-run changes to a candidate workbook."""

from __future__ import annotations

from copy import copy
from datetime import datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import shutil
from typing import Any

import openpyxl
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Font

from .rules import RED_FONT, cell_text

JsonDict = dict[str, Any]


def apply_approved_changes(
    base_xlsx: str | Path,
    dry_run_path: str | Path,
    approved_path: str | Path,
    out_xlsx: str | Path,
    apply_report_path: str | Path | None = None,
) -> JsonDict:
    """Copy base_xlsx to out_xlsx and apply only approved dry-run changes."""

    base = Path(base_xlsx)
    output = Path(out_xlsx)
    if base.resolve() == output.resolve():
        raise ValueError("out_xlsx must not be the same path as base_xlsx")

    dry_run = json.loads(Path(dry_run_path).read_text(encoding="utf-8"))
    profile = str(dry_run.get("profile", ""))
    approved_ids = _load_approved_ids(approved_path)
    changes_by_id = {
        str(change.get("id")): change
        for change in dry_run.get("proposed_changes", [])
        if isinstance(change, dict) and change.get("id")
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base, output)
    workbook = openpyxl.load_workbook(output, rich_text=True)
    sheet = workbook.active
    applied: list[JsonDict] = []
    skipped: list[JsonDict] = []
    applied_ids: set[str] = set()
    failed_ids: set[str] = set()

    try:
        remaining = set(approved_ids)
        while remaining:
            progress = False
            for change_id in sorted(remaining):
                change = changes_by_id.get(change_id)
                if change is None:
                    skipped.append({"id": change_id, "skip_reason": "approved_change_not_in_dry_run"})
                    failed_ids.add(change_id)
                    remaining.remove(change_id)
                    progress = True
                    break

                requires = _string_list(change.get("requires", []))
                not_approved = [required for required in requires if required not in approved_ids]
                if not_approved:
                    skipped.append(
                        {
                            **change,
                            "required": not_approved,
                            "skip_reason": "required_change_not_approved",
                        }
                    )
                    failed_ids.add(change_id)
                    remaining.remove(change_id)
                    progress = True
                    break

                unavailable = [
                    required
                    for required in requires
                    if required in failed_ids or required not in changes_by_id
                ]
                if unavailable:
                    skipped.append(
                        {
                            **change,
                            "required": unavailable,
                            "skip_reason": "required_change_not_applied",
                        }
                    )
                    failed_ids.add(change_id)
                    remaining.remove(change_id)
                    progress = True
                    break
                if any(required not in applied_ids for required in requires):
                    continue

                row = int(change["row"])
                column = int(change["column"])
                cell = sheet.cell(row, column)
                current = cell_text(cell.value)
                expected_old = cell_text(change.get("old"))
                if current != expected_old:
                    skipped.append(
                        {
                            **change,
                            "current": current,
                            "skip_reason": "current_value_differs_from_dry_run_old",
                        }
                    )
                    failed_ids.add(change_id)
                    remaining.remove(change_id)
                    progress = True
                    break
                new_value = cell_text(change.get("new"))
                if change.get("red_mode") == "partial":
                    _set_partial_red_value(cell, expected_old, new_value)
                else:
                    cell.value = new_value
                    _set_red_font(cell)
                applied.append(change)
                applied_ids.add(change_id)
                remaining.remove(change_id)
                progress = True
                break

            if not progress:
                for change_id in sorted(remaining):
                    change = changes_by_id.get(change_id, {"id": change_id})
                    skipped.append({**change, "skip_reason": "required_change_not_applied"})
                    failed_ids.add(change_id)
                remaining.clear()
        if profile == "v6_candidate":
            _apply_v6_story_layout(sheet, applied)
        workbook.save(output)
    finally:
        workbook.close()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_xlsx": base.as_posix(),
        "out_xlsx": output.as_posix(),
        "dry_run": Path(dry_run_path).as_posix(),
        "approved": Path(approved_path).as_posix(),
        "approved_count": len(approved_ids),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }
    if apply_report_path is not None:
        target = Path(apply_report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _load_approved_ids(path: str | Path) -> set[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_changes = payload.get("approved_changes", payload.get("changes", [])) if isinstance(payload, dict) else payload
    approved: set[str] = set()
    if not isinstance(raw_changes, list):
        return approved
    for item in raw_changes:
        if isinstance(item, str):
            approved.add(item)
        elif isinstance(item, dict) and item.get("approved", True):
            change_id = item.get("id")
            if change_id:
                approved.add(str(change_id))
    return approved


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _set_red_font(cell: Any) -> None:
    old = copy(cell.font)
    cell.font = Font(
        name=old.name,
        sz=old.sz,
        b=old.b,
        i=old.i,
        vertAlign=old.vertAlign,
        underline=old.underline,
        strike=old.strike,
        color=RED_FONT,
    )


def _set_partial_red_value(cell: Any, old_value: str, new_value: str) -> None:
    """Write new_value with only inserted/replaced runs colored red."""

    old_font = copy(cell.font)
    normal_font = _inline_font(old_font, color=copy(old_font.color))
    red_font = _inline_font(old_font, color=RED_FONT)
    changed = [False] * len(new_value)
    matcher = SequenceMatcher(a=old_value, b=new_value, autojunk=False)
    for tag, _old_start, _old_end, new_start, new_end in matcher.get_opcodes():
        if tag in {"insert", "replace"}:
            for index in range(new_start, new_end):
                changed[index] = True
        elif tag == "delete" and new_value:
            anchor = new_start if new_start < len(new_value) else len(new_value) - 1
            changed[anchor] = True

    blocks: list[TextBlock] = []
    start = 0
    while start < len(new_value):
        is_changed = changed[start]
        end = start + 1
        while end < len(new_value) and changed[end] == is_changed:
            end += 1
        text = new_value[start:end]
        font = red_font if is_changed else normal_font
        if blocks and blocks[-1].font == font:
            blocks[-1].text += text
        else:
            blocks.append(TextBlock(font, text))
        start = end
    if not blocks:
        cell.value = new_value
        _set_red_font(cell)
        return
    cell.value = CellRichText(blocks)


def _inline_font(font: Font, color: Any) -> InlineFont:
    return InlineFont(
        rFont=font.name,
        charset=font.charset,
        family=font.family,
        b=font.b,
        i=font.i,
        strike=font.strike,
        outline=font.outline,
        shadow=font.shadow,
        condense=font.condense,
        extend=font.extend,
        color=color,
        sz=font.sz,
        u=font.u,
        vertAlign=font.vertAlign,
        scheme=font.scheme,
    )


def _apply_v6_story_layout(sheet: Any, applied: list[JsonDict]) -> None:
    story_rows = {int(change["row"]) for change in applied if int(change.get("column", 0)) == 11}
    for row in story_rows:
        current = sheet.row_dimensions[row].height or 0
        sheet.row_dimensions[row].height = max(current, 50.1)
    current_width = sheet.column_dimensions["K"].width or 0
    sheet.column_dimensions["K"].width = max(current_width, 57.25)
