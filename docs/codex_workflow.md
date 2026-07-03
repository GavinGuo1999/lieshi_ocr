# Codex 工作流

## 分支策略

`main` 只保存当前可信状态。每轮 Codex 工作都从 `main` 新建一个小分支：

```powershell
git checkout main
git checkout -b refactor/00-docs-map
```

建议顺序：

1. `refactor/00-docs-map`：只做 Git 化、文档和项目地图。
2. `refactor/01-paths`：统一目录和路径管理，但不迁移真实数据。
3. `refactor/02-schemas`：定义数据结构和 JSON 契约。
4. `refactor/03-crop-modules`：拆分裁剪模块。
5. `refactor/04-ocr-parse`：拆分 OCR 与正文解析。
6. `refactor/05-excel-dry-run`：重构 Excel dry-run，不直接 apply。
7. `refactor/06-cli`：统一 CLI。

## 每轮任务边界

- 只做一个主题。
- 不在 `main` 上直接改。
- 不修改真实 Excel。
- 不提交 PDF、OCR 中间产物、模型缓存或真实数据。
- 不把 v5 当成正式基线。
- 不引入重型依赖，除非任务明确批准。

## 完成后检查

```powershell
git status
git diff --stat main...HEAD
git diff main...HEAD
pytest
```

如果项目还没有测试套件，至少运行：

```powershell
python -m compileall old_code new_code _archive
```

## 交付给人工验收

每轮完成后提供：

- 当前分支。
- 本轮目标。
- 修改文件列表。
- 是否修改业务代码。
- 是否改变业务逻辑。
- `git diff --stat main...HEAD`。
- 测试或 `compileall` 结果。
- 已知风险和不确定点。
- 下一阶段建议。

人工验收通过后，再合并回 `main` 并打 tag。
