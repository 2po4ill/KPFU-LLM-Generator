"""
Extract content from pages that were actually used for generation
"""
from app.literature.processor import PDFProcessor
import sys

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

pdf = PDFProcessor()
data = pdf.extract_text_from_pdf('питон_мок_дата.pdf')

# Pages that were used: [43, 44, 45, 46, 47, 49, 50, 87, 88, 89, 97, 98]
used_pages = [43, 44, 45, 46, 47, 49, 50, 87, 88, 89, 97, 98]

print("BOOK CONTENT FROM USED PAGES")
print("="*80)
print(f"Extracting content from {len(used_pages)} pages")
print("="*80)

all_content = []

for page_num in used_pages:
    page = next((p for p in data['pages'] if p['page_number'] == page_num), None)
    if page:
        text = page['text']
        all_content.append(f"\n{'='*80}\nPDF PAGE {page_num} (Book page {page_num - 8})\n{'='*80}\n{text}")

# Save to file
with open('book_content_used_pages.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(all_content))

print(f"\n✓ Extracted content from {len(used_pages)} pages")
print("✓ Saved to: book_content_used_pages.txt")
print(f"✓ Total characters: {sum(len(p['text']) for p in data['pages'] if p['page_number'] in used_pages)}")

# Show first page as preview
first_page = next((p for p in data['pages'] if p['page_number'] == used_pages[0]), None)
if first_page:
    print("\n" + "="*80)
    print(f"PREVIEW: PDF Page {used_pages[0]} (first 500 chars)")
    print("="*80)
    print(first_page['text'][:500])
