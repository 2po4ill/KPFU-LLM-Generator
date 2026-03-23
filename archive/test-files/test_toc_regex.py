"""
Test TOC extraction with regex (no LLM)
"""

import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.literature.processor import PDFProcessor

def test_regex_toc():
    """Test TOC extraction with regex only"""
    
    # Initialize
    pdf_path = Path('питон_мок_дата.pdf')
    processor = PDFProcessor()
    
    print("=" * 80)
    print("TESTING TOC EXTRACTION WITH REGEX (NO LLM)")
    print("=" * 80)
    
    # Extract text
    print("\n1. Extracting text from PDF...")
    result = processor.extract_text_from_pdf(pdf_path)
    
    if not result['success']:
        print(f"ERROR: {result['error']}")
        return
    
    print(f"   ✓ Extracted {result['total_pages']} pages")
    
    # Find TOC pages
    print("\n2. Finding TOC pages...")
    toc_pages = processor.find_toc_pages(result['pages'])
    print(f"   ✓ Found TOC on pages: {toc_pages}")
    
    # Get TOC text
    toc_text = '\n\n'.join([
        p['text'] for p in result['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    # Parse with regex
    print("\n3. Parsing TOC with regex...")
    toc_entries = processor.parse_table_of_contents(toc_text)
    
    print(f"\n   ✓ Extracted {len(toc_entries)} TOC entries")
    
    # Show all entries
    print("\n4. All TOC entries:")
    for i, entry in enumerate(toc_entries, 1):
        indent = "  " * (entry.level - 1)
        print(f"   {i}. {indent}[L{entry.level}] {entry.title} → page {entry.page_number}")
    
    # Check if we got the OOP entry
    print("\n5. Looking for OOP-related entries...")
    oop_entries = [e for e in toc_entries if 'ооп' in e.title.lower() or 'класс' in e.title.lower() or 'объект' in e.title.lower()]
    
    if oop_entries:
        print(f"   ✓ Found {len(oop_entries)} OOP-related entries:")
        for entry in oop_entries:
            print(f"      - {entry.title} → page {entry.page_number}")
    else:
        print("   ✗ No OOP entries found!")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_regex_toc()
