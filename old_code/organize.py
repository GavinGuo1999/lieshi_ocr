import json, re, shutil
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')
data_dir = Path(r'd:\ying_min_mineru\data')
base_dir = data_dir.parent  # d:\ying_min_mineru

pdf_dir = base_dir / 'pdf'
extracted_out_dir = base_dir / 'extracted_out'

pdf_dir.mkdir(exist_ok=True)
extracted_out_dir.mkdir(exist_ok=True)

def safe_filename(s):
    """Remove/replace characters invalid in Windows filenames."""
    if not s:
        return ''
    s = s.replace('/', '／').replace('\\', '＼')
    s = s.replace(':', '：').replace('*', '＊').replace('?', '？')
    s = s.replace('"', '＂').replace('<', '＜').replace('>', '＞')
    s = s.replace('|', '｜')
    return s.strip()

def build_name(code, name):
    if name:
        return code + '_' + safe_filename(name)
    else:
        return code + '_无姓名'

# Collect all entries
entries = []
for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    code = data.get('code', '')
    name = data.get('name', '')

    if not code:
        print('SKIP (no code): ' + jf.name)
        continue

    entries.append({
        'code': code,
        'name': name,
        'pdf_src': data_dir / jf.stem,
        'json_src': jf,
    })

# Handle duplicate names
name_count = {}
for e in entries:
    key = e['code']
    name_count[key] = name_count.get(key, 0) + 1

# Assign suffixes for deduplication
used_names = {}
for e in entries:
    base = build_name(e['code'], e['name'])
    if base not in used_names:
        used_names[base] = 0
        e['new_name'] = base
    else:
        used_names[base] += 1
        suffix = '_' + str(used_names[base])
        e['new_name'] = base + suffix

# Print all planned renames
print('=== 计划文件名 ===')
for e in entries:
    old_pdf = e['pdf_src'].name
    old_json = e['json_src'].name
    new = e['new_name']
    status = ''
    if not e['pdf_src'].exists():
        status = ' [PDF NOT FOUND]'
    print(new + status)

# Confirm
print('\nTotal: ' + str(len(entries)) + ' files')
print('PDF dir: ' + str(pdf_dir))
print('Extracted dir: ' + str(extracted_out_dir))

# Copy and rename
copied_pdf = 0
copied_json = 0
errors = []

for e in entries:
    new_name = e['new_name']

    # Copy PDF
    if e['pdf_src'].exists():
        shutil.copy2(e['pdf_src'], pdf_dir / (new_name + '.pdf'))
        copied_pdf += 1
    else:
        errors.append('PDF not found: ' + e['pdf_src'].name)

    # Copy JSON
    shutil.copy2(e['json_src'], extracted_out_dir / (new_name + '.json'))
    copied_json += 1

print('\nCopied ' + str(copied_pdf) + ' PDFs, ' + str(copied_json) + ' JSONs')
if errors:
    print('ERRORS:')
    for err in errors:
        print('  ' + err)
