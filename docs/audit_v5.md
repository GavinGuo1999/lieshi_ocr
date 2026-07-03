# v5 审计状态

当前状态：未完成审计。

`英名录25版-祁县-二审_v4.xlsx` 是当前可信 Excel 基线。

`英名录25版-祁县-二审_v5.xlsx` 是第二波数据进入后的候选输出。在审计完成前，所有重构、测试和 dry-run 都不得默认以 v5 为正式基线。

## v5 升级条件

1. 每条 second-wave applied change 有来源 JSON 或 OCR 文本证据。
2. Excel 行号、编号、姓名能够匹配。
3. J/K/N/G/H 等关键列变化符合业务规则。
4. 空字符串到 `None` 这类 Excel 重写副作用被识别并排除。
5. 人工确认 v5 可以作为后续基线。

## 升级后需要记录

如果 v5 审计通过，应另开分支，例如：

```powershell
git checkout -b baseline/promote-v5
```

并新增 `docs/baseline_history.md`，写清：

- v4 到 v5 已审计完成。
- v5 自哪个日期起成为新基线。
- 后续批次以 v5 为基础增量处理。
