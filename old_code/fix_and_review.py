import json, re
from pathlib import Path

extracted_dir = Path(r'd:\ying_min_mineru\extracted')

with open(extracted_dir / 'ocr_codes.json', encoding='utf-8') as f:
    ocr_data = json.load(f)

MANUAL_MAP = {}
for i in range(1069, 1091):
    sub_num = '%04d' % (i - 1001)
    fname = 'lieshi2026064_' + sub_num + '.pdf.json'
    code = '晋祁县%06d' % i
    MANUAL_MAP[fname] = code

print('Manual corrections:')
for k in sorted(MANUAL_MAP.keys()):
    old = ocr_data.get(k, {}).get('code', 'NO ENTRY')
    print('  ' + k + ': ' + old + ' -> ' + MANUAL_MAP[k])

changes = 0
for fname, new_code in MANUAL_MAP.items():
    json_path = extracted_dir / fname
    if not json_path.exists():
        print('  WARNING: ' + fname + ' not found')
        continue
    if fname in ocr_data:
        ocr_data[fname]['code'] = new_code
        ocr_data[fname]['source'] = 'manual'
    else:
        ocr_data[fname] = {'code': new_code, 'ocr_text': '', 'source': 'manual'}
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    data['code'] = new_code
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    changes += 1

print('\nApplied ' + str(changes) + ' corrections')

with open(extracted_dir / 'ocr_codes.json', 'w', encoding='utf-8') as f:
    json.dump(ocr_data, f, ensure_ascii=False, indent=2)

all_codes = {}
no_code_files = []
errors = []

for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    code = data.get('code', '')
    md = data.get('markdown', '') or ''
    name_m = re.search(r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>', md)
    name = name_m.group(1).strip() if name_m else ''

    if not name:
        errors.append((jf.name, '姓名为空'))

    if code:
        if not re.match(r'^晋祁县\d{6}$', code):
            errors.append((jf.name, '编号格式异常: ' + code))
        else:
            if code not in all_codes:
                all_codes[code] = []
            all_codes[code].append((jf.name, name))
    else:
        no_code_files.append((jf.name, name))

dupes = {k: v for k, v in all_codes.items() if len(v) > 1}

total = len(list(extracted_dir.glob('*.pdf.json'))) - 2
print('\n========== 审查结果 ==========')
print('总文件: ' + str(total))
print('有有效编号: ' + str(len(all_codes)))
print('无编号: ' + str(len(no_code_files)))
print('编号重复: ' + str(len(dupes)))
print('其他错误: ' + str(len(errors)))

if no_code_files:
    print('\n--- 无编号 ---')
    for fn, name in no_code_files:
        print('  ' + fn + ' (' + name + ')')

if dupes:
    print('\n--- 编号重复 ---')
    for code, files in sorted(dupes.items()):
        for fn, name in files:
            print('  ' + code + ' <- ' + fn + ' (' + name + ')')

if errors:
    print('\n--- 其他错误 ---')
    for fn, msg in errors:
        print('  ' + fn + ': ' + msg)

print('\n--- 1068-1090 编号范围 ---')
for i in range(1068, 1091):
    code = '晋祁县%06d' % i
    files = all_codes.get(code, [])
    if files:
        for fn, name in files:
            print('  ' + code + ' <- ' + fn + ' (' + name + ')')
    else:
        print('  ' + code + ' <- MISSING')

batches = {}
for jf in sorted(extracted_dir.glob('*.pdf.json')):
    if jf.name in ('ocr_codes.json', '_checkpoint.json'):
        continue
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    code = data.get('code', '')
    if not code:
        continue
    m = re.match(r'^晋祁县(\d+)$', code)
    if not m:
        continue
    fname = jf.name[:-5]
    parts = fname.rsplit('_', 1)
    batch = '_'.join(parts[:-1]) if len(parts) > 1 else fname
    num = int(m.group(1))
    if batch not in batches:
        batches[batch] = []
    batches[batch].append((num, fname))

print('\n--- 批次编号连续性 ---')
for batch, items in sorted(batches.items()):
    items.sort()
    nums = [x[0] for x in items]
    print(batch + ': ' + str(nums[0]) + ' - ' + str(nums[-1]) + ' (' + str(len(nums)) + ' files)')
    gaps = []
    for idx in range(1, len(nums)):
        if nums[idx] - nums[idx-1] > 1:
            gaps.append((nums[idx-1], nums[idx], nums[idx]-nums[idx-1]-1))
    if gaps:
        for g in gaps:
            print('  GAP: ' + str(g[0]) + ' -> ' + str(g[1]) + ' (缺 ' + str(g[2]) + ' 个)')
            for miss in range(g[0]+1, g[1]):
                miss_code = '晋祁县%06d' % miss
                miss_files = all_codes.get(miss_code, [])
                if miss_files:
                    print('    ' + miss_code + ' -> ' + miss_files[0][0] + ' (' + miss_files[0][1] + ')')
                else:
                    print('    ' + miss_code + ' -> 未找到对应文件')
