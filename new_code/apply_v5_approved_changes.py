import json
import shutil
from copy import copy
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font


BASE = Path(r"D:\ying_min_mineru")
V4_XLSX = BASE / "英名录25版-祁县-二审_v4.xlsx"
V5_XLSX = BASE / "英名录25版-祁县-二审_v5.xlsx"
DRY_RUN_JSON = BASE / "log" / "20260630_v5_dry_run_report.json"
APPLY_REPORT = BASE / "log" / "20260701_v5_apply_report.json"

RED = "FFFF0000"
SKIP_CODES = {
    "晋祁县000601",  # 宋儒哲：用户要求先不管
}


def cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def set_red(cell):
    old = copy(cell.font)
    cell.font = Font(
        name=old.name or "Calibri",
        size=old.sz or 11,
        bold=old.bold,
        italic=old.italic,
        vertAlign=old.vertAlign,
        underline=old.underline,
        strike=old.strike,
        color=RED,
    )


def main():
    report = json.loads(DRY_RUN_JSON.read_text(encoding="utf-8"))
    changes = [change for change in report["proposed_changes"] if change["code"] not in SKIP_CODES]

    if V5_XLSX.exists():
        V5_XLSX.unlink()
    shutil.copy2(V4_XLSX, V5_XLSX)

    wb = openpyxl.load_workbook(V5_XLSX)
    ws = wb.active

    applied = []
    skipped = []
    for change in changes:
        row = int(change["row"])
        col = int(change["column"])
        cell = ws.cell(row, col)
        current = cell_text(cell.value)
        expected_old = cell_text(change["old"])
        if current != expected_old:
            skipped.append(
                {
                    **change,
                    "current": current,
                    "skip_reason": "current_value_differs_from_dry_run_old_value",
                }
            )
            continue
        cell.value = change["new"]
        set_red(cell)
        applied.append(change)

    wb.save(V5_XLSX)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(V4_XLSX),
        "output": str(V5_XLSX),
        "dry_run": str(DRY_RUN_JSON),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "skipped_codes": sorted(SKIP_CODES),
        "applied": applied,
        "skipped": skipped,
    }
    APPLY_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"output: {V5_XLSX}")
    print(f"report: {APPLY_REPORT}")
    print(json.dumps({"applied_count": len(applied), "skipped_count": len(skipped)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
