"""Project-level constants that do not execute business workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

ENV_PROJECT_ROOT = "LIESHI_OCR_ROOT"
ENV_BATCH = "LIESHI_OCR_BATCH"

DEFAULT_BATCH = "20260626"

CURRENT_BASELINE_XLSX = "英名录25版-祁县-二审_v4.xlsx"
V5_CANDIDATE_XLSX = "英名录25版-祁县-二审_v5.xlsx"


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime options that can be overridden by environment variables."""

    project_root: Path | None = None
    batch: str = DEFAULT_BATCH

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        root = os.environ.get(ENV_PROJECT_ROOT)
        batch = os.environ.get(ENV_BATCH, DEFAULT_BATCH)
        return cls(project_root=Path(root).expanduser() if root else None, batch=batch)
