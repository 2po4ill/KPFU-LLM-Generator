"""
Debug the TOC parsing issue in the LLM selection
"""
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator
import sys
import re

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def debug_toc_parsing_issue():
    print("DEBUGGING TOC PARSING ISSUE")
    print("="*60)
    
    # Test with "Изучаем Python" book
    book_path = 'Изучаем_Питон.pdf'
    
    pdf_processor = PDFProcessor()
    data = pdf_processor.extract_text_from_pdf(book_path)
    
    if not data['success']:
        print("❌ Failed to extract PDF")
        return
    
    # Get TOC
    toc_pages = pdf_processor.find_toc_pages(data['pages'])
    print(f"TOC pages: {toc_pages}")
    
    toc_text = '\n\n'.join([
        p['text'] for p in data['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    print(f"TOC text length: {len(toc_text)} chars")
    
    # Show first 2000 chars of TOC
    print(f"\nFirst 2000 chars of TOC:")
    print("-" * 60)
    print(toc_text[:2000])
    print("-" * 60)
    
    # Test the generator's TOC parsing method
    generator = ContentGenerator()
    
    # Test the _parse_toc_with_regex method
    sections = generator._parse_toc_with_regex(toc_text)
    print(f"\nGenerator parsed {len(sections)} sections")
    
    if sections:
        print("Sample sections:")
        for section in sections[:10]:
            print(f"  {section['number']:6s} {section['title'][:50]:50s} → page {section['page']}")
    else:
        print("❌ No sections parsed by generator!")
        
        # Try manual regex patterns
        print("\nTrying manual regex patterns:")
        
        patterns = [
            r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)$',
            r'^(.+?)\s+(\d+)$',
            r'(\d+)\s*$'
        ]
        
        lines = toc_text.split('\n')
        
        for i, pattern in enumerate(patterns):
            print(f"\nPattern {i+1}: {pattern}")
            matches = 0
            
            for line in lines[:50]:  # Check first 50 lines
                line = line.strip()
                if not line:
                    continue
                
                match = re.search(pattern, line)
                if match:
                    matches += 1
                    if matches <= 5:  # Show first 5 matches
                        print(f"  Match: {line}")
            
            print(f"  Total matches: {matches}")

if __name__ == "__main__":
    debug_toc_parsing_issue()