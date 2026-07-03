#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
祁县烈士英名录 PDF 数据处理流水线 — 统一入口

用法：
  python run_pipeline.py extract        # 步骤1: PDF → JSON (MinerU)
  python run_pipeline.py ocr            # 步骤2: OCR 编号识别
  python run_pipeline.py merge          # 步骤3: 合并 OCR 结果
  python run_pipeline.py fix-codes      # 步骤4: 手动修正编号
  python run_pipeline.py names          # 步骤5: 姓名提取
  python run_pipeline.py organize       # 步骤6: 重命名 + 整理
  python run_pipeline.py compare        # 步骤7: Excel 比对 + 红字标注

  python run_pipeline.py full           # 一键执行全流程
  python run_pipeline.py status         # 查看当前数据状态
  python run_pipeline.py clean-stale    # 清理 _无姓名 残旧文件
"""
import sys
import json
from pathlib import Path

BASE_DIR = Path(r'd:\ying_min_mineru')
DATA_DIR = BASE_DIR / 'data'
EXTRACTED_DIR = BASE_DIR / 'extracted'
EXTRACTED_OUT_DIR = BASE_DIR / 'extracted_out'
PDF_DIR = BASE_DIR / 'pdf'
OUTPUT_DIR = BASE_DIR / 'output'


def status():
    """查看当前数据状态"""
    pdf_count = len(list(DATA_DIR.glob('*.pdf')))
    json_count = len([f for f in EXTRACTED_DIR.glob('*.pdf.json') if f.name not in ('ocr_codes.json',)])
    
    # 统计姓名
    names_found = 0
    names_empty = 0
    for f in EXTRACTED_DIR.glob('*.pdf.json'):
        if f.name in ('ocr_codes.json', '_checkpoint.json'):
            continue
        d = json.loads(f.read_text(encoding='utf-8'))
        if d.get('name', '').strip():
            names_found += 1
        else:
            names_empty += 1
    
    # 统计编号
    codes_found = 0
    codes_empty = 0
    for f in EXTRACTED_DIR.glob('*.pdf.json'):
        if f.name in ('ocr_codes.json', '_checkpoint.json'):
            continue
        d = json.loads(f.read_text(encoding='utf-8'))
        if d.get('code', '').strip():
            codes_found += 1
        else:
            codes_empty += 1
    
    # 整理后的文件
    out_json = len(list(EXTRACTED_OUT_DIR.glob('*.json')))
    out_pdf = len(list(PDF_DIR.glob('*.pdf')))
    
    # 输出文件
    outputs = list(OUTPUT_DIR.glob('*.xlsx'))
    
    print('=' * 50)
    print('  祁县烈士英名录 — 数据状态')
    print('=' * 50)
    print(f'  原始 PDF:         {pdf_count}')
    print(f'  提取 JSON:        {json_count}')
    print(f'  已识别编号:       {codes_found} / 缺编号: {codes_empty}')
    print(f'  已提取姓名:       {names_found} / 缺姓名: {names_empty}')
    print(f'  整理后 JSON:      {out_json}')
    print(f'  整理后 PDF:       {out_pdf}')
    print(f'  输出 Excel:       {len(outputs)}')
    if outputs:
        for o in outputs:
            size_kb = o.stat().st_size / 1024
            print(f'    - {o.name} ({size_kb:.0f} KB)')
    print()


def clean_stale():
    """清理 _无姓名 残旧文件"""
    for d in [EXTRACTED_OUT_DIR, PDF_DIR]:
        stale = list(d.glob('*无姓名*'))
        for f in stale:
            f.unlink()
            print(f'Deleted: {f.name}')
    if not stale:
        print('No stale files found.')
    print('Done.')


def run_script(script_name: str, description: str):
    """运行一个子脚本"""
    print(f'\n{"=" * 50}')
    print(f'  {description}')
    print(f'{"=" * 50}')
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        print(f'ERROR: {script_path} not found!')
        sys.exit(1)
    
    # 执行脚本
    exec(script_path.read_text(encoding='utf-8'), {'__name__': '__main__'})
    print(f'\n--- {description} 完成 ---')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        status()
    elif cmd == 'clean-stale':
        clean_stale()
    elif cmd == 'extract':
        run_script('extract_batch.py', '步骤1: PDF → JSON 提取 (MinerU Flash API)')
    elif cmd == 'ocr':
        run_script('batch_ocr_codes.py', '步骤2: OCR 编号识别 (RapidOCR)')
    elif cmd == 'merge':
        run_script('merge_codes.py', '步骤3: 合并 OCR 编号到 JSON')
    elif cmd == 'fix-codes':
        run_script('fix_and_review.py', '步骤4: 手动修正编号范围')
    elif cmd == 'names':
        run_script('add_names_v2.py', '步骤5: 姓名提取 (多策略)')
    elif cmd == 'organize':
        # 先清理再整理
        clean_stale()
        run_script('organize.py', '步骤6: 按编号+姓名重命名整理')
    elif cmd == 'compare':
        run_script('process_qixian.py', '步骤7: Excel 比对 + 红字标注')
    elif cmd == 'full':
        steps = [
            ('extract_batch.py', '步骤1: PDF → JSON 提取'),
            ('batch_ocr_codes.py', '步骤2: OCR 编号识别'),
            ('merge_codes.py', '步骤3: 合并 OCR 编号'),
            ('fix_and_review.py', '步骤4: 手动修正编号'),
            ('add_names_v2.py', '步骤5: 姓名提取'),
        ]
        for script, desc in steps:
            run_script(script, desc)
        
        # organize 前清理
        clean_stale()
        run_script('organize.py', '步骤6: 重命名整理')
        run_script('process_qixian.py', '步骤7: Excel 比对')
        
        print('\n' + '=' * 50)
        print('  全流程完成！')
        print('=' * 50)
        status()
    else:
        print(f'未知命令: {cmd}')
        print(__doc__)


if __name__ == '__main__':
    main()
