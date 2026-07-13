# Excel Dry Run / Apply

本流水线读取 `correction_records.json`，以调用方显式传入的 v4 Excel 为可信基线生成 dry-run 报告。只有列入 `approved_changes.json` 且通过依赖检查的变更才能写入候选 Excel。

## 安全边界

- 当前可信基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物，不能作为默认基线。
- 不默认读取 `data/private/` 中的真实 Excel。
- 不覆盖输入 Excel，apply 必须写入调用方指定的新文件。
- apply 必须提供 `approved_changes.json`。
- 不修改 `old_code/` 和 `new_code/`。
- 不提交 `data/` 产物。

## 列规则

- B 列：编号匹配。
- D 列：姓名精确校验。
- F 列：籍贯。
- G 列：出生时间。
- H 列：参加革命/工作时间。
- I 列：政治面貌。
- J 列：生前单位及曾任职务，尽量规范为 `单位/职务`。
- K 列：牺牲时间、地点及简要事迹候选。
- N 列：审稿意见，保留旧意见并追加新意见。
- T 列：K 列修改前的备份。
- apply 后修改的单元格使用红字。

## K/T 备份状态

`classify_story_backup(old_story, existing_backup)` 将每行分为四种状态：

- `no_backup_needed`：旧 K 为空，可以提出 K，不提出 T。
- `backup_required`：旧 K 非空且 T 为空；先提出 T = 旧 K，再提出依赖该 T 变更的 K。
- `backup_verified`：T 与当前旧 K 可比相等，说明已备份；只提出 K。
- `backup_conflict`：T 非空但不等于当前旧 K；保留 T，不提出可批准的 K。

`backup_conflict` 下的 K 候选不会丢失，而是进入 `blocked_changes`。阻断项包含旧值、新值、阻断原因、候选长度和 warnings，仅用于人工审查，不能进入 apply。

## Apply 依赖

当旧 K 非空且 T 为空时，K change 的 `requires` 包含对应 T change ID。apply 不依赖审批人员手工保证顺序：

- T 未获批准：K 跳过并记录 `required_change_not_approved`。
- T 因当前值与 dry-run 不一致等原因未应用：K 跳过并记录 `required_change_not_applied`。
- 只有 T 成功应用后，K 才能应用。

已有 T 永远不会被覆盖。该规则避免丢失可能来自 v3 到 v4 过程的历史 K 备份。

## 长故事候选

K 候选超过 40 字时添加 `story_candidate_long`，并在 JSON/Markdown 中记录 `story_length`。系统只警告，不截断、不摘要、不自动改写。

如果 K 因 `story_backup_conflict` 被阻断，且该记录没有其他安全业务字段或需要写入 N 的安葬地、民族信息，dry-run 不会仅因 warnings 生成 N-only 变更。warnings 仍保留在记录结果和阻断报告中。

## CLI

生成 dry-run：

```powershell
lieshi-ocr excel-dry-run `
  --base-xlsx "path\to\v4.xlsx" `
  --records "data\work\20260626\review\correction_records.json" `
  --out-dir "data\work\20260626\excel"
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

应用已批准变更：

```powershell
lieshi-ocr excel-apply `
  --base-xlsx "path\to\v4.xlsx" `
  --dry-run "data\work\20260626\excel\dry_run_report.json" `
  --approved "approved_changes.json" `
  --out-xlsx "data\output\20260626\candidate.xlsx"
```

## 验证

```powershell
python -m compileall src old_code new_code _archive
python -m unittest discover -s tests
lieshi-ocr excel-dry-run --help
lieshi-ocr excel-apply --help
git diff --check
```
