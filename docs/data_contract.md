# 数据契约

本文件记录后续重构时优先遵守的 JSON 契约。当前契约来自 `new_code/` 中已经存在的 region pipeline、MinerU 增强、v5 dry-run 和 apply 脚本。

本轮只定义契约，不改变任何现有业务脚本，也不读取或写入真实 Excel。

## 质量状态

所有 OCR/解析记录的 `quality` 只能是：

- `ok`：可进入后续自动 dry-run。
- `review_needed`：可以保留在报告中，但需要人工复核。
- `failed`：本条处理失败，不能自动进入 Excel 修改。

告警字段统一使用 `warnings: list[str]`。常见值包括：

- `code_not_found`
- `name_not_found`
- `correction_text_empty`
- `parse_low_confidence`
- `mineru_error`
- `mineru_text_empty`

## OCR 详情记录

单条 OCR 详情 JSON 对应 `OcrRecord`：

```json
{
  "source_pdf": "data/scan/20260626/example.pdf",
  "source_stem": "example",
  "code": "晋祁县000001",
  "name": "示例姓名",
  "quality": "ok",
  "cut_pdf": "data/work/20260626/example.pdf",
  "json": "data/work/20260626/example.json",
  "warnings": [],
  "ocr": {},
  "correction_items": {
    "籍贯": {
      "value": "山西省晋中市祁县",
      "reason": "依据英名录"
    }
  },
  "regions": {},
  "mineru": {}
}
```

`correction_items` 的 key 是业务字段名，value 至少包含：

- `value`：候选新值。
- `reason`：来源理由或证据说明。

## Manifest 记录

Manifest 中的每条 `records[]` 对应 `ManifestRecord`：

```json
{
  "source_stem": "example",
  "code": "晋祁县000001",
  "name": "示例姓名",
  "json": "data/work/20260626/example.json",
  "quality": "ok",
  "warnings": []
}
```

MinerU manifest 可额外包含：

- `mineru_item_count`
- `mineru_marker_count`
- `mineru_reason_count`

## Batch Manifest

批次 manifest 对应 `BatchManifest`：

```json
{
  "batch": "20260626",
  "total": 1,
  "quality_counts": {"ok": 1},
  "warning_counts": {},
  "records": [],
  "generated_at": "2026-07-01 12:00:00"
}
```

`total` 必须等于 `records` 长度。

## Dry-run Report

Excel dry-run 报告对应 `DryRunReport`。它只能描述拟修改，不允许直接 apply：

```json
{
  "generated_at": "2026-07-01T12:00:00",
  "input": {
    "v4_xlsx": "英名录25版-祁县-二审_v4.xlsx",
    "full237_manifest": "mineru_text_manifest.json",
    "new6_manifest": "mineru_text_manifest.json"
  },
  "summary": {
    "records_total": 243,
    "proposed_changes": 1
  },
  "proposed_changes": [
    {
      "row": 2,
      "code": "晋祁县000001",
      "name": "示例姓名",
      "column": 6,
      "target": "origin",
      "field": "籍贯",
      "old": "",
      "new": "山西省晋中市祁县",
      "reason": "依据英名录",
      "source_stem": "example"
    }
  ]
}
```

`ProposedChange` 是后续 Excel apply 的唯一输入单位。apply 前必须再次检查当前单元格值等于 `old`，不相等则跳过。
