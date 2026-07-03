# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

ext_out_dir = Path(r'd:\ying_min_mineru\extracted_out')
no_name_files = []

LQ = '\u201c'
RQ = '\u201d'

for jf in sorted(ext_out_dir.glob('*.json')):
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    name = data.get('name', '').strip()
    if not name:
        # Get correction text
        md = data.get('markdown', '')
        m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
        correction = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

        # Extract name from 姓名补充xxx为"YYY" pattern
        name_corr = None
        # Try various patterns
        for pat_str in [
            r'姓名补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ,
            r'姓名补充(?:填写|完善)为([^于理\u4e00-\u9fa5]+?)(?=[\u201c\u201d""|理由])',
        ]:
            pm = re.search(pat_str, correction)
            if pm:
                name_corr = pm.group(1).strip()
                break

        # Extract from shici text - first sentence often has the name
        shici_match = re.search(r'事迹补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction)

        no_name_files.append({
            'code': data.get('code', ''),
            'json_name': name,
            'correction': correction[:300],
            'name_from_corr': name_corr,
            'shici_val': shici_match.group(1)[:80] if shici_match else None,
            'filename': jf.stem
        })

print(f'无姓名文件总数: {len(no_name_files)}')
print()
for item in no_name_files:
    print(f'--- {item["code"]} ---')
    print(f'  JSON中姓名: {repr(item["json_name"])}')
    print(f'  修正内容中的姓名: {repr(item["name_from_corr"])}')
    if item['shici_val']:
        print(f'  事迹原文: {item["shici_val"]}')
    print(f'  修正内容: {item["correction"][:200]}')
    print()
