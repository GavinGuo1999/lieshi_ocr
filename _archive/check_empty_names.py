import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')

empty_name_files = [
    'lieshi2026064_0068.pdf.json', 'lieshi2026064_0069.pdf.json',
    'lieshi2026064_0070.pdf.json', 'lieshi2026064_0071.pdf.json',
    'lieshi2026064_0072.pdf.json', 'lieshi2026064_0073.pdf.json',
    'lieshi2026064_0074.pdf.json', 'lieshi2026064_0075.pdf.json',
    'lieshi2026064_0076.pdf.json', 'lieshi2026064_0077.pdf.json',
    'lieshi2026064_0078.pdf.json', 'lieshi2026064_0079.pdf.json',
    'lieshi2026064_0080.pdf.json', 'lieshi2026064_0081.pdf.json',
    'lieshi2026064_0082.pdf.json', 'lieshi2026064_0083.pdf.json',
    'lieshi2026064_0084.pdf.json', 'lieshi2026064_0085.pdf.json',
    'lieshi2026064_0086.pdf.json', 'lieshi2026064_0087.pdf.json',
    'lieshi2026064_0088.pdf.json', 'lieshi2026064_0089.pdf.json',
]

for fname in empty_name_files:
    fp = extracted_dir / fname
    if not fp.exists():
        print('NOT FOUND: ' + fname)
        continue
    with open(fp, encoding='utf-8') as f:
        data = json.load(f)
    md = data.get('markdown', '') or ''
    code = data.get('code', '')

    # Try multiple patterns to extract name
    # Pattern 1: standard table
    m1 = re.search(r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>', md)
    # Pattern 2: in table with rowspan
    m2 = re.search(r'姓名[：:]*\s*</td>\s*<td[^>]*>([^<]{1,10}?)</td>', md)
    # Pattern 3: after the name label in text
    m3 = re.search(r'姓名[：:]*\s*</td>\s*<td[^>]*>([^<]{2,10}?)</td>', md)
    # Pattern 4: simple text extraction
    m4 = re.search(r'姓名[：:]*\s*</td>\s*<td[^>]*>(.{1,10}?)</td>', md)
    # Pattern 5: look for 姓名 anywhere and find next cell
    m5 = re.search(r'姓名[：:]*\s*</td>\s*<td[^>]*>(.{0,15}?)</td>', md)

    # Check if there's any table data at all
    has_table = '<table>' in md
    table_rows = md.count('<tr>')
    # Find all text content in the table
    all_td = re.findall(r'<td[^>]*>([^<]{1,20}?)</td>', md)

    name_candidates = [m1.group(1).strip() if m1 else '',
                       m2.group(1).strip() if m2 else '',
                       m3.group(1).strip() if m3 else '']

    # Print the first 400 chars of markdown to see the structure
    print('=== ' + fname + ' ===')
    print('Code: ' + code)
    print('Has table: ' + str(has_table) + ' | table rows: ' + str(table_rows))
    print('All TD cells: ' + str(all_td[:20]))
    print('Markdown snippet:')
    print(md[:500])
    print()
