"""
Test TOC encoding - save to file to verify
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.literature.processor import PDFProcessor

def main():
    processor = PDFProcessor()
    book_path = 'питон_мок_дата.pdf'
    
    # Extract pages
    pages_data = processor.extract_text_from_pdf(book_path)
    
    # Get TOC
    toc_page_numbers = processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    # Limit
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    # Save to file with UTF-8
    with open('toc_clean.txt', 'w', encoding='utf-8') as f:
        f.write(toc_text)
    
    print(f"TOC saved to toc_clean.txt ({len(toc_text)} chars)")
    print(f"TOC pages: {toc_page_numbers}")
    
    # Check if Cyrillic is present
    has_cyrillic = any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in toc_text)
    print(f"Contains Cyrillic: {has_cyrillic}")
    
    # Show first 500 chars
    print("\nFirst 500 chars:")
    print(toc_text[:500])

if __name__ == '__main__':
    main()
