"""
Test to see actual content on pages to understand chunking
"""
import sys
sys.path.insert(0, 'app')

from literature.processor import PDFProcessor

def test_page_content():
    """Check what's actually on the pages we're selecting"""
    
    processor = PDFProcessor()
    
    # Extract text
    result = processor.extract_text_from_pdf('питон_мок_дата.pdf')
    
    if not result['success']:
        print(f"Error: {result['error']}")
        return
    
    pages_text = result['pages']
    
    # Check specific pages (OOP chapter)
    pages_to_check = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112]
    
    for page_num in pages_to_check:
        # Find page
        page_data = next((p for p in pages_text if p['page_number'] == page_num), None)
        
        if page_data:
            text = page_data['text']
            print(f"\n{'='*80}")
            print(f"PAGE {page_num} ({len(text)} chars)")
            print(f"{'='*80}")
            print(text[:1000])  # First 1000 chars
            print(f"\n... (total {len(text)} chars)")
            
            # Check for OOP keywords
            keywords = ['класс', 'объект', 'наследование', 'метод', '__init__', 'self']
            found = []
            for kw in keywords:
                count = text.lower().count(kw)
                if count > 0:
                    found.append(f"{kw}:{count}")
            
            print(f"Keywords found: {', '.join(found)}")

if __name__ == "__main__":
    test_page_content()
