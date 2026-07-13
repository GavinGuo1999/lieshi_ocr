# Story Candidate Audit

`audit-story` 生成只读的事迹候选 JSON/HTML 报告，帮助人工归纳 K 列简写规则。本工具不修改 Excel、不自动缩短候选，也不决定 T 列的长期历史存储方案。

日常逐条审核优先使用 `audit-story-xlsx` 生成的 Excel 工作簿。HTML 保留为开发诊断工具，不是人工审稿的必需步骤。

## 安全边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 必须显式传入 v4、`correction_records.json` 和 `dry_run_report.json`。
- 工作簿以只读审计方式打开，不保存、不覆盖。
- HTML/JSON 可能包含真实姓名和事迹，只能写入已忽略的 `data/work/{batch}/`，不得提交 Git。
- 人工意见默认保存在浏览器 `localStorage`，不会回写报告 JSON、Excel 或源数据。
- 正式审查前应先确认导出/导入功能可用，并定期把意见导出为本地 JSON 备份。

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

## Excel 人工审核

生成审核工作簿：

```powershell
lieshi-ocr audit-story-xlsx `
  --base-xlsx "data/private/baselines/英名录25版-祁县-二审_v4.xlsx" `
  --records "data/work/20260626/review/correction_records.json" `
  --dry-run "data/work/20260626/excel/dry_run_report.json" `
  --out-xlsx "data/work/20260626/story_audit/事迹候选人工审核.xlsx"
```

工作簿包含：

- `人工审核`：当前 K/T、系统候选、日期、地点、原因、warnings 和审核输入列。
- `原始正文`：完整 MinerU 正文、来源路径和 warnings。
- `使用说明`：审核步骤和敏感数据边界。
- `_审核元数据`：veryHidden 校验表，用于发现编号、姓名或系统候选被误改。

只编辑 `人工审核` 的三列：

- `审核结论`
- `建议最终K`
- `人工备注`

审核结论下拉选项：

- `通过系统候选`
- `需要改写`
- `信息不足`
- `原文疑似错误`
- `暂不处理`

工作表保护只用于防误操作，不是安全加密。审核工作簿包含真实个人信息，必须保存在被 Git 忽略的 `data/` 目录。

收集审核结果：

```powershell
lieshi-ocr collect-story-review `
  --review-xlsx "data/work/20260626/story_audit/事迹候选人工审核.xlsx" `
  --out-json "data/work/20260626/story_audit/story_review_decisions.json"
```

收集规则：

- `通过系统候选`：最终 K 使用未被修改的系统候选 K。
- `需要改写`：`建议最终K` 必填。
- `信息不足`、`原文疑似错误`、`暂不处理`：记录决定，但不生成可审批 K。
- 编号、姓名或系统候选与隐藏元数据不一致时拒绝收集。
- 内容审核通过不会解除 `story_backup_conflict`；决定 JSON 会保留候选状态，并标记 `requires_backup_resolution`。
- 只输出审核决定 JSON，不修改 v4/v5，不执行 `excel-apply`。

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

## 人工意见备份

报告顶部显示 `已审 x/总数`，非空意见会实时计数。提供三个本地操作：

- `导出意见 JSON`：下载 `story_review_opinions.json`，包含格式版本、导出时间、记录数和按审计 key 保存的意见。
- `导入意见 JSON`：只接受本工具导出的版本 1 JSON，只导入当前报告中能够匹配的字符串意见。
- `清空意见`：清空前弹出不可撤销确认，并提醒先导出备份。

导出文件可能包含人工整理后的真实个人信息，仍属于敏感本地产物。应保存在 `data/private/` 或其他不进入 Git 的本地目录，不得公开或提交。

`localStorage` 按 origin 隔离。更换协议、主机或端口后，原意见不会自动出现在新 origin；此时使用导出的 JSON 恢复。正式审查期间建议固定使用同一个 loopback 地址和端口。

推荐每条意见使用以下结构：

```text
结论：接受 / 需改写 / 信息不足 / 原文疑似错误

牺牲时间：
- 选择：
- 粒度：年月日 / 年月 / 年 / 不确定
- 依据：

牺牲地点：
- 建议保留：
- 保留层级：

牺牲原因：
- 建议表述：

事迹：
- 应保留的核心动作：
- 应删除的冗余内容：

建议最终 K：

规则标签：多日期 / 地点过细 / 原因不明 / OCR错字 / 原文信息冲突 / 其他
```

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
