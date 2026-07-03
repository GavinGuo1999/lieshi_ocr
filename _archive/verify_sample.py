from rapidocr_onnxruntime import RapidOCR
import fitz, io
from PIL import Image
from pathlib import Path
import re, json

ocr = RapidOCR()
data_dir = Path(r'd:\ying_min_mineru\data')
extracted_dir = Path(r'd:\ying_min_mineru\extracted')
pdf_dir = Path(r'd:\ying_min_mineru\pdf')
ext_out_dir = Path(r'd:\ying_min_mineru\extracted_out')

all_json = sorted(extracted_dir.glob('*.pdf.json'))
all_json = [j for j in all_json if j.name not in ('ocr_codes.json', '_checkpoint.json')]

# Every 10th, plus last
sample_indices = list(range(0, len(all_json), 10))
if (len(all_json) - 1) not in sample_indices:
    sample_indices.append(len(all_json) - 1)

samples = [(all_json[i], i) for i in sample_indices]

print('Total: ' + str(len(all_json)) + ' | Sampling: ' + str(len(samples)))
print()

issues = []
correct = []

for jf, idx in samples:
    pdf_stem = jf.stem  # e.g. lieshi20260525_0004.pdf
    pdf_path = data_dir / pdf_stem

    with open(jf, encoding='utf-8') as f:
        data = json.load(f)

    expected_code = data.get('code', '')
    expected_name = data.get('name', '')
    expected_pdf_name = expected_code + '_' + (expected_name if expected_name else '无姓名') + '.pdf'
    expected_json_name = expected_pdf_name.replace('.pdf', '.json')

    pdf_renamed_exists = (pdf_dir / expected_pdf_name).exists()
    json_renamed_exists = (ext_out_dir / expected_json_name).exists()

    # Also check if JSON with old name still exists (shouldn't, after copy)
    old_json_exists = jf.exists()

    try:
        doc = fitz.open(pdf_path)
        p = doc[0]
        pw, ph = p.rect.width, p.rect.height
        pix = p.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes('png')))
        doc.close()

        sx, sy = img.width / pw, img.height / ph
        # Crop top-right for code
        cx0 = int(0.70 * pw * sx)
        cy0 = 0
        cx1 = img.width
        cy1 = int(0.15 * ph * sy)
        cropped = img.crop((cx0, cy0, cx1, cy1))
        crop_result, _ = ocr(cropped, return_img=False)
        crop_text = ' '.join(r[1] for r in crop_result) if crop_result else ''

        # Full page for name extraction from table
        full_result, _ = ocr(img, return_img=False)
        full_text = ' '.join(r[1] for r in full_result) if full_result else ''

        # Extract code from OCR
        actual_code = ''
        m = re.search(r'(晋祁县\d{6})', crop_text)
        if m:
            actual_code = m.group(1)
        else:
            m = re.search(r'(祁县\d{6})', crop_text)
            if m:
                actual_code = '晋' + m.group(1)

        # Extract name from MinerU markdown table
        name_from_md = ''
        for pat in [
            r'姓名[：:]*\s*</td><td[^>]*>([^<]{1,10}?)</td>',
            r'姓名[：:]*\s*</td>\s*<td[^>]*>([^<]{1,10}?)</td>',
        ]:
            m = re.search(pat, data.get('markdown', ''))
            if m and m.group(1).strip():
                name_from_md = m.group(1).strip()
                break

        code_ok = (actual_code == expected_code)
        name_ok = (name_from_md == expected_name)
        file_ok = pdf_renamed_exists and json_renamed_exists

        item_issues = []
        if not code_ok:
            item_issues.append('编号不符')
        if not name_ok:
            item_issues.append('姓名不符')
        if not file_ok:
            item_issues.append('文件名不对')

        item = {
            'idx': idx,
            'old_json': jf.name,
            'expected_code': expected_code,
            'actual_code': actual_code,
            'code_ok': code_ok,
            'expected_name': expected_name,
            'name_from_md': name_from_md,
            'name_ok': name_ok,
            'pdf_renamed': pdf_renamed_exists,
            'json_renamed': json_renamed_exists,
            'file_ok': file_ok,
            'expected_pdf': expected_pdf_name,
            'expected_json': expected_json_name,
            'issues': item_issues,
            'crop_text': crop_text[:120],
        }

        if item_issues:
            issues.append(item)
        else:
            correct.append(item)

        status = 'OK' if not item_issues else 'ISSUE: ' + ', '.join(item_issues)
        print('[' + str(idx) + '] ' + jf.name + ' -> ' + status)

    except Exception as e:
        print('ERROR [' + str(idx) + '] ' + jf.name + ': ' + str(e))
        issues.append({
            'idx': idx,
            'old_json': jf.name,
            'issues': ['处理出错: ' + str(e)],
            'expected_code': expected_code,
            'expected_name': expected_name,
        })

print()
print('========== 抽样审查汇总 ==========')
print('抽样数: ' + str(len(samples)) + ' | 通过: ' + str(len(correct)) + ' | 有问题: ' + str(len(issues)))
print()

if issues:
    print('=== 问题文件详情 ===')
    for item in issues:
        print('[' + str(item['idx']) + '] ' + item['old_json'])
        for iss in item['issues']:
            print('  问题: ' + iss)
        if 'expected_code' in item:
            print('  预期编号: ' + item['expected_code'] + ' | OCR实际: ' + item.get('actual_code', ''))
            print('  预期姓名: ' + item['expected_name'] + ' | 提取姓名: ' + item.get('name_from_md', ''))
            print('  预期PDF: ' + item.get('expected_pdf', ''))
            print('  预期JSON: ' + item.get('expected_json', ''))
            print('  PDF已重命名: ' + str(item.get('pdf_renamed', 'N/A')))
            print('  JSON已重命名: ' + str(item.get('json_renamed', 'N/A')))
            if 'crop_text' in item:
                print('  OCR原文: ' + item['crop_text'])
        print()
else:
    print('所有抽样文件均通过审查！')
