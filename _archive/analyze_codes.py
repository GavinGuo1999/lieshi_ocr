import json, re
from pathlib import Path
from collections import defaultdict

extracted = Path(r'd:\ying_min_mineru\extracted')

results = []
for f in sorted(extracted.glob('*.pdf.json')):
    data = json.loads(f.read_text(encoding='utf-8'))
    md = data.get('markdown', '') or ''

    name_match = re.search(r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>', md)
    name = name_match.group(1).strip() if name_match else ''

    code_match = re.search(r'编号[：:]\s*([^\s\n]+)', md)
    if code_match:
        raw = code_match.group(1).strip()
        if raw == '' or raw in ('烈士信息修正审核表', '##'):
            code = ''
        elif re.match(r'^晋祁县\d+$', raw):
            code = raw
        elif re.match(r'^\d{3,6}$', raw):
            code = '晋祁县' + raw.zfill(6)
        else:
            code = ''
    else:
        code = ''

    fname = f.stem
    if '_' in fname:
        batch = fname.rsplit('_', 1)[0]
        sub = fname.rsplit('_', 1)[1]
    else:
        batch = fname
        sub = 'main'

    results.append({'filename': f.name, 'batch': batch, 'sub': sub, 'code': code, 'name': name})

by_batch = defaultdict(list)
for r in results:
    by_batch[r['batch']].append(r)

for batch in sorted(by_batch.keys()):
    items = by_batch[batch]
    has_code = sum(1 for i in items if i['code'])
    no_name = sum(1 for i in items if not i['name'])
    print(f'{batch}: {len(items)} files, {has_code} with code, {no_name} empty name')
    for i in items:
        if i['code']:
            print(f'  sub={i["sub"]:>8}  code={i["code"]:>16}  name={i["name"]}')
    print()
