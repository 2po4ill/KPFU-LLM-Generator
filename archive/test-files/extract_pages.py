from app.literature.processor import PDFProcessor
import sys
import re

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

pdf = PDFProcessor()
data = pdf.extract_text_from_pdf('питон_мок_дата.pdf')

# Check a few pages to find the offset
print("Checking pages to find offset between PDF page numbers and book page numbers...")
print("="*80)

for pdf_page_num in [36, 40, 44, 45, 46]:
    page = next((p for p in data['pages'] if p['page_number'] == pdf_page_num), None)
    if page:
        # Try to extract the footer page number (колонтитул)
        text = page['text']
        # Look for page number at the end of text (usually last line)
        lines = text.strip().split('\n')
        last_lines = lines[-5:]  # Check last 5 lines
        
        # Try to find a standalone number (the footer page number)
        footer_num = None
        for line in reversed(last_lines):
            # Look for lines that are just a number or "number Chapter X"
            match = re.search(r'(\d+)\s*(?:Глава|Chapter|$)', line.strip())
            if match:
                footer_num = int(match.group(1))
                break
        
        print(f"\nPDF Page {pdf_page_num}:")
        print(f"  Footer number (колонтитул): {footer_num if footer_num else 'Not found'}")
        print(f"  First 100 chars: {text[:100].replace(chr(10), ' ')}")
        if footer_num:
            print(f"  → Offset: PDF {pdf_page_num} = Book page {footer_num} (offset = {pdf_page_num - footer_num})")
