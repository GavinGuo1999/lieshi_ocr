# Excel Dry Run / Apply

本流水线读取 `correction_records.json`，以调用方显式传入的 v4 Excel 为基线，生成 dry-run 报告；只有审批后的 change 才能 apply 到候选 Excel。

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物，不能作为默认基线。
- 不默认读取 `data/private/` 中的真实 Excel。
- 不覆盖输入 Excel。
- apply 必须提供 `approved_changes.json`。
- 不修改 `old_code/` 和 `new_code/`。
- 不提交 `data/` 产物。

## 列规则

- B 列：编号匹配。
- D 列：姓名校验。
- F 列：籍贯。
- G 列：出生时间。
- H 列：参加革命/工作时间。
- I 列：政治面貌。
- J 列：生前单位及曾任职务，尽量规范为 `单位/职务`。
- K 列：牺牲时间地点简要事迹，短写。
- N 列：审稿意见。
- T 列：备份旧 K。
- apply 后修改单元格使用红字。

## CLI

```powershell
python -m lieshi_ocr.cli excel-dry-run --base-xlsx path\to\v4.xlsx --records data/work/20260626/review/correction_records.json --out-dir data/work/20260626/excel
```

审批文件示例：

```json
{
  "approved_changes": [
    "QX-0001:F2",
    {"id": "QX-0001:K2", "approved": true}
  ]
}
```

应用审批：

```powershell
python -m lieshi_ocr.cli excel-apply --base-xlsx path\to\v4.xlsx --dry-run data/work/20260626/excel/dry_run_report.json --approved approved_changes.json --out-xlsx data/output/20260626/candidate.xlsx
```
