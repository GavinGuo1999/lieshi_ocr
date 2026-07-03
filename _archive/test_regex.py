# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

LQ = '\u201c'; RQ = '\u201d'

# Direct pattern matching approach - test on 000851 and 000942
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
    # 特殊写法
    ('出生时间', r'出年时间补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
    ('参加革命时间', r'参加革命（工作）时间补充(?:填写|完善)为' + LQ + r'([^' + RQ + r']+)' + RQ),
]

def extract_v2(corr_text):
    items = {}
    for field, pat in patterns:
        m = re.search(pat, corr_text)
        if m:
            items[field] = m.group(1).strip()
    return items

for code in ['晋祁县000851', '晋祁县000942']:
    for jf in sorted(Path(r'd:\ying_min_mineru\extracted_out').glob('*.json')):
        with open(jf, encoding='utf-8') as f:
            data = json.load(f)
        if data.get('code') != code: continue
        md = data.get('markdown','')
        m = re.search(r'修正内容及理由</td><td[^>]*>(.*?)(?=</td></tr>)', md, re.DOTALL)
        corr = re.sub(r'<[^>]+>','',m.group(1)).strip() if m else ''
        items = extract_v2(corr)
        print('[' + code + '] 提取结果:')
        for k, v in items.items():
            print('  ' + k + ': ' + repr(v[:50]))
        print()
        break
