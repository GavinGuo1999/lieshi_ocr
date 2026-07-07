# 裁剪模块

本轮只抽出裁剪基础层，不迁移真实数据，不运行 OCR，不改变 `new_code/` 的业务脚本。

## 新模块

- `src/lieshi_ocr/crop/geometry.py`：PDF 点坐标矩形 `PdfRect`，支持裁剪到页面范围、转 manifest 列表、缩放到像素边界、像素框反算 PDF 框。
- `src/lieshi_ocr/crop/layouts.py`：当前扫描版式的稳定区域定义，包括整块有效区域、三段拆分区域、region pipeline 候选区域。
- `src/lieshi_ocr/crop/line_rules.py`：从 legacy 线检测脚本中抽出的纯几何规则，输入模拟线坐标，输出 name/correction 单元格像素边界和命名规则。
- `src/lieshi_ocr/crop/naming.py`：裁剪输出文件名清洗和 PDF/JSON 成对唯一命名。
- `src/lieshi_ocr/crop/precheck.py`：只读裁剪预检计划，基于输入 PDF 路径和布局生成 manifest 数据。
- `src/lieshi_ocr/crop/records.py`：裁剪 manifest 的轻量记录模型。

这些模块都是纯 Python，不依赖 PyMuPDF、OpenCV、Pillow 或 OCR 引擎。
`precheck.py` 不打开 PDF、不创建目录、不写 JSON 文件、不运行 OCR、不读写 Excel。
`line_rules.py` 不做图像二值化或线检测，只接收调用方已经得到的线坐标或测试构造的模拟坐标。
`CropLayout.clipped_regions()` 只根据调用方传入的页面矩形裁剪固定区域，不读取真实 PDF 页面。

## 当前保留的旧实现

以下脚本暂不修改：

- `new_code/cut_review_area.py`
- `new_code/split_review_regions.py`
- `new_code/crop_precheck.py`
- `new_code/batch_region_pipeline.py`
- `new_code/batch_region_pipeline_v2.py`

后续可以逐个脚本替换公共逻辑，例如先把 `safe_filename`、`unique_output_paths` 和固定区域常量替换为新模块，再单独验证输出一致性。

## 下一步

建议下一轮优先继续做裁剪只读预检验收：

1. 用脱敏 fixture 验证裁剪预检 manifest 的字段稳定性。
2. 保持真实 PDF 裁剪和 OCR 引擎调用留在 legacy 脚本中。
3. 再进入 OCR/解析拆分前，先确认 manifest 能覆盖后续裁剪输出需要的字段。
