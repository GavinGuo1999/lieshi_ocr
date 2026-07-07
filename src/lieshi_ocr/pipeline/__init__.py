"""Pipeline entry points."""

from .extract_text import TextManifest, TextRecord, extract_text_manifest, write_text_manifest

__all__ = [
    "TextManifest",
    "TextRecord",
    "extract_text_manifest",
    "write_text_manifest",
]
