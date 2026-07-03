import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')
pdf_dir = Path(r'd:\ying_min_mineru\pdf')
ext_out_dir = Path(r'd:\ying_min_mineru\extracted_out')

expected_missing = {889, 912, 933, 940, 963, 1004, 1026, 1027}
all_expected_codes = set(range(850, 1091)) - expected_missing  # 233 codes

# Load all files
files_by_code = {}
no_code_files = []
for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    code = data.get('code', '')
    name = data.get('name', '')
    if not code:
        no_code_files.append((jf.name, name))
        continue
    m = re.match(r'^晋祁县(\d+)$', code)
    if not m:
        print('FORMAT ERROR: ' + jf.name + ' -> ' + code)
        continue
    num = int(m.group(1))
    files_by_code[num] = (jf.name, name)

actual_codes = set(files_by_code.keys())

# Check range
out_of_range = sorted([c for c in actual_codes if c < 850 or c > 1090])
missing_from_expected = sorted(all_expected_codes - actual_codes)
extra_vs_expected = sorted(actual_codes - all_expected_codes)

# File naming check
naming_errors = []
for num, (jf_name, name) in sorted(files_by_code.items()):
    code = '晋祁县%06d' % num
    fname_base = code + '_' + (name if name else '无姓名')
    pdf_ok = (pdf_dir / (fname_base + '.pdf')).exists()
    json_ok = (ext_out_dir / (fname_base + '.json')).exists()
    if not pdf_ok or not json_ok:
        naming_errors.append((num, code, name, fname_base, pdf_ok, json_ok))

print('========== 完整编号核对报告 ==========')
print()
print('理论范围: 晋祁县000850 - 晋祁县001090')
print('理论缺失: ' + str(sorted(expected_missing)))
print('理论文件数: ' + str(len(all_expected_codes)))
print()
print('实际文件数: ' + str(len(actual_codes)))
print('范围外编号: ' + str(out_of_range) if out_of_range else '无')
print()
print('--- 预期缺失 vs 实际缺失 ---')
if sorted(expected_missing) == missing_from_expected:
    print('缺失编号: 与预期完全一致  ' + str(sorted(expected_missing)))
else:
    print('预期缺失但实际存在: ' + str(sorted(expected_missing - set(missing_from_expected))))
    print('实际缺失但预期未列: ' + str(sorted(set(missing_from_expected) - expected_missing)))

print()
print('--- 各批次文件数 ---')
batches = [
    ('850-899', 850, 899),
    ('900-999', 900, 999),
    ('1000-1054', 1000, 1054),
    ('1055-1090', 1055, 1090),
]
for label, lo, hi in batches:
    codes_in = sorted([c for c in actual_codes if lo <= c <= hi])
    missing_in = sorted([c for c in range(lo, hi+1) if c in expected_missing])
    print('  ' + label + ': ' + str(len(codes_in)) + ' 个文件' + (' (缺失: ' + str(missing_in) + ')' if missing_in else ''))

print()
print('--- 文件命名检查 ---')
if naming_errors:
    print('发现 ' + str(len(naming_errors)) + ' 个命名不匹配:')
    for num, code, name, fname, pdf_ok, json_ok in naming_errors:
        print('  ' + code + ' (' + (name or '无姓名') + ')')
        print('    期望: ' + fname)
        print('    PDF: ' + str(pdf_ok) + ' | JSON: ' + str(json_ok))
else:
    print('所有 233 个文件的 PDF 和 JSON 均已正确命名')

print()
print('--- 无编号字段的文件 ---')
if no_code_files:
    for fn, name in no_code_files:
        print('  ' + fn + ' (' + name + ')')
else:
    print('无')

print()
print('--- 编号与姓名列表 ---')
for num, (jf_name, name) in sorted(files_by_code.items()):
    print('  晋祁县%06d  %s  <- %s' % (num, name or '(无姓名)', jf_name))
