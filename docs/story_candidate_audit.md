# Story Candidate Audit

`audit-story` 生成只读的事迹候选 JSON/HTML 报告，帮助人工归纳 K 列简写规则。本工具不修改 Excel、不自动缩短候选，也不决定 T 列的长期历史存储方案。

## 安全边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 必须显式传入 v4、`correction_records.json` 和 `dry_run_report.json`。
- 工作簿以只读审计方式打开，不保存、不覆盖。
- HTML/JSON 可能包含真实姓名和事迹，只能写入已忽略的 `data/work/{batch}/`，不得提交 Git。
- 人工意见只保存在浏览器 `localStorage`，不会回写 JSON、Excel 或源数据。

## 命令

先生成受备份安全规则保护的 dry-run：

```powershell
lieshi-ocr excel-dry-run `
  --base-xlsx "data/private/baselines/英名录25版-祁县-二审_v4.xlsx" `
  --records "data/work/20260626/review/correction_records.json" `
  --out-dir "data/work/20260626/excel"
```

再生成事迹候选审计报告：

```powershell
lieshi-ocr audit-story `
  --records "data/work/20260626/review/correction_records.json" `
  --dry-run "data/work/20260626/excel/dry_run_report.json" `
  --base-xlsx "data/private/baselines/英名录25版-祁县-二审_v4.xlsx" `
  --out-dir "data/work/20260626/story_audit"
```

输出：

```text
data/work/20260626/story_audit/story_candidate_audit.json
data/work/20260626/story_audit/story_candidate_audit.html
```

## 报告内容

每条记录并排展示：

- 当前 v4 K。
- 当前 v4 T。
- dry-run 中的 proposed 或 blocked K 候选。
- 候选长度与 `story_candidate_long`。
- MinerU 原文及原文文件链接。
- 原文中检测到的所有日期，不替用户选择日期。
- parser 给出的牺牲时间、地点、原因和事迹候选。
- `story_backup_conflict`、`multiple_date_candidates`、`needs_human_review` 等 warnings。
- 浏览器本地保存的人工意见输入框。

`blocked_changes` 只用于审计，报告不会把它转换成可审批变更。候选超过 40 字仍完整显示，不截断、不摘要。

## 人工审查建议

逐条记录以下判断，再归纳规则：

1. 牺牲时间应保留完整日期、年月还是年份。
2. 多日期中哪个日期有明确的牺牲语义，无法确定时保持 warning。
3. 地点保留到哪个行政或事件层级。
4. 牺牲原因如何统一表达，但不增加原文没有的信息。
5. 事迹只保留哪个明确动作或事件。
6. 候选是否可以进入后续 dry-run；本报告本身不执行批准。

## 本地查看

不要放宽 `file://` 安全策略。需要浏览器查看时，只绑定 loopback：

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory D:\Projects\lieshi_ocr
```

打开：

```text
http://127.0.0.1:8765/data/work/20260626/story_audit/story_candidate_audit.html
```

检查结束后停止服务器。报告和截图均属于本地敏感产物，不得提交。
