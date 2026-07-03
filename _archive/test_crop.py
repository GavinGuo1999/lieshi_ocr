from rapidocr_onnxruntime import RapidOCR
import fitz, io
from PIL import Image
from pathlib import Path
import re, json

ocr = RapidOCR()
data_dir = Path(r'd:\ying_min_mineru\data')
extracted_dir = Path(r'd:\ying_min_mineru\extracted')

test_files = [
    ('lieshi20260525_0004.pdf', '晋祁县000961'),
    ('lieshi20260525_0001.pdf', ''),
    ('lieshi20260525_0006.pdf', '晋祁县000964'),
]

crop_configs = [
    ('right_top_40pct',   0.40, 0.00, 1.00, 0.15),
    ('right_top_30pct',   0.70, 0.00, 1.00, 0.12),
    ('right_top_20pct',   0.80, 0.00, 1.00, 0.10),
    ('right_top_15pct',   0.85, 0.00, 1.00, 0.08),
]

for fname, expected in test_files:
    pdf_path = data_dir / fname
    if not pdf_path.exists():
        print(f'NOT FOUND: {fname}')
        continue

    doc = fitz.open(pdf_path)
    p = doc[0]
    pw, ph = p.rect.width, p.rect.height
    pix = p.get_pixmap(dpi=150)
    iw, ih = pix.width, pix.height
    img = Image.open(io.BytesIO(pix.tobytes('png')))
    doc.close()

    scale_x = iw / pw
    scale_y = ih / ph

    for crop_name, xr0, yr0, xr1, yr1 in crop_configs:
        cx0, cy0 = int(xr0 * pw * scale_x), int(yr0 * ph * scale_y)
        cx1, cy1 = int(xr1 * pw * scale_x), int(yr1 * ph * scale_y)
        cropped = img.crop((cx0, cy0, cx1, cy1))

        result, elapse = ocr(cropped, return_img=False)
        texts = ' | '.join(r[1] for r in result) if result else '(empty)'
        match = 'OK' if expected and expected in texts else ('--' if not expected else 'MISS')
        print(f'{fname} | {crop_name} | {match} | {texts}')

    print()
