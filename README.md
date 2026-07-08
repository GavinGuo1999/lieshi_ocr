# lieshi_ocr

烈士英名录 OCR 与 Excel 更新辅助项目。

当前阶段目标是先把历史脚本、数据产物和 Excel 基线关系梳理清楚，建立可回退、可审计、可验收的本地 Git 工作流。正式重构会分多轮小任务进行，每轮只处理一个主题。

## 当前基线

- 当前可信 Excel 基线：`英名录25版-祁县-二审_v4.xlsx`。
- 待审计候选产物：`英名录25版-祁县-二审_v5.xlsx`。
- v5 在人工审计完成前不能作为正式业务基线。
- 真实 Excel、PDF、OCR 中间产物和输出文件默认不提交 Git。

## 代码来源

- `old_code/`：第一次提取的历史脚本，只作为 legacy 参考。
- `new_code/`：第二次提取的脚本，是后续重构主线的主要参考，但还需要拆分、契约化和测试覆盖。
- `_archive/`：更早期的分析、验证和试验脚本，保留用于追溯。

## 后续方向

目标目录会逐步演进到 `src/lieshi_ocr/`、`scripts/legacy/`、`tests/fixtures/` 和 `docs/` 的结构。迁移和重构必须小步执行，不能在未审计前改变 Excel 业务输出。

## 路径约定

新的路径入口位于 `src/lieshi_ocr/paths.py`。它只负责发现项目根目录和计算 `data/scan/{batch}/`、`data/work/{batch}/`、`data/output/{batch}/` 等标准目录，不会创建目录或读写真实数据。详细说明见 `docs/path_management.md`。

## 数据契约

新的 JSON 契约入口位于 `src/lieshi_ocr/schemas.py`，覆盖 OCR 详情记录、批次 manifest、correction items 和 Excel dry-run report。详细说明见 `docs/data_contract.md`。

## 裁剪基础模块

裁剪相关基础模块位于 `src/lieshi_ocr/crop/`，目前只包含纯 Python 的矩形、版式、命名和 manifest 记录工具，不执行真实 PDF 裁剪。详细说明见 `docs/crop_modules.md`。

## 安装和 CLI

本项目使用 `src` layout。开发环境推荐可编辑安装：

```powershell
python -m pip install -e .
lieshi-ocr --help
```

完整命令链见 `docs/cli.md`。

## 本地检查

当前已有路径约定的最小单元测试。每轮完成后，至少运行：

```powershell
python -m compileall src old_code new_code _archive
python -m unittest discover -s tests
git status
git diff --stat main...HEAD
```
