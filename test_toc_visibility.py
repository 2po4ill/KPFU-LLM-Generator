"""
Check what TOC text the LLM actually sees
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
    
    # Limit like in the code
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    print("=" * 80)
    print("TOC TEXT THAT LLM SEES")
    print("=" * 80)
    print(f"\nLength: {len(toc_text)} chars")
    print(f"Pages: {toc_page_numbers}")
    
    # Check if "Строки" (page 36) is in the text
    print("\n" + "=" * 80)
    print("SEARCHING FOR KEY SECTIONS")
    print("=" * 80)
    
    # Search for strings section
    if "7.4" in toc_text and "трок" in toc_text:
        print("\n✓ Found '7.4 Строки' section")
        # Find the line
        for line in toc_text.split('\n'):
            if "7.4" in line or ("трок" in line.lower() and "36" in line):
                print(f"  Line: {line.strip()}")
    else:
        print("\n✗ '7.4 Строки' NOT found in TOC text")
    
    # Search for "Ещё о строках" (page 89)
    if "12.8" in toc_text or ("щё" in toc_text and "трок" in toc_text):
        print("\n✓ Found '12.8 Ещё о строках' section")
        for line in toc_text.split('\n'):
            if "12.8" in line or ("щё" in line and "трок" in line.lower()):
                print(f"  Line: {line.strip()}")
    else:
        print("\n✗ '12.8 Ещё о строках' NOT found in TOC text")
    
    # Check if text is cut off
    print("\n" + "=" * 80)
    print("TOC TEXT END")
    print("=" * 80)
    print("\nLast 500 chars:")
    print(toc_text[-500:])
    
    # Check what page numbers are visible
    import re
    all_numbers = re.findall(r'\b(\d+)\b', toc_text)
    page_like_numbers = [int(n) for n in all_numbers if 10 <= int(n) <= 150]
    
    print("\n" + "=" * 80)
    print("PAGE NUMBERS IN TOC")
    print("=" * 80)
    print(f"\nAll page-like numbers (10-150): {sorted(set(page_like_numbers))}")
    
    if 36 in page_like_numbers:
        print("\n✓ Page 36 is visible in TOC")
    else:
        print("\n✗ Page 36 NOT visible in TOC")
    
    if 89 in page_like_numbers:
        print("✓ Page 89 is visible in TOC")
    else:
        print("✗ Page 89 NOT visible in TOC")

if __name__ == '__main__':
    main()
