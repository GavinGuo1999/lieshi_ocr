"""Read caller-provided MinerU text/markdown outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MineruTextResult:
    text: str
    path: str = ""
    warnings: tuple[str, ...] = ()


def read_mineru_text(text_dir: str | Path, source_stem: str, region: str = "") -> MineruTextResult:
    """Read text for one source/region from an explicit directory."""

    root = Path(text_dir)
    candidates = _candidate_paths(root, source_stem, region)
    for path in candidates:
        if path.is_file():
            return MineruTextResult(text=path.read_text(encoding="utf-8").strip(), path=path.as_posix())
    return MineruTextResult(text="", warnings=("mineru_text_not_found",))


def _candidate_paths(root: Path, source_stem: str, region: str) -> tuple[Path, ...]:
    suffixes = (".md", ".txt")
    names: list[str] = []
    if region:
        names.extend([f"{source_stem}__{region}", f"{source_stem}_{region}"])
    names.append(source_stem)
    return tuple(root / f"{name}{suffix}" for name in names for suffix in suffixes)
