import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')

# Fix: lieshi2026064_0079 has name 张平山 - update
fp = extracted_dir / 'lieshi2026064_0079.pdf.json'
with open(fp, encoding='utf-8') as f:
    data = json.load(f)
data['name'] = '张平山'
with open(fp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Fixed 0079 name: 张平山')

# Summary: all empty-name files are blank forms
empty = ['lieshi2026064_%04d' % i for i in range(68, 90)]
print('These are blank forms (name field empty in original PDF):')
for fname in empty:
    if fname == 'lieshi2026064_0079':
        print('  ' + fname + '.pdf.json: 张平山 (fixed)')
    else:
        print('  ' + fname + '.pdf.json: (blank - no name in original)')
