# -*- coding: utf-8 -*-
import json, re, openpyxl
from pathlib import Path

LQ = '\u201c'
RQ = '\u201d'

# ── 辅助函数 ───────────────────────────────────────────────
def normalize(s):
    if s is None:
        return ''
    s = str(s).strip()
    s = s.replace('\\', '/')
    s = s.replace('\uff08', '(').replace('\uff09', ')')
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'\s+', '', s)
    return s

def fields_match(excel_val, pdf_val):
    if not pdf_val:
        return True
    e = normalize(excel_val)
    p = normalize(pdf_val)
    return e == p

def parse_corrections(correction_text):
    if not correction_text:
        return {}
    corrections = {}

    m = re.search(r'姓名补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['姓名'] = m.group(1).strip()

    m = re.search(r'性别补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['性别'] = m.group(1).strip()

    m = re.search(r'籍贯补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['籍贯'] = m.group(1).strip()

    for pat in [
        r'出生(?:年月(?:日)?)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ,
        r'出年时间补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ,
    ]:
        m = re.search(pat, correction_text)
        if m:
            corrections['出生时间'] = m.group(1).strip()
            break

    m = re.search(r'参加革命[（工作]?(?:时间)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['参加革命时间'] = m.group(1).strip()

    m = re.search(r'政治面貌补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['政治面貌'] = m.group(1).strip()

    for pat in [
        r'生前（部队）单位及(?:曾任)?职务补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ,
        r'生前单位(?:及职务)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ,
    ]:
        m = re.search(pat, correction_text)
        if m:
            corrections['生前单位职务'] = m.group(1).strip()
            break

    m = re.search(r'牺牲(?:年月(?:日)?)?补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['牺牲时间'] = m.group(1).strip()

    m = re.search(r'牺牲地点补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['牺牲地点'] = m.group(1).strip()

    m = re.search(r'牺牲原因补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['牺牲原因'] = m.group(1).strip()

    m = re.search(r'事迹补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ, correction_text)
    if m:
        corrections['事迹'] = m.group(1).strip()

    return corrections

def extract_correction_text(markdown):
    m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', markdown, re.DOTALL)
    if not m:
        return ''
    return re.sub(r'<[^>]+>', '', m.group(1)).strip()

# ── Excel列映射 ────────────────────────────────────────────
EXCEL_COL_MAP = {
    4: '姓名',
    5: '性别',
    6: '籍贯',
    7: '出生时间',
    8: '参加革命时间',
    9: '政治面貌',
    10: '生前单位职务',
    11: '牺牲时间地点事迹',
}

# ── 1. 加载Excel ──────────────────────────────────────────
EXCEL_PATH = r'd:\ying_min_mineru\《英名录》25版-排版-祁县-第一稿20260310B打印版-胡毅排3.13.xlsx'
excel_wb = openpyxl.load_workbook(EXCEL_PATH)
excel_ws = excel_wb.active

excel_row_by_code = {}
for row in range(2, excel_ws.max_row + 1):
    code = excel_ws.cell(row, 2).value
    if code:
        excel_row_by_code[str(code)] = row

# ── 2. 全面比对 ───────────────────────────────────────────
ext_out_dir = Path(r'd:\ying_min_mineru\extracted_out')
results = []

for jf in sorted(ext_out_dir.glob('*.json')):
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    code = data.get('code', '')
    if not code:
        continue

    correction_text = extract_correction_text(data.get('markdown', ''))
    corrections = parse_corrections(correction_text)
    excel_row = excel_row_by_code.get(code)
    in_excel = excel_row is not None

    diffs = {}
    if in_excel:
        for col, field in EXCEL_COL_MAP.items():
            excel_val = excel_ws.cell(excel_row, col).value
            if field in corrections:
                if not fields_match(excel_val, corrections[field]):
                    diffs[field] = {'excel': excel_val, 'pdf': corrections[field]}
    else:
        diffs['__missing__'] = True

    results.append({
        'code': code,
        'name': data.get('name', ''),
        'in_excel': in_excel,
        'excel_row': excel_row,
        'corrections': corrections,
        'diffs': diffs
    })

# ── 3. 打印结果 ───────────────────────────────────────────
total_json = len(list(ext_out_dir.glob('*.json')))
in_excel_count = len([r for r in results if r['in_excel']])
not_in_excel_count = len([r for r in results if not r['in_excel']])
with_diffs = [r for r in results if r['in_excel'] and r['diffs'] and '__missing__' not in r['diffs']]
with_diffs_count = len(with_diffs)

print('总计JSON文件: ' + str(total_json))
print('在Excel中有对应行: ' + str(in_excel_count))
print('不在Excel中: ' + str(not_in_excel_count))
print('有差异的行: ' + str(with_diffs_count))
print()

# 差异字段统计
diff_field_count = {}
for r in with_diffs:
    for field in r['diffs']:
        diff_field_count[field] = diff_field_count.get(field, 0) + 1

print('=== 差异字段统计 ===')
for field, count in sorted(diff_field_count.items(), key=lambda x: -x[1]):
    print('  ' + field + ': ' + str(count) + '处差异')

print()
print('=== 不在Excel中的编号 ===')
missing_in_excel = [r for r in results if not r['in_excel']]
for r in missing_in_excel:
    print('  ' + r['code'] + ' (' + (r['name'] or '无姓名') + ')')

print()
print('=== 详细差异 ===')
print('共 ' + str(len(with_diffs)) + ' 行有差异:')
for r in with_diffs:
    print('')
    print(r['code'] + ' (Row' + str(r['excel_row']) + '):')
    for field, diff in r['diffs'].items():
        print('  ' + field + ':')
        print('    Excel: ' + (str(diff['excel'])[:120] if diff['excel'] else ''))
        print('    PDF:   ' + (str(diff['pdf'])[:120] if diff['pdf'] else ''))
