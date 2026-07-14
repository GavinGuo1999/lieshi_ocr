# v6 candidate 全量生成

## 范围

本轮以 `英名录25版-祁县-二审_v4.xlsx` 为唯一可信基线，处理
`data/scan/20260626/scan/` 中的 243 份扫描 PDF。`20260526` 批次未参与，v5 未作为输入。

全量流程为：

```text
243 PDF
-> refined code/name/correction crops
-> RapidOCR code/name + existing MinerU correction text
-> structured correction records
-> v6 dry-run
-> v6 candidate workbook
```

真实 PDF、MinerU 文本、manifest、dry-run 详情和 candidate Excel 均位于被 Git 忽略的
`data/` 目录，不提交公开仓库。

## 已确认规则

1. 编号按 v4 B 列精确匹配，姓名按 v4 D 列精确复核，不使用模糊匹配。
2. 日期保留原有精度：年、年月或年月日分别写成 `1947`、`1947-8`、`1947-8-15`。
3. 月和日不补零；原值或修正值为 `0` 时保留 `0`。
4. v6 candidate 只更新 E/F/G/H/I/J/K；N 审稿意见和 T 备份列保持不变。
5. K 只使用修正内容中明确提取的完整“事迹”值，不用时间、地点、原因机械拼接，也不截断。
6. F/J/K 使用富文本，只把相对 v4 新增或替换的文字标红；纯删除差异用删除位置旁的保留字符作红色锚点。
7. 短字段变化后整格红字。
8. F 籍贯按 v4 格式保留县级换行和乡镇、村之间的 `-`。
9. J 只增加单位/职务 `/` 分隔，不自动纠正姓名、地名、单位或职务正文。
10. candidate 中暂时保留 T，人工确认后由用户决定何时删除。

## 全量结果

- 扫描记录：243。
- 与 v4 编号、姓名精确匹配：240。
- 扫描修正内容明确要求删除、且 v4 已不存在的重复编号：3。
- 拟修改并成功写入：280 个单元格。
- F 列：16。
- J 列：25。
- K 列：239。
- apply 跳过：0。
- 日期格式异常并被阻断：2；candidate 保留对应 v4 原值。
- N 列变化：0。
- T 列变化：0。

未映射到 v4 独立列的民族、安葬地、牺牲时间、牺牲地点、牺牲原因、入党团时间和立功受奖等
修正项目仍完整保存在本地 dry-run/review JSON 中。牺牲相关信息通过明确的完整“事迹”项进入 K，
不是直接丢弃。

## 本地输出

- candidate：`data/output/20260626/英名录25版-祁县-二审_v6_candidate.xlsx`
- dry-run JSON：`data/work/20260626/v6/v6_dry_run_report.json`
- dry-run Markdown：`data/work/20260626/v6/v6_dry_run_report.md`
- approved changes：`data/work/20260626/v6/approved_changes.json`
- apply report：`data/work/20260626/v6/v6_apply_report.json`

## 核对重点

1. 在 candidate 中筛查 F/J/K 的红字内容，优先核对单位、职务、人名、地名和 OCR 易错字。
2. 两条日期异常没有写入 candidate，应结合扫描修正内容单独确认。
3. 三条重复删除记录不应重新添加到 v4/v6。
4. 确认 K 后再决定是否删除 T；本轮代码和 candidate 均未删除 T。
5. v6 candidate 通过人工核对前，v4 仍是可信基线。

## 验证

- candidate 与 v4 均为 1091 行、20 列，工作表名称一致。
- 实际变化坐标与 dry-run 的 280 个坐标完全一致，无额外改单元格。
- N/T 全列与 v4 一致。
- 所有 280 个变化单元格均包含红字。
- 原单元格样式、边框、填充和对齐保持不变。
- 写入 K 的 239 行使用审贾参考行高 `50.1`，K 列宽至少为 `57.25`。
