import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')
ocr_codes_path = extracted_dir / 'ocr_codes.json'

# Load OCR results
with open(ocr_codes_path, encoding='utf-8') as f:
    ocr_data = json.load(f)

updated = 0
errors = []

for json_file in sorted(extracted_dir.glob('*.pdf.json')):
    if json_file.name == 'ocr_codes.json':
        continue
    if json_file.name == '_checkpoint.json':
        continue

    with open(json_file, encoding='utf-8') as f:
        data = json.load(f)

    ocr_result = ocr_data.get(json_file.name, {})

    # Build updated record
    data['code'] = ocr_result.get('code', '')
    data['ocr_text'] = ocr_result.get('ocr_text', '')
    if 'error' in ocr_result:
        data['ocr_error'] = ocr_result['error']

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    updated += 1

print(f'Updated {updated} files')

# Summary of problem files
no_code = [k for k, v in ocr_data.items() if not v.get('code') and k.endswith('.pdf.json')]
bad_code = [k for k, v in ocr_data.items() if v.get('code') and not re.match(r'^晋祁县\d{6}$', v['code'])]
print(f'\nStill no code: {len(no_code)}')
for k in no_code:
    print(f'  {k}: [{ocr_data[k]["ocr_text"]}]')
print(f'\nBad code format: {len(bad_code)}')
for k in bad_code:
    print(f'  {k}: {ocr_data[k]["code"]}')
