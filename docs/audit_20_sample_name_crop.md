# 20 Sample Name Crop Audit

本轮在本地真实数据上验证连续 20 个 PDF。真实 PDF、Excel、manifest、debug overlay、联系表和 dry-run 报告均保留在被 Git 忽略的 `data/`，本文件只记录脱敏统计。

## 范围与边界

- batch: `20260626`
- sample count: `20`
- 姓名细化：`--refine-name-cell --write-debug`
- code/name OCR: RapidOCR
- correction text: MinerU
- Excel 基线：可信 v4
- 只执行 Excel dry-run，未创建批准清单，未执行 apply

## 姓名裁剪验收

| 指标 | 结果 | 通过线 | 结论 |
| --- | ---: | ---: | --- |
| `name_cell_lines` 成功 | 20/20 | >= 18/20 | 通过 |
| fallback | 0/20 | <= 2/20 | 通过 |
| 姓名 OCR 非空 | 20/20 | >= 19/20 | 通过 |
| 姓名与 v4 精确匹配 | 20/20 | >= 18/20 | 通过 |
| 明显裁到相邻单元格 | 0/20 | 0 | 通过 |
| code 非空且在 Excel 中存在 | 20/20 | >= 19/20 | 通过 |
| correction 非空 | 20/20 | >= 18/20 | 通过 |

20 张 debug overlay 已通过本地联系表人工检查，最终框均只覆盖姓名值单元格。姓名 OCR 长度范围为 2 至 3 个字符。

## Excel Dry-run

- records: `20`
- proposed changes: `40`
- K changes: `20`
- N changes: `20`
- T changes: `0`
- 每条记录均带 `multiple_date_candidates`、`needs_human_review`、`brief_deed_from_unlabeled_text` 和 `unlabeled_text_parsed`
- 未执行 approved/apply

K 候选长度：

- minimum: `16`
- median: `51`
- maximum: `106`
- longer than 40 characters: `18/20`
- longer than 60 characters: `1/20`

当前 K 候选整体偏长，不能批量批准。

## T 列备份风险

只读核对对应 20 行的 v4：

- old K 非空：20/20
- existing T 非空：20/20
- existing T 与当前 old K 相同：0/20

当前 dry-run 规则在 T 已有值时保留既有 T，因此没有提出 T 变更。这个行为避免覆盖历史备份，但也意味着当前 old K 没有被本轮明确备份。当前 20 条 K 变更不得批准，直到备份冲突策略明确。

## 下一步建议

开独立小范围任务处理 Excel story backup conflict：

1. old K 非空且 T 为空：照常提出 T=old K。
2. T 已等于 old K：视为已备份，不重复变更。
3. T 非空但不等于 old K：添加 `story_backup_conflict`，默认阻止 K 变更，不覆盖 T。
4. 同时为过长 K 候选增加明确 warning 或保守长度检查，不自动截断正文。
5. 使用 synthetic workbook 覆盖以上三种 T 状态。

在上述风险修复前，不创建 `approved_changes.json`，不生成 candidate Excel。
