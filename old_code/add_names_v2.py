"""
add_names_v2.py — 增强版姓名提取
1. 优先从表格单元格提取
2. 尝试多种正则模式
3. 回退到"修正内容"中的姓名补充
4. 回退到"事迹"文本第一句中的姓名
"""
import json, re
from pathlib import Path

LQ = '\u201c'
RQ = '\u201d'
extracted_dir = Path(r'd:\ying_min_mineru\extracted')

updated = 0
empty_name = []
fixed_from_correction = 0

for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    md = data.get('markdown', '') or ''

    # ─── 策略 1: 从表格单元格提取 ───
    name = ''
    for pat in [
        r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>',
        r'姓名[：:]*\s*</td>\s*<td[^>]*>([^<]{1,10}?)</td>',
        r'>姓名[：:]*</td><td[^>]*>([^<]{1,10}?)</td>',
        r'姓名[：:]*\s*</td>\s*<td[^>]*>(.{1,15}?)</td>',
        r'姓名[：:]*\s*</td>\s*<td[^>]*>(.{0,20}?)</td>',
    ]:
        m = re.search(pat, md)
        if m and m.group(1).strip():
            candidate = m.group(1).strip()
            # 排除非人名字符串
            if candidate not in ('', '<img', '</td>', '&nbsp;') and not candidate.startswith('<'):
                name = candidate
                break

    # ─── 策略 2: 从"修正内容"中提取 ───
    if not name:
        m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
        if m:
            corr_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            # 匹配 "姓名补充填写为"XXX"" 或 "姓名补充完善为"XXX""
            nm = re.search(
                r'姓名补充(?:填写|完善|更正)为[' + LQ + RQ + '\u201c\u201d""]' 
                r'([^' + RQ + '\u201d"]+)[' + RQ + '\u201d"]',
                corr_text
            )
            if nm and nm.group(1).strip():
                name = nm.group(1).strip()
                fixed_from_correction += 1

    # ─── 策略 3: 从事迹补充中提取第一句的人名 ───
    if not name:
        m = re.search(r'事迹补充(?:填写|完善)为[' + LQ + RQ + '\u201c\u201d""]([^' + RQ + '\u201d"]{10,80})', md)
        if not m:
            m = re.search(r'事迹补充(?:填写|完善)为[' + LQ + RQ + '\u201c\u201d""]([^' + RQ + '\u201d"]{10,80})', 
                          re.sub(r'<[^>]+>', '', md))
        if m:
            shici = m.group(1).strip()
            # 事迹第一句通常包含 "XXX烈士，男，..."
            nm = re.search(r'^([^\s，,]{2,4})烈士[,，]', shici)
            if nm:
                name = nm.group(1).strip()
                fixed_from_correction += 1

    data['name'] = name
    with open(jf, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not name:
        empty_name.append((jf.name, data.get('code', '')))
    updated += 1

print(f'Updated {updated} files')
print(f'Fixed from correction/shici: {fixed_from_correction}')
print(f'Still empty name: {len(empty_name)}')
for fn, code in empty_name:
    print(f'  {code}  {fn}')
