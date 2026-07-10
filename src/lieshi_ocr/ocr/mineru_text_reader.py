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
    recursive_candidates = _recursive_candidate_paths(root, source_stem, region)
    if recursive_candidates:
        path = recursive_candidates[0]
        warnings = ("mineru_text_multiple_candidates",) if len(recursive_candidates) > 1 else ()
        return MineruTextResult(text=path.read_text(encoding="utf-8").strip(), path=path.as_posix(), warnings=warnings)
    return MineruTextResult(text="", warnings=("mineru_text_not_found",))


def _candidate_paths(root: Path, source_stem: str, region: str) -> tuple[Path, ...]:
    suffixes = (".md", ".txt")
    names: list[str] = []
    if region:
        names.extend([f"{source_stem}__{region}", f"{source_stem}_{region}"])
    names.append(source_stem)
    return tuple(root / f"{name}{suffix}" for name in names for suffix in suffixes)


def _recursive_candidate_paths(root: Path, source_stem: str, region: str) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    files = [path for pattern in ("*.md", "*.txt") for path in root.rglob(pattern) if path.is_file()]
    source_matches = [path for path in files if _path_contains_source_stem(path, source_stem)]
    if source_matches:
        files = source_matches
    if region == "correction":
        files = _prefer_body_text(files, source_stem)
    return tuple(sorted(files, key=lambda path: _candidate_sort_key(path, source_stem)))


def _path_contains_source_stem(path: Path, source_stem: str) -> bool:
    return any(source_stem in part for part in path.parts)


def _prefer_body_text(files: list[Path], source_stem: str) -> list[Path]:
    preferred = [
        path
        for path in files
        if not any(marker in path.name.lower() for marker in ("code", "name"))
        and path.suffix.lower() in {".md", ".txt"}
        and _path_contains_source_stem(path, source_stem)
    ]
    return preferred or files


def _candidate_sort_key(path: Path, source_stem: str) -> tuple[int, int, int, str]:
    suffix_rank = 0 if path.suffix.lower() == ".md" else 1
    ocr_rank = 0 if path.parent.name.lower() == "ocr" else 1
    source_rank = 0 if _path_contains_source_stem(path, source_stem) else 1
    return (ocr_rank, suffix_rank, source_rank, path.as_posix())
