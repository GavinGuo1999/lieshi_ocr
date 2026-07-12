# OCR Audit Report

本工具用于诊断编号、姓名 OCR 与可信 v4 Excel 的不一致，不执行 Excel 修改。

## 边界

- 当前可信基线仍是 `英名录25版-祁县-二审_v4.xlsx`。
- `英名录25版-祁县-二审_v5.xlsx` 仍是待审计候选产物。
- 编号按 B 列精确查找，姓名按 D 列现有严格规则校验。
- 姓名清洗只去空格、换行、`姓名：` 标签和常见标点。
- 不做编辑距离放行、同音字替换、形近字纠正，也不会忽略姓名校验。
- 报告包含真实姓名和正文时属于本地敏感产物，必须保留在 `data/`，不得提交 Git。

## 命令

先重新运行 `extract-text` 和 `build-review`，使新 manifest 记录 MinerU 原文路径：

```powershell
lieshi-ocr extract-text --batch 20260626 --crop-manifest data/work/20260626/crop/crop_manifest.json --mineru-text-dir data/scan/20260626/mineru_text --code-name-engine rapidocr --correction-engine mineru
lieshi-ocr build-review --batch 20260626 --text-manifest data/work/20260626/text/text_manifest.json
```

生成只读审计报告：

```powershell
lieshi-ocr audit-ocr `
  --text-manifest data/work/20260626/text/text_manifest.json `
  --records data/work/20260626/review/correction_records.json `
  --base-xlsx "data/private/baselines/英名录25版-祁县-二审_v4.xlsx" `
  --out-dir data/work/20260626/audit
```

输出：

```text
data/work/20260626/audit/ocr_audit_report.json
data/work/20260626/audit/ocr_audit_report.html
```

## 报告内容

每条记录展示：

- OCR 编号、置信度、Excel 是否存在该编号及对应行号。
- OCR 姓名、安全清洗结果、Excel D 列预期姓名和精确匹配状态。
- 原始 PDF、code/name/correction crop 和 MinerU 原文链接。
- Parser 候选字段、MinerU 正文和全部 warnings。
- 可在浏览器中填写的人工结论；内容仅保存在当前浏览器的本地存储中，不回写 JSON 或 Excel。

旧版 `text_manifest.json` 没有 `text_source` 时，报告仍可生成，但 MinerU 原文链接显示为不可用。重新运行 `extract-text` 即可补齐该链接。

## 人工检查顺序

1. 先看编号 crop 与 OCR 编号是否一致。
2. 再看姓名 crop 是否只包含姓名值。
3. 对比 OCR 姓名、安全清洗姓名和 Excel 预期姓名。
4. 最后查看 correction/MinerU 原文、parser 候选和 warnings。

本报告只帮助定位问题。任何 Excel 修改仍必须经过 `excel-dry-run`、人工批准和 `excel-apply`。

## 本地浏览器视觉检查

浏览器不应放宽 `file://` 安全策略。需要检查 HTML 布局时，在项目根目录临时启动仅监听 loopback 的 HTTP 服务：

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory D:\Projects\lieshi_ocr
```

然后打开：

```text
http://127.0.0.1:8765/data/work/20260626/audit/ocr_audit_report.html
```

视觉检查至少确认：

- HTML 记录数与 JSON `record_count` 一致。
- code/name/correction crop 和 MinerU 原文链接可访问。
- 页面没有横向溢出，中文、长正文和 warnings 不重叠。
- OCR 姓名、安全清洗姓名和 Excel 预期姓名对比清楚。
- 浏览器控制台没有 JavaScript error。

服务必须绑定 `127.0.0.1`，禁止改为 `0.0.0.0`。检查完成后按 `Ctrl+C` 停止服务。截图和检查结果属于本地敏感产物，只能写入已忽略的 `data/work/{batch}/audit/`。
