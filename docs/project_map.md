# 项目地图

## 当前目录

- `old_code/`：第一轮历史代码，作为 legacy 参考，不在本轮移动。
- `new_code/`：第二轮候选主线代码，后续重构主要参考，不在本轮移动。
- `_archive/`：早期试验、分析和验证脚本。
- `data/`：真实批次数据、扫描件、裁剪结果、OCR/MinerU 中间产物。默认不提交 Git。
- `tmp/`：临时分析脚本、模型缓存、试验输出。默认不提交 Git。
- `output/`：历史输出文件。默认不提交 Git。
- `log/`：运行日志。默认不提交 Git。
- 根目录 `.xlsx`：真实 Excel 文件。默认不提交 Git。

## 目标目录

```text
lieshi_ocr/
  README.md
  pyproject.toml
  .gitignore

  docs/
    project_map.md
    data_contract.md
    excel_rules.md
    codex_workflow.md
    audit_v5.md

  src/lieshi_ocr/
    cli.py
    config.py
    paths.py
    schemas.py
    pdf/
    crop/
    ocr/
    parse/
    excel/
    pipeline/

  scripts/
    legacy/
      old_code/
      new_code/

  tests/
    fixtures/

  data/
    scan/
    work/
    output/
    private/
```

## 迁移原则

1. 先建立 Git 基线和文档，再迁移代码。
2. 不移动真实数据，不修改真实 Excel。
3. 不删除 legacy 代码。
4. 每轮只做一个小主题，完成后交给人工验收。
5. 需要测试数据时，创建小型脱敏 fixture，放入 `tests/fixtures/`。
