import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')

updated = 0
empty_name = []

for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    md = data.get('markdown', '') or ''

    # Extract name from table
    name = ''
    # Try various patterns
    for pat in [
        r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>',
        r'姓名[：:]*\s*</td>\s*<td[^>]*>([^<]{1,10}?)</td>',
        r'>姓名[：:]*</td><td[^>]*>([^<]{1,10}?)</td>',
    ]:
        m = re.search(pat, md)
        if m and m.group(1).strip():
            name = m.group(1).strip()
            break

    data['name'] = name
    with open(jf, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not name:
        empty_name.append(jf.name)
    updated += 1

print('Updated ' + str(updated) + ' files')
print('Empty name: ' + str(len(empty_name)))
for n in empty_name:
    print('  ' + n)
