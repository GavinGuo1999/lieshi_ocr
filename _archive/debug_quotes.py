import re, json
from pathlib import Path

# 先看原始文本里引号到底是什么字符
with open(r'd:\ying_min_mineru\extracted_out\晋祁县000850_闫彩珍.json', encoding='utf-8') as f:
    data = json.load(f)
md = data.get('markdown', '')

m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
if m:
    raw = m.group(1)
    print('Raw text (first 200 chars):')
    for i, c in enumerate(raw[:200]):
        print(f'  {i}: U+{ord(c):04X} = {repr(c)}')
    print()
    # Strip HTML
    text = re.sub(r'<[^>]+>', '', raw)
    print('Clean text:', text[:300])
