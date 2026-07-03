import json, re
from pathlib import Path

extracted = Path(r'd:\ying_min_mineru\extracted')

# Check if images are present in files WITH codes vs WITHOUT codes
has_code = []
no_code = []

for f in sorted(extracted.glob('*.pdf.json')):
    data = json.loads(f.read_text(encoding='utf-8'))
    md = data.get('markdown', '') or ''

    name_match = re.search(r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>', md)
    name = name_match.group(1).strip() if name_match else ''

    code_match = re.search(r'编号[：:]\s*([^\s\n]+)', md)
    if code_match:
        raw = code_match.group(1).strip()
        if raw and raw not in ('烈士信息修正审核表', '##'):
            has_code.append((f.name, md))
            continue
    no_code.append((f.name, md))

print(f'=== WITH code: {len(has_code)} files ===')
# Show last 200 chars of each to see if code appears at end
for fname, md in has_code[:3]:
    print(f'{fname}:')
    print(md[-300:])
    print()

print(f'=== WITHOUT code: {len(no_code)} files ===')
# Check if there are any image markers or other patterns near top
for fname, md in no_code[:5]:
    print(f'{fname}:')
    print(md[:500])
    print()

# Count how many have <!-- image--> markers
no_code_with_img = sum(1 for f, m in no_code if '<!-- image-->' in m)
print(f'no-code files with <!-- image-->: {no_code_with_img}')
