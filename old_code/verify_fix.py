# -*- coding: utf-8 -*-
"""验证 extract_all_corrections 能正确处理括号补充格式"""
import json, re

LQ = '\u201c'
RQ = '\u201d'

def extract_all_corrections(corr_text):
    if not corr_text: return {}
    items = {}
    patterns = [
        ('姓名',       r'姓名补充(?:填写|完善)为"([^"]+)"'),
        ('性别',       r'性别补充(?:填写|完善)为"([^"]+)"'),
        ('民族',       r'民族补充(?:填写|完善)为"([^"]+)"'),
        ('政治面貌',   r'政治面貌补充(?:填写|完善)为"([^"]+)"'),
        ('籍贯',       r'籍贯补充(?:填写|完善)为"([^"]+)"'),
        ('生前单位职务', r'生前（部队）单位及(?:曾任)?职务补充(?:填写|完善)为"([^"]*(?:"[^"]*)?)"'),
        ('出生时间',   r'出生(?:年月(?:日)?)?补充(?:填写|完善)为"([^"]+)"'),
        ('参加革命时间', r'参加革命[（工作]?(?:时间)?补充(?:填写|完善)为"([^"]+)"'),
        ('牺牲时间',   r'牺牲(?:年月(?:日)?)?补充(?:填写|完善)为"([^"]+)"'),
        ('牺牲地点',   r'牺牲地点补充(?:填写|完善)为"([^"]+)"'),
        ('牺牲原因',   r'牺牲原因补充(?:填写|完善)为"([^"]+)"'),
        ('事迹',       r'事迹补充(?:填写|完善)为"([^"]+)"'),
        ('出生时间',   r'出年时间补充(?:填写|完善)为"([^"]+)"'),
    ]
    for field, pat in patterns:
        m = re.search(pat, corr_text)
        if m:
            val = m.group(1).strip()
            after_quote = corr_text[m.end(1):]
            bracket_m = re.match(r'（[^）]+）', after_quote)
            if bracket_m:
                val = val + bracket_m.group(0)
            if val.count('"') > 1:
                val = val.replace('"', '')
            items[field] = val
    return items

# 从贾狗成 JSON 提取原始文本
with open('extracted_out/晋祁县001076_贾狗成.json', encoding='utf-8') as f:
    data = json.load(f)

md = data.get('markdown', '')
m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
corr_text = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

result = extract_all_corrections(corr_text)
print('提取结果:')
for k, v in result.items():
    print(f'  {k}: {v}')
