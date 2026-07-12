"""Optional OCR engine adapters.

RapidOCR is never imported at module import time. Callers must explicitly
select the real engine; tests can use FakeOcrEngine without that dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class OcrTextResult:
    text: str
    confidence: float
    engine: str
    warnings: tuple[str, ...] = ()


class TextOcrEngine(Protocol):
    name: str

    def extract_text(self, crop_pdf: str | Path) -> OcrTextResult:
        ...


class NoOcrEngine:
    name = "none"

    def extract_text(self, crop_pdf: str | Path) -> OcrTextResult:
        return OcrTextResult(
            text="",
            confidence=0.0,
            engine=self.name,
            warnings=("ocr_engine_not_selected",),
        )


class FakeOcrEngine:
    name = "fake"

    def __init__(self, results: Mapping[str, str | OcrTextResult] | None = None) -> None:
        self._results = dict(results or {})

    def extract_text(self, crop_pdf: str | Path) -> OcrTextResult:
        key = Path(crop_pdf).as_posix()
        fallback_key = Path(crop_pdf).name
        value = self._results.get(key, self._results.get(fallback_key, ""))
        if isinstance(value, OcrTextResult):
            return value
        warnings: tuple[str, ...] = () if value else ("fake_ocr_text_missing",)
        return OcrTextResult(text=str(value), confidence=1.0 if value else 0.0, engine=self.name, warnings=warnings)


class RapidOcrEngine:
    name = "rapidocr"

    def __init__(self) -> None:
        try:
            from rapidocr import RapidOCR

            self._api = "current"
        except ImportError:
            try:
                from rapidocr_onnxruntime import RapidOCR

                self._api = "legacy"
            except ImportError as exc:  # pragma: no cover - depends on optional runtime.
                raise RuntimeError(
                    'RapidOCR is not installed. Run python -m pip install -e ".[ocr]" '
                    "or use --engine none / --code-name-engine none."
                ) from exc
        self._ocr = RapidOCR()

    def extract_text(self, crop_pdf: str | Path) -> OcrTextResult:
        image = _rapidocr_input(crop_pdf)
        if self._api == "current":
            result = self._ocr(image)
        else:
            result = self._ocr(image, return_img=False)
        rows, scores = _normalize_rapidocr_output(result)
        confidence = sum(scores) / len(scores) if scores else 0.0
        warnings: tuple[str, ...] = () if rows else ("rapidocr_empty_text",)
        return OcrTextResult(text="\n".join(rows), confidence=confidence, engine=self.name, warnings=warnings)


def create_ocr_engine(name: str) -> TextOcrEngine:
    normalized = (name or "none").lower()
    if normalized == "none":
        return NoOcrEngine()
    if normalized == "rapidocr":
        return RapidOcrEngine()
    raise ValueError(f"Unknown OCR engine: {name}")


def _rapidocr_input(path: str | Path) -> Any:
    source = Path(path)
    if source.suffix.lower() != ".pdf":
        return str(source)

    try:
        import fitz
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - declared runtime dependencies.
        raise RuntimeError("PyMuPDF and Pillow are required to OCR PDF crops with RapidOCR.") from exc

    with fitz.open(source) as document:
        if document.page_count == 0:
            raise RuntimeError(f"PDF has no pages: {source}")
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def _normalize_rapidocr_output(output: Any) -> tuple[list[str], list[float]]:
    """Normalize current dataclass and legacy tuple/list RapidOCR outputs."""
    if hasattr(output, "txts"):
        texts = list(output.txts or ())
        raw_scores = list(getattr(output, "scores", None) or ())
        return _clean_texts_and_scores(texts, raw_scores)

    legacy_rows = output
    if isinstance(output, tuple) and len(output) == 2:
        legacy_rows = output[0]

    texts: list[Any] = []
    scores: list[Any] = []
    for item in legacy_rows or ():
        if not isinstance(item, (list, tuple)):
            continue
        if len(item) >= 3:
            texts.append(item[1])
            scores.append(item[2])
        elif len(item) == 2 and isinstance(item[0], str):
            texts.append(item[0])
            scores.append(item[1])
    return _clean_texts_and_scores(texts, scores)


def _clean_texts_and_scores(texts: list[Any], scores: list[Any]) -> tuple[list[str], list[float]]:
    clean_texts: list[str] = []
    clean_scores: list[float] = []
    for index, value in enumerate(texts):
        text = str(value).strip()
        if not text:
            continue
        clean_texts.append(text)
        if index < len(scores) and scores[index] is not None:
            clean_scores.append(float(scores[index]))
    return clean_texts, clean_scores
