import json
from pathlib import Path

import fitz


BASE = Path(r"D:\ying_min_mineru")
MANIFEST = BASE / "data" / "20260626" / "extracted_mineru_text_full237" / "mineru_text_manifest.json"
OUT_DIR = BASE / "log" / "name_mismatch_crops"
TARGET_CODES = {"晋祁县000616", "晋祁县000631", "晋祁县000786"}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    written = []
    for record in manifest["records"]:
        if record["code"] not in TARGET_CODES:
            continue
        detail = json.loads(Path(record["json"]).read_text(encoding="utf-8"))
        x0, y0, x1, y1 = detail["regions"]["name"]["candidate_rect_pdf_points"]
        clip = fitz.Rect(x0 - 10, y0 - 5, x1 + 15, y1 + 8)
        with fitz.open(detail["source_pdf"]) as doc:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False)
        path = OUT_DIR / f"{record['code']}_{record['name']}_{record['source_stem']}_name_cell.png"
        pix.save(path)
        written.append(path)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
