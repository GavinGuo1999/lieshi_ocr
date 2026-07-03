# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

# Read one sample
with open(r'd:\ying_min_mineru\extracted_out\晋祁县000850_闫彩珍.json', encoding='utf-8') as f:
    data = json.load(f)

md = data.get('markdown', '')
m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
raw = m.group(1) if m else ''
text = re.sub(r'<[^>]+>', '', raw)

print('Clean text:')
print(text[:500])
print()

# Try to find all quoted values
LQ = '\u201c'  # "
RQ = '\u201d'  # "

# Pattern 1: content between Chinese quotes
pat1 = re.compile(r'[\u4e00-\u9fa5]{2,10}补充(?:填写|完善)为([\u201c"]([^\u201c\u201d"]+)[\u201d"])')
matches1 = pat1.findall(text)
print('Matches with quoted values:')
for field, val in matches1:
    print(f'  Field pattern matched text: {field} -> {val}')

# Pattern 2: simpler - everything between LQ and RQ
pat2 = re.compile(r'([\u4e00-\u9fa5]{2,10}补充(?:填写|完善)为)[\u201c"]([^\u201c\u201d"]+)[\u201d"]')
matches2 = pat2.findall(text)
print()
print('Matches (field, value):')
for field, val in matches2:
    print(f'  {field}: {val}')

# Pattern 3: using lookbehind
pat3 = re.compile(r'(?<=为[\u201c"]).*?(?=[\u201d"])')
matches3 = pat3.findall(text)
print()
print('All quoted values:')
for val in matches3:
    print(f'  {val}')
