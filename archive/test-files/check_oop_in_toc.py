"""
Check TOC for OOP-related content
"""
from app.literature.processor import PDFProcessor
import sys
import re

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

pdf = PDFProcessor()
data = pdf.extract_text_from_pdf('питон_мок_дата.pdf')

# Find TOC pages
toc_page_numbers = pdf.find_toc_pages(data['pages'])

print("CHECKING TOC FOR OOP CONTENT")
print("="*80)
print(f"TOC pages: {toc_page_numbers}")
print()

# Get TOC text
toc_text = '\n\n'.join([
    p['text'] for p in data['pages'] 
    if p['page_number'] in toc_page_numbers
])

print("FULL TOC CONTENT:")
print("="*80)
print(toc_text)
print()

# Parse TOC with regex
print("\n" + "="*80)
print("PARSED TOC SECTIONS:")
print("="*80)

sections = []
lines = toc_text.split('\n')

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Pattern: section_number + title + dots/spaces + page_number
    match = re.match(r'^(\d+(?:\.\d+)?)\s+(.+?)\s+[.\s]+(\d+)$', line)
    
    if match:
        section_num = match.group(1)
        title = match.group(2).strip()
        page = int(match.group(3))
        
        sections.append({
            'number': section_num,
            'title': title,
            'page': page
        })
        
        print(f"{section_num:6s} {title:60s} → page {page}")

print(f"\nTotal sections parsed: {len(sections)}")

# Search for OOP-related keywords
print("\n" + "="*80)
print("SEARCHING FOR OOP-RELATED CONTENT:")
print("="*80)

oop_keywords = [
    'ООП',
    'объектно-ориентированное',
    'объектно-ориентированный',
    'класс',
    'классы',
    'объект',
    'объекты',
    'метод',
    'методы',
    'наследование',
    'инкапсуляция',
    'полиморфизм',
    'self',
    '__init__',
    'конструктор'
]

found_sections = []

for section in sections:
    title_lower = section['title'].lower()
    for keyword in oop_keywords:
        if keyword.lower() in title_lower:
            found_sections.append(section)
            break

if found_sections:
    print(f"\n✓ Found {len(found_sections)} OOP-related sections:")
    for section in found_sections:
        print(f"  {section['number']:6s} {section['title']:60s} → page {section['page']}")
else:
    print("\n✗ No OOP-related sections found in TOC")
    print("\nThis book may not cover OOP topics.")
    print("The book appears to be an introductory Python book focusing on basics.")

# Check last chapter
print("\n" + "="*80)
print("LAST CHAPTERS IN BOOK:")
print("="*80)

last_sections = sections[-10:] if len(sections) >= 10 else sections
for section in last_sections:
    print(f"{section['number']:6s} {section['title']:60s} → page {section['page']}")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

if found_sections:
    print("✓ OOP content is available in this book")
    print(f"  Sections: {', '.join([s['number'] for s in found_sections])}")
    print(f"  Pages: {', '.join([str(s['page']) for s in found_sections])}")
else:
    print("✗ This book does not appear to cover OOP topics")
    print("  Recommendation: Use a different book for OOP lecture")
    print("  Or: Skip OOP lecture for this course")
