# OCR/Text 提取流水线

本流水线读取裁剪阶段生成的 `crop_manifest.json`，输出统一的 `text_manifest.json`，为后续 parse/review 做准备。

## 边界

- 当前可信 Excel 基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 不读写 Excel。
- 不修改 `old_code/` 和 `new_code/`。
- 默认不运行真实 RapidOCR；只有显式 `--engine rapidocr` 才尝试加载可选依赖。
- 不调用 MinerU 命令行，只读取调用方显式传入目录中的 markdown/text 文件。
- 不提交 `data/` 产物。

## 输入输出

默认输入：

```text
data/work/{batch}/crop/crop_manifest.json
```

默认输出：

```text
data/work/{batch}/text/text_manifest.json
```

每条文本记录至少包含：

- `batch`
- `source_pdf`
- `source_stem`
- `region`
- `crop_pdf`
- `engine`
- `text`
- `confidence`
- `warnings`

## CLI

```powershell
python -m lieshi_ocr.cli extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json
```

默认 `--engine none` 只生成结构化 manifest 和 warning，不跑真实 OCR。

如需读取已有 MinerU 文本：

```powershell
python -m lieshi_ocr.cli extract-text --batch 20260626 --mineru-text-dir data/work/20260626/mineru_text
```

For smoke tests where correction text comes from MinerU but code/name need OCR,
use the mixed-region mode:

```powershell
python -m pip install -e ".[ocr]"
```

```powershell
python -m lieshi_ocr.cli extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json --mineru-text-dir data/scan/20260626/mineru_text --code-name-engine rapidocr --correction-engine mineru
```

- `--code-name-engine rapidocr` only applies to `code` and `name` regions.
- `--correction-engine mineru` keeps the long correction body on MinerU text.
- `--engine` remains as the legacy/default all-region engine and defaults to
  `none`.
- Tests use fake OCR engines; the real RapidOCR runtime is optional and only
  loaded when explicitly selected.
