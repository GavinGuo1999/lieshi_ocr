# 裁剪模块

本轮只抽出裁剪基础层，不迁移真实数据，不运行 OCR，不改变 `new_code/` 的业务脚本。

## 新模块

- `src/lieshi_ocr/crop/geometry.py`：PDF 点坐标矩形 `PdfRect`，支持裁剪到页面范围、转 manifest 列表、缩放到像素边界、像素框反算 PDF 框。
- `src/lieshi_ocr/crop/layouts.py`：当前扫描版式的稳定区域定义，包括整块有效区域、三段拆分区域、region pipeline 候选区域。
- `src/lieshi_ocr/crop/naming.py`：裁剪输出文件名清洗和 PDF/JSON 成对唯一命名。
- `src/lieshi_ocr/crop/records.py`：裁剪 manifest 的轻量记录模型。

这些模块都是纯 Python，不依赖 PyMuPDF、OpenCV、Pillow 或 OCR 引擎。

## 当前保留的旧实现

以下脚本暂不修改：

- `new_code/cut_review_area.py`
- `new_code/split_review_regions.py`
- `new_code/crop_precheck.py`
- `new_code/batch_region_pipeline.py`
- `new_code/batch_region_pipeline_v2.py`

后续可以逐个脚本替换公共逻辑，例如先把 `safe_filename`、`unique_output_paths` 和固定区域常量替换为新模块，再单独验证输出一致性。

## 下一步

建议下一轮优先做 OCR/解析拆分前的接口整理：

1. 把 OCR 原始行、清洗文本、结构化 correction items 的边界写清楚。
2. 保持 OCR 引擎调用留在 legacy 脚本中，不在公共 schema 层引入重型依赖。
3. 用脱敏 fixture 验证解析函数，而不是跑真实扫描件。
