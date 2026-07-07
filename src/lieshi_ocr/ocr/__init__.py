"""OCR/Text extraction adapters."""

from .mineru_text_reader import MineruTextResult, read_mineru_text
from .rapidocr_engine import FakeOcrEngine, NoOcrEngine, OcrTextResult, RapidOcrEngine, create_ocr_engine

__all__ = [
    "FakeOcrEngine",
    "MineruTextResult",
    "NoOcrEngine",
    "OcrTextResult",
    "RapidOcrEngine",
    "create_ocr_engine",
    "read_mineru_text",
]
