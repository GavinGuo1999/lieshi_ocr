# 裁剪批处理流水线

本流水线把现有 crop 模块串起来，用于读取调用方指定批次目录下的 PDF 页尺寸，生成 code/name/correction 三类区域裁剪计划，并在显式要求时保存裁剪 PDF。

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 不运行 RapidOCR、PaddleOCR、MinerU 或 OpenCV。
- 不读写 Excel。
- 不修改 `old_code/` 和 `new_code/`。
- 不提交 `data/` 产物。

## 输入输出

批量输入目录固定为：

```text
data/scan/{batch}/
```

输出目录固定为：

```text
data/work/{batch}/crop/
```

默认 dry-run 会写出：

```text
data/work/{batch}/crop/crop_manifest.json
```

只有显式传入 `--write-crops` 时，才会写出裁剪 PDF。

## CLI

```powershell
python -m lieshi_ocr.cli crop-batch --batch 20260626 --dry-run
python -m lieshi_ocr.cli crop-batch --batch 20260626 --write-crops
python -m lieshi_ocr.cli crop-one --pdf path\to\one.pdf --batch 20260626 --write-crops
```

`crop-one` 只处理调用方显式传入的单个 PDF，不扫描批次目录。
