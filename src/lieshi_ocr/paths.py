"""Path conventions for the lieshi_ocr project.

This module only computes paths. It does not create directories, move files,
read Excel workbooks, or run OCR work.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .config import ENV_PROJECT_ROOT

ROOT_MARKERS = ("AGENTS.md", ".git")


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the repository root from a starting path or LIESHI_OCR_ROOT."""

    env_root = os.environ.get(ENV_PROJECT_ROOT)
    if env_root:
        return Path(env_root).expanduser().resolve()

    current = Path.cwd() if start is None else Path(start).expanduser()
    current = current.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate

    raise FileNotFoundError(
        f"Could not find project root from {current}. "
        f"Set {ENV_PROJECT_ROOT} or run from inside the repository."
    )


@dataclass(frozen=True)
class BatchPaths:
    """Standard paths for one input batch."""

    batch: str
    scan: Path
    work: Path
    output: Path

    def as_dict(self) -> dict[str, Path | str]:
        return {
            "batch": self.batch,
            "scan": self.scan,
            "work": self.work,
            "output": self.output,
        }


@dataclass(frozen=True)
class ProjectPaths:
    """Computed project path layout."""

    root: Path

    @classmethod
    def discover(cls, start: str | Path | None = None) -> "ProjectPaths":
        return cls(root=find_project_root(start))

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def src(self) -> Path:
        return self.root / "src"

    @property
    def package(self) -> Path:
        return self.src / "lieshi_ocr"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def scan_root(self) -> Path:
        return self.data / "scan"

    @property
    def work_root(self) -> Path:
        return self.data / "work"

    @property
    def output_root(self) -> Path:
        return self.data / "output"

    @property
    def private(self) -> Path:
        return self.data / "private"

    @property
    def tests(self) -> Path:
        return self.root / "tests"

    @property
    def fixtures(self) -> Path:
        return self.tests / "fixtures"

    @property
    def old_code(self) -> Path:
        return self.root / "old_code"

    @property
    def new_code(self) -> Path:
        return self.root / "new_code"

    @property
    def archive(self) -> Path:
        return self.root / "_archive"

    def batch(self, batch: str) -> BatchPaths:
        return BatchPaths(
            batch=batch,
            scan=self.scan_root / batch,
            work=self.work_root / batch,
            output=self.output_root / batch,
        )

    def private_baseline(self, filename: str) -> Path:
        return self.private / "baselines" / filename

    def root_file(self, filename: str) -> Path:
        return self.root / filename

    def as_dict(self) -> dict[str, Path]:
        return {
            "root": self.root,
            "docs": self.docs,
            "src": self.src,
            "package": self.package,
            "data": self.data,
            "scan_root": self.scan_root,
            "work_root": self.work_root,
            "output_root": self.output_root,
            "private": self.private,
            "tests": self.tests,
            "fixtures": self.fixtures,
            "old_code": self.old_code,
            "new_code": self.new_code,
            "archive": self.archive,
        }
