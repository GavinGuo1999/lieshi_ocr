from rapidocr_onnxruntime import RapidOCR
import fitz, io
from PIL import Image
from pathlib import Path
import re, json

ocr = RapidOCR()
data_dir = Path(r'd:\ying_min_mineru\data')
extracted_dir = Path(r'd:\ying_min_mineru\extracted')

CROP_X0, CROP_Y0, CROP_X1, CROP_Y1 = 0.70, 0.00, 1.00, 0.12

results = {}
no_pdf = []

json_files = sorted(extracted_dir.glob('*.pdf.json'))
for json_file in json_files:
    pdf_name = json_file.name[:-5]  # remove '.json' -> lieshi20260525_0004.pdf
    pdf_path = data_dir / pdf_name

    if not pdf_path.exists():
        no_pdf.append(pdf_name)
        continue

    try:
        doc = fitz.open(pdf_path)
        p = doc[0]
        pw, ph = p.rect.width, p.rect.height
        pix = p.get_pixmap(dpi=150)
        iw, ih = pix.width, pix.height
        img = Image.open(io.BytesIO(pix.tobytes('png')))
        doc.close()

        sx, sy = iw / pw, ih / ph
        cx0 = int(CROP_X0 * pw * sx)
        cy0 = int(CROP_Y0 * ph * sy)
        cx1 = int(CROP_X1 * pw * sx)
        cy1 = int(CROP_Y1 * ph * sy)
        cropped = img.crop((cx0, cy0, cx1, cy1))

        result, elapse = ocr(cropped, return_img=False)
        texts = ' '.join(r[1] for r in result) if result else ''

        code = ''
        if texts.strip():
            # Match: 晋祁县000XXX
            m = re.search(r'(晋祁县\d{6})', texts)
            if m:
                code = m.group(1)
            else:
                # Try: 祁县000XXX
                m = re.search(r'(祁县\d{6})', texts)
                if m:
                    code = '晋' + m.group(1)
                else:
                    # Try: just number 000XXX (4-6 digits)
                    m = re.search(r'\b(\d{4,6})\b', texts)
                    if m:
                        code = '晋祁县' + m.group(1).zfill(6)

        results[json_file.name] = {'ocr_text': texts.strip(), 'code': code}
    except Exception as e:
        results[json_file.name] = {'ocr_text': '', 'code': '', 'error': str(e)}

if no_pdf:
    print(f'WARNING: {len(no_pdf)} PDFs not found: {no_pdf[:5]}')

has_code = sum(1 for r in results.values() if r['code'])
has_text = sum(1 for r in results.values() if r['ocr_text'] and not r['code'])
empty = sum(1 for r in results.values() if not r['ocr_text'])

print(f'Total: {len(results)} | 有编号: {has_code} | 有文字无编号: {has_text} | 空白: {empty}')
print()
print('=== 有编号 ===')
for k, v in sorted(results.items()):
    if v['code']:
        print(f'  {k}: {v["code"]}')

print()
print('=== 有文字无编号 ===')
for k, v in sorted(results.items()):
    if v['ocr_text'] and not v['code']:
        print(f'  {k}: [{v["ocr_text"]}]')

print()
print('=== 空白 ===')
for k, v in sorted(results.items()):
    if not v['ocr_text']:
        print(f'  {k}')

# Save
out_path = extracted_dir / 'ocr_codes.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'\nSaved to {out_path}')
