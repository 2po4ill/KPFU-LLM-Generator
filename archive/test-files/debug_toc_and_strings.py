"""
Debug script to understand TOC structure and string content location
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.literature.processor import PDFProcessor

def main():
    print("=" * 80)
    print("TOC AND STRING CONTENT INVESTIGATION")
    print("=" * 80)
    
    processor = PDFProcessor()
    book_path = 'питон_мок_дата.pdf'
    
    # Extract all pages
    print("\n1. Extracting pages...")
    result = processor.extract_text_from_pdf(book_path)
    
    if not result['success']:
        print("Failed to extract pages")
        return
    
    pages = result['pages']
    print(f"   Total pages: {len(pages)}")
    
    # Find TOC pages
    print("\n2. Finding TOC pages...")
    toc_page_numbers = processor.find_toc_pages(pages)
    print(f"   TOC pages: {toc_page_numbers}")
    
    # Print TOC content
    print("\n3. TOC CONTENT:")
    print("=" * 80)
    for page_num in toc_page_numbers:
        page = next((p for p in pages if p['page_number'] == page_num), None)
        if page:
            print(f"\n--- PAGE {page_num} ---")
            print(page['text'][:1000])  # First 1000 chars
            print("...")
    
    # Search for "строк" in TOC
    print("\n" + "=" * 80)
    print("4. SEARCHING FOR 'СТРОК' IN TOC:")
    print("=" * 80)
    
    toc_text = '\n'.join([p['text'] for p in pages if p['page_number'] in toc_page_numbers])
    
    if "строк" in toc_text.lower():
        print("✓ Found 'строк' in TOC")
        # Find lines containing "строк"
        for line in toc_text.split('\n'):
            if "строк" in line.lower():
                print(f"  → {line.strip()}")
    else:
        print("✗ 'строк' NOT found in TOC")
    
    # Search all pages for string content
    print("\n" + "=" * 80)
    print("5. SEARCHING ALL PAGES FOR STRING CONTENT:")
    print("=" * 80)
    
    string_pages = []
    keywords = ["строк", "string", "format", "метод строк"]
    
    for page in pages:
        page_text_lower = page['text'].lower()
        
        # Check if page has significant string content
        keyword_count = sum(1 for kw in keywords if kw in page_text_lower)
        
        if keyword_count >= 2:  # At least 2 keywords
            string_pages.append(page['page_number'])
            
            # Check for specific string topics
            has_methods = "метод" in page_text_lower and "строк" in page_text_lower
            has_format = "format" in page_text_lower or "форматирование" in page_text_lower
            has_slicing = "срез" in page_text_lower or "slice" in page_text_lower
            
            topics = []
            if has_methods:
                topics.append("methods")
            if has_format:
                topics.append("formatting")
            if has_slicing:
                topics.append("slicing")
            
            print(f"Page {page['page_number']:3d}: {', '.join(topics) if topics else 'general'}")
    
    print(f"\nTotal pages with string content: {len(string_pages)}")
    print(f"Page numbers: {string_pages}")
    
    # Check specific pages mentioned
    print("\n" + "=" * 80)
    print("6. CHECKING SPECIFIC PAGES:")
    print("=" * 80)
    
    pages_to_check = [8, 12, 39]
    
    for page_num in pages_to_check:
        page = next((p for p in pages if p['page_number'] == page_num), None)
        if page:
            print(f"\n--- PAGE {page_num} ---")
            print(page['text'][:500])
            print("...")
            
            # Check what topics are on this page
            text_lower = page['text'].lower()
            topics = []
            if "строк" in text_lower:
                topics.append("strings")
            if "ооп" in text_lower or "класс" in text_lower:
                topics.append("OOP")
            if "функц" in text_lower:
                topics.append("functions")
            if "список" in text_lower:
                topics.append("lists")
            
            print(f"Topics: {', '.join(topics) if topics else 'unclear'}")
    
    # Analyze TOC structure
    print("\n" + "=" * 80)
    print("7. TOC STRUCTURE ANALYSIS:")
    print("=" * 80)
    
    # Try to extract chapter/section structure
    import re
    
    chapter_pattern = r'(\d+)\.\s*([А-Яа-яA-Za-z\s]+)\.+\s*(\d+)'
    
    chapters = []
    for line in toc_text.split('\n'):
        match = re.search(chapter_pattern, line)
        if match:
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip()
            page_num = match.group(3)
            chapters.append((chapter_num, chapter_title, page_num))
    
    if chapters:
        print("\nExtracted chapters:")
        for ch_num, title, page in chapters:
            print(f"  {ch_num}. {title} ... стр. {page}")
    else:
        print("\nCouldn't extract chapter structure with regex")
        print("TOC might have different format")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    print(f"\n1. TOC pages: {toc_page_numbers}")
    print(f"2. 'строк' in TOC: {'Yes' if 'строк' in toc_text.lower() else 'No'}")
    print(f"3. Pages with string content: {len(string_pages)}")
    print(f"4. String content distribution: {string_pages[:10]}{'...' if len(string_pages) > 10 else ''}")
    
    if len(string_pages) > 0:
        # Check if string content is concentrated or scattered
        if len(string_pages) > 5:
            gaps = [string_pages[i+1] - string_pages[i] for i in range(len(string_pages)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            
            if avg_gap < 3:
                print(f"5. Content type: CONCENTRATED (avg gap: {avg_gap:.1f} pages)")
            else:
                print(f"5. Content type: SCATTERED (avg gap: {avg_gap:.1f} pages)")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
