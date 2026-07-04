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

## Legacy 路径说明

旧脚本中可能仍出现 `data/{batch}/scan`、`data/{batch}/cut`、`data/{batch}/extracted` 等历史目录写法。这些路径只作为 legacy 参考保留，不进入新的 `ProjectPaths` 契约。

新的正式契约只包含：

- `data/scan/{batch}/`
- `data/work/{batch}/`
- `data/output/{batch}/`
- `data/private/`

## 硬编码路径脚本状态

`old_code/` 和 `new_code/` 中仍可能包含硬编码本地路径或旧式批次目录。这些脚本当前都视为 legacy 或候选主线参考，不在本轮迁移，不允许因此改变 OCR、裁剪或 Excel 输出逻辑。

后续迁移时应逐个脚本处理：先用 `ProjectPaths` 替换路径边界，再用 dry-run 或脱敏 fixture 验证输出一致性。

## 下一步使用方式

后续拆分脚本时，优先从 `new_code/` 中选择单个脚本，把硬编码路径替换为 `ProjectPaths`，并保持原业务输出不变。每次只替换一个工作流，替换前后都要运行 dry-run 或最小验证。
