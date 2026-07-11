"""Build text manifests from crop manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from lieshi_ocr.ocr.mineru_text_reader import read_mineru_text
from lieshi_ocr.ocr.rapidocr_engine import NoOcrEngine, OcrTextResult, TextOcrEngine

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class TextRecord:
    batch: str
    source_pdf: str
    source_stem: str
    region: str
    crop_pdf: str
    engine: str
    text: str
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "source_pdf": self.source_pdf,
            "source_stem": self.source_stem,
            "region": self.region,
            "crop_pdf": self.crop_pdf,
            "engine": self.engine,
            "text": self.text,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class TextManifest:
    batch: str
    crop_manifest: str
    out_dir: str
    records: list[TextRecord]

    def to_json(self) -> JsonDict:
        return {
            "batch": self.batch,
            "crop_manifest": self.crop_manifest,
            "out_dir": self.out_dir,
            "total": len(self.records),
            "records": [record.to_json() for record in self.records],
        }


def extract_text_manifest(
    crop_manifest_path: str | Path,
    out_dir: str | Path,
    ocr_engine: TextOcrEngine | None = None,
    code_name_ocr_engine: TextOcrEngine | None = None,
    correction_ocr_engine: TextOcrEngine | None = None,
    mineru_text_dir: str | Path | None = None,
    use_mineru_correction: bool = True,
) -> TextManifest:
    """Read a crop manifest and return a text manifest."""

    crop_path = Path(crop_manifest_path)
    crop_manifest = json.loads(crop_path.read_text(encoding="utf-8"))
    batch = str(crop_manifest.get("batch", ""))
    engine = ocr_engine or NoOcrEngine()
    records: list[TextRecord] = []

    for source_record in crop_manifest.get("records", []):
        if not isinstance(source_record, dict):
            continue
        source_pdf = str(source_record.get("source_pdf", ""))
        source_stem = str(source_record.get("source_stem", Path(source_pdf).stem))
        source_warnings = _string_list(source_record.get("warnings", []))

        for region_record in source_record.get("regions", []):
            if not isinstance(region_record, dict):
                continue
            region = str(region_record.get("region", ""))
            crop_pdf = _crop_pdf_from_region(region_record)
            region_warnings = source_warnings + _string_list(region_record.get("warnings", []))
            region_engine = _engine_for_region(
                region=region,
                default_engine=engine,
                code_name_ocr_engine=code_name_ocr_engine,
                correction_ocr_engine=correction_ocr_engine,
            )
            result = _extract_region_text(
                crop_pdf=crop_pdf,
                source_stem=source_stem,
                region=region,
                engine=region_engine,
                mineru_text_dir=mineru_text_dir,
                use_mineru_correction=use_mineru_correction,
            )
            records.append(
                TextRecord(
                    batch=batch,
                    source_pdf=source_pdf,
                    source_stem=source_stem,
                    region=region,
                    crop_pdf=crop_pdf,
                    engine=result.engine,
                    text=result.text,
                    confidence=result.confidence,
                    warnings=region_warnings + list(result.warnings),
                )
            )

    return TextManifest(
        batch=batch,
        crop_manifest=crop_path.as_posix(),
        out_dir=Path(out_dir).as_posix(),
        records=records,
    )


def write_text_manifest(manifest: TextManifest, manifest_path: str | Path) -> None:
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_region_text(
    crop_pdf: str,
    source_stem: str,
    region: str,
    engine: TextOcrEngine,
    mineru_text_dir: str | Path | None,
    use_mineru_correction: bool = True,
) -> OcrTextResult:
    if use_mineru_correction and mineru_text_dir is not None and region == "correction":
        mineru = read_mineru_text(mineru_text_dir, source_stem=source_stem, region=region)
        if mineru.text:
            return OcrTextResult(text=mineru.text, confidence=1.0, engine="mineru_text", warnings=mineru.warnings)
        if isinstance(engine, NoOcrEngine):
            return OcrTextResult(text="", confidence=0.0, engine="mineru_text", warnings=mineru.warnings)
    if not crop_pdf:
        return OcrTextResult(text="", confidence=0.0, engine=engine.name, warnings=("crop_pdf_missing",))
    if engine.name == "rapidocr" and not Path(crop_pdf).exists():
        return OcrTextResult(text="", confidence=0.0, engine=engine.name, warnings=("crop_pdf_not_found",))
    return engine.extract_text(crop_pdf)


def _engine_for_region(
    region: str,
    default_engine: TextOcrEngine,
    code_name_ocr_engine: TextOcrEngine | None,
    correction_ocr_engine: TextOcrEngine | None,
) -> TextOcrEngine:
    if region in {"code", "name"}:
        return code_name_ocr_engine or default_engine
    if region == "correction":
        return correction_ocr_engine or default_engine
    return default_engine


def _crop_pdf_from_region(region_record: dict[str, Any]) -> str:
    return str(region_record.get("output_pdf") or region_record.get("pdf") or "")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
