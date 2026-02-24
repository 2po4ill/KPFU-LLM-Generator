"""
Test page offset detection
"""
from app.literature.processor import PDFProcessor
import sys

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

print("Testing page offset detection...")
print("="*80)

pdf = PDFProcessor()
data = pdf.extract_text_from_pdf('питон_мок_дата.pdf')

if not data['success']:
    print("Failed to extract PDF")
    sys.exit(1)

# Test offset detection
offset = pdf.detect_page_offset(data['pages'])

print(f"\n✓ Detected offset: {offset}")
print(f"  This means: TOC page number + {offset} = PDF page number")
print(f"  Example: TOC page 36 → PDF page {36 + offset}")

# Verify with known examples
print("\n" + "="*80)
print("Verification:")
print("="*80)

test_cases = [
    (36, "7.4 Строки"),
    (28, "6.3 Выбор редактора"),
    (42, "Словари")  # Changed to a page that exists
]

for book_page, expected_content in test_cases:
    pdf_page = book_page + offset
    page = next((p for p in data['pages'] if p['page_number'] == pdf_page), None)
    
    if page:
        text = page['text']
        found = expected_content in text
        status = "✓" if found else "✗"
        
        print(f"\n{status} Book page {book_page} → PDF page {pdf_page}")
        print(f"  Expected: {expected_content}")
        print(f"  Found: {found}")
        
        if found:
            # Show context
            idx = text.find(expected_content)
            context = text[max(0, idx-50):idx+len(expected_content)+50]
            print(f"  Context: ...{context}...")
    else:
        print(f"\n✗ Book page {book_page} → PDF page {pdf_page} NOT FOUND")

print("\n" + "="*80)
print("Test complete!")
