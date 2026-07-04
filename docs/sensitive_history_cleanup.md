# 敏感历史清理记录

## 2026-07-05

本轮只清理 Git 历史中的敏感样本文档，不做 OCR、Excel、裁剪业务重构。

清理目标：

- `_archive/test_output.md`

清理原因：

- 该文件曾包含公开仓库不应暴露的真实联系信息字段和具体样本文本。

清理方式：

```powershell
python -m git_filter_repo --sensitive-data-removal --invert-paths --path _archive/test_output.md --force
```

清理前该路径可在历史中查到：

```powershell
git log --all --oneline --decorate -- _archive/test_output.md
```

清理后确认：

```powershell
git log --all --oneline --decorate -- _archive/test_output.md
git ls-files _archive/test_output.md
python -m compileall src old_code new_code _archive
python -m unittest discover -s tests
```

注意事项：

- 本轮使用历史重写，会改变 commit hash。
- 推送到 GitHub 需要 force push `main`、相关分支和 tags。
- 其他本地 clone 应重新 clone，或按 `git-filter-repo` 文档完成本地清理和 rebase。
