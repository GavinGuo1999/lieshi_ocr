# 路径管理

本轮只建立路径约定和代码入口，不迁移真实数据，不修改历史业务脚本。

## 新模块

- `src/lieshi_ocr/config.py`：保存批次默认值、环境变量名和 Excel 基线文件名常量。
- `src/lieshi_ocr/paths.py`：发现项目根目录，计算标准目录和批次路径。

路径模块只计算路径，不创建目录、不复制文件、不读取或写入 Excel。

## 环境变量

- `LIESHI_OCR_ROOT`：显式指定项目根目录。未设置时，会从当前目录向上查找 `AGENTS.md` 或 `.git`。
- `LIESHI_OCR_BATCH`：指定默认批次。当前默认值是 `20260626`。

## 标准批次目录

给定批次 `20260626` 后，标准路径为：

```text
data/scan/20260626/
data/work/20260626/
data/output/20260626/
```

真实 Excel 基线和不应公开数据仍放在本地，不提交 Git。后续如需统一引用基线文件，应使用：

```text
data/private/baselines/
```

## 下一步使用方式

后续拆分脚本时，优先从 `new_code/` 中选择单个脚本，把硬编码路径替换为 `ProjectPaths`，并保持原业务输出不变。每次只替换一个工作流，替换前后都要运行 dry-run 或最小验证。
