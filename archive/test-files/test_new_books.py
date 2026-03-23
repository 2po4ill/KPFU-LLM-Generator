"""
Test the newly added books for compatibility and content
"""
from app.literature.processor import PDFProcessor
import sys

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Available books
BOOKS = {
    'byte_of_python': {
        'path': 'питон_мок_дата.pdf',
        'title': 'A Byte of Python (Russian)',
        'level': 'beginner'
    },
    'learning_python': {
        'path': 'Изучаем_Питон.pdf',
        'title': 'Изучаем Python',
        'level': 'intermediate'
    },
    'oop_python': {
        'path': 'ООП_на_питоне.pdf',
        'title': 'ООП на Python',
        'level': 'advanced'
    }
}

def test_book_compatibility(book_id, book_config):
    """Test if a book is compatible with our system"""
    print(f"\n{'='*80}")
    print(f"Testing: {book_config['title']}")
    print(f"File: {book_config['path']}")
    print(f"Level: {book_config['level']}")
    print(f"{'='*80}")
    
    try:
        pdf_processor = PDFProcessor()
        
        # Test PDF extraction
        print("1. Testing PDF extraction...")
        data = pdf_processor.extract_text_from_pdf(book_config['path'])
        
        if not data['success']:
            print(f"❌ PDF extraction failed: {data.get('error', 'Unknown error')}")
            return False
        
        print(f"✓ PDF extraction successful")
        print(f"  Total pages: {data['total_pages']}")
        print(f"  Total characters: {data['total_chars']:,}")
        
        # Test offset detection
        print("\n2. Testing offset detection...")
        offset = pdf_processor.detect_page_offset(data['pages'])
        print(f"✓ Page offset detected: {offset}")
        
        # Test TOC detection
        print("\n3. Testing TOC detection...")
        toc_pages = pdf_processor.find_toc_pages(data['pages'])
        print(f"✓ TOC pages found: {toc_pages}")
        
        if not toc_pages:
            print(f"⚠️ Warning: No TOC pages detected")
            return False
        
        # Extract and analyze TOC
        print("\n4. Analyzing TOC content...")
        toc_text = '\n\n'.join([
            p['text'] for p in data['pages'] 
            if p['page_number'] in toc_pages
        ])
        
        print(f"✓ TOC text extracted: {len(toc_text)} characters")
        
        # Parse TOC sections
        import re
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
        
        print(f"✓ Parsed {len(sections)} TOC sections")
        
        # Show sample sections
        print(f"\nSample TOC sections:")
        for i, section in enumerate(sections[:10]):
            print(f"  {section['number']:6s} {section['title'][:50]:50s} → page {section['page']}")
        
        if len(sections) > 10:
            print(f"  ... and {len(sections) - 10} more sections")
        
        # Check for OOP content (if this is OOP book)
        if 'oop' in book_id.lower():
            print(f"\n5. Checking OOP content...")
            oop_keywords = ['класс', 'объект', 'наследование', 'инкапсуляция', 'полиморфизм', 'self', '__init__']
            oop_sections = []
            
            for section in sections:
                title_lower = section['title'].lower()
                if any(keyword in title_lower for keyword in oop_keywords):
                    oop_sections.append(section)
            
            print(f"✓ Found {len(oop_sections)} OOP-related sections:")
            for section in oop_sections[:5]:
                print(f"  {section['number']:6s} {section['title']}")
        
        print(f"\n✅ Book '{book_config['title']}' is COMPATIBLE")
        return True
        
    except Exception as e:
        print(f"❌ Error testing book: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("TESTING NEW BOOKS FOR COMPATIBILITY")
    print("="*80)
    
    results = {}
    
    for book_id, book_config in BOOKS.items():
        compatible = test_book_compatibility(book_id, book_config)
        results[book_id] = {
            'compatible': compatible,
            'config': book_config
        }
    
    # Summary
    print(f"\n{'='*80}")
    print("COMPATIBILITY SUMMARY")
    print("="*80)
    
    compatible_books = []
    
    for book_id, result in results.items():
        status = "✅ Compatible" if result['compatible'] else "❌ Not Compatible"
        print(f"{result['config']['title']:30s} {status}")
        
        if result['compatible']:
            compatible_books.append(book_id)
    
    print(f"\nCompatible books: {len(compatible_books)}/{len(BOOKS)}")
    
    if len(compatible_books) >= 2:
        print(f"\n🎉 Ready for multi-book testing!")
        print(f"Available books: {', '.join(compatible_books)}")
        print(f"\nNext steps:")
        print(f"1. Run multi-book comparison: python compare_books.py")
        print(f"2. Generate lectures with different books")
        print(f"3. Measure quality improvements")
    else:
        print(f"\n⚠️ Need at least 2 compatible books for comparison")
    
    return compatible_books

if __name__ == "__main__":
    compatible_books = main()