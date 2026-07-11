# Parse/Review Manifest

本流水线读取 `text_manifest.json`，输出适合人工复核的结构化结果，不读写 Excel。

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 本轮只解析文本并生成审核材料，不写 Excel。
- 不修改 `old_code/` 和 `new_code/`。
- 不调用 OCR、MinerU、OpenCV 或 PDF 处理。
- 不提交 `data/` 产物。

## 输入输出

默认输入：

```text
data/work/{batch}/text/text_manifest.json
```

默认输出：

```text
data/work/{batch}/review/correction_records.json
data/work/{batch}/review/review_report.md
```

`correction_records.json` 每条记录包含：

- `batch`
- `source_pdf`
- `source_stem`
- `code`
- `name`
- `fields`
- `raw_text`
- `normalized_text`
- `regions`
- `warnings`

## 解析规则

- `code` 和 `name` 优先来自对应 region。
- correction 正文来自 `correction` region。
- 只解析明确字段标签，不从无标签正文中猜字段。
- `栖牲原因` 会归一为 `牺牲原因`。
- 多余空格、中文冒号和换行断裂会做轻量归一。
- 编号缺失、姓名缺失、字段冲突、重复字段等情况进入 `warnings`。

## CLI

## Unlabeled MinerU text

`parse_correction_text()` still prefers explicit labelled fields. When no
recognized label is present, it now performs a conservative unlabeled pass for
MinerU text:

- Only clear sacrifice and burial patterns are converted to review candidates.
- Multiple date candidates produce `multiple_date_candidates`; the parser does
  not force a sacrifice-time choice in that case.
- Inferred fields always add warnings such as `unlabeled_text_parsed`,
  `sacrifice_time_inferred`, `sacrifice_place_inferred`,
  `brief_deed_from_unlabeled_text`, `burial_place_inferred`, and
  `needs_human_review`.
- Birth time, join time, political status, nationality, and unit/role are not
  inferred from ordinary narrative text.
- `review_report.md` marks whether a record contains unlabeled inference so it
  can be reviewed manually before any Excel dry-run/apply step.

```powershell
python -m lieshi_ocr.cli build-review --batch 20260626 --text-manifest data/work/20260626/text/text_manifest.json
```

源码布局下如果未安装包，先设置：

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
```
