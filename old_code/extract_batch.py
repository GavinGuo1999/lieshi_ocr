"""
MinerU Flash API 批量提取脚本
- 断点续传（每个文件单独存储，出错不影响整体）
- 进度可视化
- 错误重试
- 结果存储为 JSON（包含原始 Markdown）
"""

import mineru
import json
import os
import sys
import time
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# ========== 配置 ==========
DATA_DIR = Path(r"d:\ying_min_mineru\data")
OUTPUT_DIR = Path(r"d:\ying_min_mineru\extracted")
CHECKPOINT_FILE = OUTPUT_DIR / "_checkpoint.json"
LOG_FILE = OUTPUT_DIR / "_extraction_log.txt"

TIMEOUT_PER_FILE = 120  # 单文件超时（秒）
BATCH_INTERVAL = 2.0     # API 轮询间隔（秒）

# ========== 数据结构 ==========
@dataclass
class ExtractionRecord:
    original_filename: str
    task_id: str
    state: str
    markdown: Optional[str]
    error: Optional[str]
    extracted_at: str


# ========== 日志 ==========
def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ========== 加载检查点 ==========
def load_checkpoint() -> dict[str, ExtractionRecord]:
    if not CHECKPOINT_FILE.exists():
        return {}
    try:
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return {k: ExtractionRecord(**v) for k, v in data.items()}
    except Exception:
        return {}


def save_checkpoint(checkpoint: dict[str, ExtractionRecord]):
    data = {k: asdict(v) for k, v in checkpoint.items()}
    CHECKPOINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ========== 进度条 ==========
def print_progress(done: int, total: int, errors: int, elapsed: float):
    bar_len = 30
    filled = int(bar_len * done / total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    pct = done / total * 100 if total > 0 else 0
    eta = (elapsed / done * (total - done)) if done > 0 else 0
    mins, secs = int(eta // 60), int(eta % 60)
    sys.stdout.write(f"\r[{bar}] {pct:5.1f}%  {done}/{total}  err:{errors}  eta:~{mins}m{secs}s    ")
    sys.stdout.flush()


# ========== 主流程 ==========
def main():
    client = mineru.MinerU()

    # 准备输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    # 获取所有 PDF
    pdf_files = sorted([f for f in DATA_DIR.iterdir() if f.suffix.lower() == ".pdf"])
    total = len(pdf_files)
    log(f"共找到 {total} 个 PDF 文件")

    # 加载检查点
    checkpoint = load_checkpoint()
    done_count = sum(1 for r in checkpoint.values() if r.state == "done")
    error_count = sum(1 for r in checkpoint.values() if r.state == "error")
    log(f"检查点: 已完成 {done_count}, 错误 {error_count}")

    # 过滤待处理文件
    pending = [f for f in pdf_files if f.name not in checkpoint]
    log(f"本次待处理: {len(pending)} 个")

    start_time = time.time()

    for i, pdf_path in enumerate(pending):
        fname = pdf_path.name
        result_file = OUTPUT_DIR / f"{fname}.json"
        is_retry = fname in checkpoint and checkpoint[fname].state == "error"

        if is_retry:
            log(f"重试 [{i+1}/{len(pending)}] {fname}")

        try:
            result = client.flash_extract(
                str(pdf_path),
                timeout=TIMEOUT_PER_FILE,
            )
        except Exception as e:
            log(f"ERROR [{i+1}/{len(pending)}] {fname}: {type(e).__name__} {e}")
            checkpoint[fname] = ExtractionRecord(
                original_filename=fname,
                task_id="",
                state="error",
                markdown=None,
                error=f"{type(e).__name__}: {e}",
                extracted_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            save_checkpoint(checkpoint)
            print_progress(done_count + sum(1 for r in list(checkpoint.values())[-len(pending):] if r.state in ("done", "error")),
                          total, error_count, time.time() - start_time)
            continue

        record = ExtractionRecord(
            original_filename=fname,
            task_id=result.task_id,
            state=result.state,
            markdown=result.markdown,
            error=result.error,
            extracted_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        checkpoint[fname] = record

        # 单独保存文件
        result_file.write_text(
            json.dumps(asdict(record), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        if result.state == "done":
            log(f"OK [{i+1}/{len(pending)}] {fname} ({len(result.markdown or '')} chars)")
            done_count += 1
        else:
            log(f"FAIL [{i+1}/{len(pending)}] {fname}: {result.error}")

        # 每5个保存一次检查点
        if (i + 1) % 5 == 0:
            save_checkpoint(checkpoint)

        print_progress(done_count, total, total - done_count, time.time() - start_time)

    # 最终保存
    save_checkpoint(checkpoint)
    elapsed = time.time() - start_time
    mins, secs = int(elapsed // 60), int(elapsed % 60)
    print(f"\n\n完成！耗时 {mins}m{secs}s")

    # 统计
    done = sum(1 for r in checkpoint.values() if r.state == "done")
    fail = sum(1 for r in checkpoint.values() if r.state == "error")
    print(f"总计: 成功 {done}, 失败 {fail}, 跳过 {total - done - fail}")
    client.close()


if __name__ == "__main__":
    main()
