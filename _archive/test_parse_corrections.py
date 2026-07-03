import json, re
from pathlib import Path

ext_out_dir = Path(r'd:\ying_min_mineru\extracted_out')
jsons = sorted(ext_out_dir.glob('*.json'))

# 字段修正的正则模式
FIELD_PATTERNS = [
    ('姓名', re.compile(r'姓名补充完善为[''"'']([^''"'']+)[''"'']')),
    ('性别', re.compile(r'性别补充完善为[''"'']([^''"'']+)[''"'']')),
    ('籍贯', re.compile(r'籍贯补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('出生时间', re.compile(r'出生(?:年月(?:日)?)?补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('参加革命时间', re.compile(r'参加革命[（工作]?(?:时间)?补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('政治面貌', re.compile(r'政治面貌补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('民族', re.compile(r'民族补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('生前单位职务', re.compile(r'生前（部队）单位及(?:曾任)?职务补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('牺牲时间', re.compile(r'牺牲(?:年月(?:日)?)?补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('牺牲地点', re.compile(r'牺牲地点补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('牺牲原因', re.compile(r'牺牲原因补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('安葬地', re.compile(r'安葬[地]?补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
    ('事迹', re.compile(r'事迹补充(?:填写|完善)为[''"'']([^''"'']+)[''"'']')),
]

def parse_corrections(correction_text):
    """从修正内容及理由文本中提取各字段修正值"""
    if not correction_text:
        return {}
    corrections = {}
    for field, pattern in FIELD_PATTERNS:
        m = pattern.search(correction_text)
        if m:
            corrections[field] = m.group(1).strip()
    return corrections

# 测试解析效果
print('=== 解析测试（前10个JSON）===')
for jf in jsons[:10]:
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    # 从markdown中提取修正内容及理由
    md = data.get('markdown', '')
    # 找"修正内容及理由"后面的内容
    m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
    if m:
        correction_text = m.group(1)
        # 去掉HTML标签
        correction_text = re.sub(r'<[^>]+>', '', correction_text).strip()
    else:
        correction_text = ''

    corrections = parse_corrections(correction_text)
    print(f'\n{jf.stem}:')
    print(f'  原始姓名: {data.get("name", "")}')
    if corrections:
        for k, v in corrections.items():
            print(f'  修正-{k}: {v[:80]}...' if len(v) > 80 else f'  修正-{k}: {v}')
    else:
        print(f'  无修正内容 | 修正原文: {correction_text[:200]}')

print('\n=== 全部文件解析统计 ===')
all_corrections = {}
no_corrections = []
for jf in jsons:
    with open(jf, encoding='utf-8') as f:
        data = json.load(f)
    md = data.get('markdown', '')
    m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
    correction_text = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''
    corrections = parse_corrections(correction_text)
    if corrections:
        for k in corrections:
            all_corrections[k] = all_corrections.get(k, 0) + 1
    else:
        no_corrections.append(jf.stem)

print('各字段修正数量:')
for k, v in sorted(all_corrections.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}个')

print(f'\n无修正内容的文件: {len(no_corrections)}个')
if no_corrections:
    for n in no_corrections[:5]:
        print(f'  {n}')
