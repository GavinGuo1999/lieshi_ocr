# -*- coding: utf-8 -*-
"""
三方校验：PDF原文 vs JSON提取值 vs Excel值
随机抽20条，输出对照表供人工核对
"""
import json, re, random, openpyxl
from pathlib import Path

LQ = '\u201c'; RQ = '\u201d'

# 加载Excel
wb = openpyxl.load_workbook(r'd:\ying_min_mineru\《英名录》25版-排版-祁县-第一稿20260310B打印版-胡毅排3.13.xlsx')
ws = wb.active
code_to_row = {}
for row in range(2, ws.max_row+1):
    code = ws.cell(row, 2).value
    if code: code_to_row[str(code)] = row

# 随机抽20条
json_files = sorted(Path(r'd:\ying_min_mineru\extracted_out').glob('*.json'))
random.seed(42)
samples = random.sample(json_files, min(20, len(json_files)))

def n2(s):
    if s is None: return ''
    s = str(s).strip()
    s = s.replace('\\','/')
    s = re.sub(r'[\s\n\r]+', '', s)
    return s.lower()

def extract_corr(md):
    m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
    corr = re.sub(r'<[^>]+>','',m.group(1)).strip() if m else ''
    items = {}
    patterns = [
        ('姓名', r'姓名补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('性别', r'性别补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('民族', r'民族补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('政治面貌', r'政治面貌补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('籍贯', r'籍贯补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('生前单位职务', r'生前（部队）单位及(?:曾任)?职务补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('出生时间', r'出生(?:年月(?:日)?)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('参加革命时间', r'参加革命[（工作]?(?:时间)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('牺牲时间', r'牺牲(?:年月(?:日)?)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('牺牲地点', r'牺牲地点补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('牺牲原因', r'牺牲原因补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('事迹', r'事迹补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
        ('出生时间', r'出年时间补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
    ]
    for field, pat in patterns:
        m2 = re.search(pat, corr)
        if m2: items[field] = m2.group(1).strip()
    return items, corr

print(f"{'编号':<20} {'姓名':<8} {'字段':<14} {'PDF原文':<25} {'JSON修正':<25} {'Excel值':<25} {'JSON=Excel?':<10}")
print('-' * 120)

for jf in samples:
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    code = data.get('code','')
    if not code or code not in code_to_row: continue
    row = code_to_row[code]
    name = data.get('name','') or '??'
    corrections, corr_text = extract_corr(data.get('markdown',''))

    excel_row = {}
    for col in range(2, 15):
        excel_row[col] = ws.cell(row, col).value

    # 展示所有有修正的字段
    shown_fields = set()
    for col, field in [(4,'姓名'),(5,'性别'),(6,'籍贯'),(7,'出生时间'),(8,'参加革命时间'),(9,'政治面貌'),(10,'生前单位职务'),(11,'牺牲时间')]:
        pdf_val = corrections.get(field, '(无修正)')
        excel_val = str(excel_row[col] or '') if excel_row[col] else '(空)'
        same = '✓' if n2(excel_val) == n2(pdf_val) else '✗'
        print(f"{code:<20} {name:<8} {field:<14} {pdf_val[:20]:<25} {excel_val[:20]:<25} {same:<10}")
        shown_fields.add(field)
    print()
