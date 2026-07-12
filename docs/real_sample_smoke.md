# Real Sample Smoke Test

本页用于本地真实小样本验收。它只说明如何准备和运行，不要求提交任何真实 `data/` 产物。

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 不提交真实 PDF、真实 Excel、裁剪 PDF、OCR 文本、manifest、report 或 candidate Excel。
- 不修改 `old_code/`、`new_code/`。
- 本轮 smoke test 不 promote v5，只验证新流水线是否贴合真实小样本。

## 本地数据准备

把真实扫描 PDF 放到批次目录：

```text
data/scan/{batch}/
```

示例：

```text
data/scan/20260626/
```

如果历史数据保留在批次子目录，例如：

```text
data/scan/20260626/scan/
```

不需要复制或移动 PDF。运行 `crop-batch` 时显式传入 `--scan-dir`：

```powershell
lieshi-ocr crop-batch --batch 20260626 --scan-dir data/scan/20260626/scan --limit 3 --write-crops
```

把可信 v4 基线 Excel 放到私有基线目录：

```text
data/private/baselines/qixian_v4.xlsx
```

这些目录已经被 `.gitignore` 排除。运行前后都要确认：

```powershell
git status --short
```

## 安装

```powershell
python -m pip install -e .
lieshi-ocr --help
```

混合模式需要 RapidOCR 可选依赖。运行 code/name OCR 前安装：

```powershell
python -m pip install -e ".[ocr]"
```

## 小样本全链路

先限制 3 个 PDF，避免第一次 smoke test 产物过多：

```powershell
lieshi-ocr crop-batch --batch 20260626 --scan-dir data/scan/20260626/scan --limit 3 --write-crops
```

读取裁剪 manifest，生成文本 manifest。默认 `--engine none` 不会跑真实 OCR；如果已经有 MinerU markdown/text 输出，优先复用它：

```powershell
lieshi-ocr extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json --mineru-text-dir data/scan/20260626/mineru_text
```

When MinerU correction text is available but code/name are still empty, run
RapidOCR only on the short code/name crops and keep correction on MinerU:

```powershell
lieshi-ocr extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json --mineru-text-dir data/scan/20260626/mineru_text --code-name-engine rapidocr --correction-engine mineru
```

This mixed route does not OCR the long correction body with RapidOCR. If the
optional RapidOCR runtime is not installed, the command fails clearly while the
default `--engine none` and MinerU-only routes remain available.

如果已有 MinerU 文本目录不在 `data/scan/20260626/mineru_text`，把 `--mineru-text-dir` 指向实际 md/txt 目录。只有 MinerU 文本仍为空时，再考虑显式 OCR。

历史 MinerU 输出可以是嵌套结构，例如：

```text
data/scan/20260626/mineru_text/{带编号姓名和source_stem的目录}/ocr/*.md
```

`extract-text --mineru-text-dir` 会优先尝试顶层精确文件名；如果找不到，会递归查找父目录名包含 `source_stem` 的 `.md/.txt`，并优先使用 `ocr/` 目录下的 Markdown。

生成人工审核记录和 Markdown 报告：

```powershell
lieshi-ocr build-review --batch 20260626 --text-manifest data/work/20260626/text/text_manifest.json
```

基于 v4 生成 Excel dry-run 报告：

```powershell
lieshi-ocr excel-dry-run --base-xlsx data/private/baselines/qixian_v4.xlsx --records data/work/20260626/review/correction_records.json --out-dir data/work/20260626/excel
```

本轮 smoke test 默认不运行 `excel-apply`。如果需要试跑 apply，只能使用人工准备的 `approved_changes.json`，并输出到 `data/output/{batch}/`。

## 验收 Checklist

- `crop_manifest.json` 存在。
- `crop_manifest.json` 中 PDF 总数符合 `--limit`。
- code/name/correction 三类裁剪区域都有记录。
- 裁剪阶段 warnings 可解释。
- `text_manifest.json` 存在。
- code/name/correction 三类文本记录数量符合预期。
- OCR/MinerU 缺失时 warnings 清楚。
- `correction_records.json` 存在。
- `review_report.md` 按 code/name 分组，便于人工审查。
- 编号缺失、姓名缺失、字段冲突进入 warnings。
- `dry_run_report.json` 和 `dry_run_report.md` 存在。
- dry-run 修改按列可解释。
- N 列审稿意见是追加，不覆盖旧意见。
- T 列备份旧 K。
- 没有覆盖 v4 输入 Excel。
- `git status --short` 不显示 `data/` 产物。

## 可以贴给 GPT 审的内容

只贴脱敏统计或脱敏片段：

- crop manifest：总 PDF 数、成功数、warnings 种类。
- text manifest：code/name/correction 三类文本成功率、warnings 种类。
- review report：脱敏后的 1-3 条记录。
- dry-run report：拟修改条数、按列统计、skipped/warnings。

## 不应公开的内容

不要贴、不要提交：

- 原始 PDF。
- 真实 Excel。
- 完整 `crop_manifest.json`。
- 完整 `text_manifest.json`。
- 完整 `correction_records.json`。
- 完整 `review_report.md`。
- 完整 `dry_run_report.json` / `dry_run_report.md`。
- candidate Excel。
- 填报单位、填表人、联系电话、完整个人事迹文本。

## 建议发给 GPT 的脱敏摘要模板

```text
batch: 20260626
pdf_limit: 3

crop:
- total_pdfs:
- records:
- warning_types:

text:
- code_records:
- name_records:
- correction_records:
- warning_types:

review:
- total_records:
- missing_code:
- missing_name:
- conflict_count:
- sample_redacted_records:

excel_dry_run:
- proposed_changes:
- changes_by_column:
- skipped:
- warning_types:
```
