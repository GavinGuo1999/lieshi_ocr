"""PDF rectangle helpers used by crop planning code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, order=True)
class PdfRect:
    """A PDF rectangle in points: left, top, right, bottom."""

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_sequence(cls, values: Sequence[float | int]) -> "PdfRect":
        if len(values) != 4:
            raise ValueError(f"Expected four rectangle values, got {len(values)}")
        return cls(*(float(value) for value in values))

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def clip_to(self, outer: "PdfRect") -> "PdfRect":
        return PdfRect(
            max(self.x0, outer.x0),
            max(self.y0, outer.y0),
            min(self.x1, outer.x1),
            min(self.y1, outer.y1),
        )

    def expand(self, dx: float = 0.0, dy: float = 0.0) -> "PdfRect":
        return PdfRect(self.x0 - dx, self.y0 - dy, self.x1 + dx, self.y1 + dy)

    def to_list(self, ndigits: int = 2) -> list[float]:
        return [round(value, ndigits) for value in (self.x0, self.y0, self.x1, self.y1)]

    def size_list(self, ndigits: int = 2) -> list[float]:
        return [round(self.width, ndigits), round(self.height, ndigits)]

    def scaled_bounds(self, scale: float) -> tuple[int, int, int, int]:
        return (
            int(round(self.x0 * scale)),
            int(round(self.y0 * scale)),
            int(round(self.x1 * scale)),
            int(round(self.y1 * scale)),
        )

    def px_bounds_to_pdf_rect(
        self,
        bounds: tuple[int, int, int, int],
        image_size: tuple[int, int],
    ) -> "PdfRect":
        left, top, right, bottom = bounds
        width, height = image_size
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid image size: {image_size}")
        return PdfRect(
            self.x0 + self.width * left / width,
            self.y0 + self.height * top / height,
            self.x0 + self.width * right / width,
            self.y0 + self.height * bottom / height,
        )
