from pathlib import Path

data = Path(r'd:\ying_min_mineru\data')
extracted = Path(r'd:\ying_min_mineru\extracted')

pdf_files = sorted(data.glob('*.pdf'))
print(f'Total PDF files in data: {len(pdf_files)}')
for f in pdf_files[:10]:
    print(f'  {f.name}')
print(f'... (showing first 10)')

json_files = sorted(extracted.glob('*.pdf.json'))
print(f'\nTotal JSON files in extracted: {len(json_files)}')
