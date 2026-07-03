# -*- coding: utf-8 -*-
import json, re, glob, os, random

def extract_corr(jf):
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    md = data.get('markdown', '')
    m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
    if not m:
        return ''
    text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    idx = text.find('生前')
    if idx >= 0:
        return text[idx:idx+300]
    return ''

jsons = glob.glob('extracted_out/*.json')

print('=== 贾狗成 ===')
print(repr(extract_corr('extracted_out/晋祁县001076_贾狗成.json')))
print()

for jf in random.sample(jsons, 5):
    print(f'=== {os.path.basename(jf)} ===')
    print(repr(extract_corr(jf)))
    print()
