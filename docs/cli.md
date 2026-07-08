# CLI

本项目使用 `src` layout。推荐先在本地开发环境安装：

```powershell
python -m pip install -e .
lieshi-ocr --help
```

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 原始 PDF、真实 Excel、OCR 中间产物和输出文件默认不提交 Git。
- `excel-apply` 必须使用 `approved_changes.json`，不会直接覆盖输入 Excel。

## 全链路命令

生成裁剪 manifest，默认 dry-run：

```powershell
lieshi-ocr crop-batch --batch 20260626 --dry-run
```

显式写出裁剪 PDF：

```powershell
lieshi-ocr crop-batch --batch 20260626 --write-crops
```

从裁剪 manifest 生成文本 manifest：

```powershell
lieshi-ocr extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json
```

从文本 manifest 生成审核记录和 Markdown 报告：

```powershell
lieshi-ocr build-review --batch 20260626 --text-manifest data/work/20260626/text/text_manifest.json
```

基于 v4 Excel 生成 dry-run 报告：

```powershell
lieshi-ocr excel-dry-run --base-xlsx data/private/baselines/qixian_v4.xlsx --records data/work/20260626/review/correction_records.json --out-dir data/work/20260626/excel
```

只应用人工批准的 change，输出候选 Excel：

```powershell
lieshi-ocr excel-apply --base-xlsx data/private/baselines/qixian_v4.xlsx --dry-run data/work/20260626/excel/dry_run_report.json --approved data/work/20260626/excel/approved_changes.json --out-xlsx data/output/20260626/candidate.xlsx
```

## 子命令

```powershell
lieshi-ocr crop-batch --help
lieshi-ocr extract-text --help
lieshi-ocr build-review --help
lieshi-ocr excel-dry-run --help
lieshi-ocr excel-apply --help
```
