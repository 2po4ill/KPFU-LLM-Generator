"""
Debug TOC parsing for new books
"""
from app.literature.processor import PDFProcessor
import sys
import re

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def debug_toc_parsing(book_path, book_name):
    """Debug TOC parsing for a specific book"""
    print(f"\n{'='*80}")
    print(f"DEBUGGING TOC PARSING: {book_name}")
    print(f"File: {book_path}")
    print(f"{'='*80}")
    
    pdf_processor = PDFProcessor()
    data = pdf_processor.extract_text_from_pdf(book_path)
    
    if not data['success']:
        print(f"❌ Failed to extract PDF")
        return
    
    # Find TOC pages
    toc_pages = pdf_processor.find_toc_pages(data['pages'])
    print(f"TOC pages: {toc_pages}")
    
    # Extract TOC text
    toc_text = '\n\n'.join([
        p['text'] for p in data['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    print(f"\nTOC text length: {len(toc_text)} characters")
    
    # Show first 1000 characters of TOC
    print(f"\nFirst 1000 characters of TOC:")
    print("-" * 60)
    print(toc_text[:1000])
    print("-" * 60)
    
    # Try different regex patterns
    print(f"\nTrying different TOC parsing patterns:")
    
    patterns = [
        # Original pattern
        (r'^(\d+(?:\.\d+)?)\s+(.+?)\s+[.\s]+(\d+)$', "Original pattern"),
        
        # More flexible patterns
        (r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)$', "Simple pattern"),
        (r'^(\d+(?:\.\d+)?)\s*[.\s]*(.+?)\s*[.\s]*(\d+)\s*$', "Flexible spacing"),
        (r'^(\d+(?:\.\d+)?)\s+(.+?)\s*\.+\s*(\d+)$', "Dots required"),
        (r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)\s*$', "End flexible"),
        
        # Different number formats
        (r'^(\d+)\s+(.+?)\s+(\d+)$', "Chapter only"),
        (r'^(\d+\.\d+)\s+(.+?)\s+(\d+)$', "Section only"),
        
        # Russian-specific
        (r'^(Глава\s+\d+|Раздел\s+\d+|\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)$', "Russian chapters"),
    ]
    
    lines = toc_text.split('\n')
    
    for pattern, description in patterns:
        print(f"\n{description}:")
        matches = 0
        sample_matches = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(pattern, line)
            if match:
                matches += 1
                if len(sample_matches) < 5:
                    sample_matches.append((match.group(1), match.group(2), match.group(3)))
        
        print(f"  Matches: {matches}")
        if sample_matches:
            print(f"  Sample matches:")
            for num, title, page in sample_matches:
                print(f"    {num:10s} {title[:40]:40s} → {page}")
        else:
            print(f"  No matches found")
    
    # Show sample lines for manual analysis
    print(f"\nSample TOC lines for manual analysis:")
    print("-" * 60)
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    for i, line in enumerate(non_empty_lines[:20]):
        print(f"{i+1:2d}: {line}")
    print("-" * 60)

def main():
    books = [
        ('Изучаем_Питон.pdf', 'Изучаем Python'),
        ('ООП_на_питоне.pdf', 'ООП на Python'),
        ('питон_мок_дата.pdf', 'A Byte of Python (working)')
    ]
    
    for book_path, book_name in books:
        debug_toc_parsing(book_path, book_name)

if __name__ == "__main__":
    main()