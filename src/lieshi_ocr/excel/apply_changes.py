"""Apply approved dry-run changes to a candidate workbook."""

from __future__ import annotations

from copy import copy
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

import openpyxl
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
    approved_ids = _load_approved_ids(approved_path)
    changes_by_id = {
        str(change.get("id")): change
        for change in dry_run.get("proposed_changes", [])
        if isinstance(change, dict) and change.get("id")
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base, output)
    workbook = openpyxl.load_workbook(output)
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
                cell.value = change.get("new", "")
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
