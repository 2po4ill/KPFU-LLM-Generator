"""
Test asking LLM for page ranges instead of individual pages
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

async def test_range_prompt():
    print("=" * 80)
    print("TESTING RANGE-BASED PROMPT")
    print("=" * 80)
    
    # Initialize
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    
    # Load book
    book_path = 'питон_мок_дата.pdf'
    pages_data = pdf_processor.extract_text_from_pdf(book_path)
    
    # Get TOC
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    print(f"\nTOC length: {len(toc_text)} chars")
    
    # Test with string theme
    theme = "Работа со строками: форматирование, методы строк, срезы"
    
    prompt = f"""Оглавление книги:
...
14. Объектно-ориентированное программирование ... 101
14.1 self ... 102
14.2 Классы ... 103
...

Тема: ООП
Страницы: 101-112

---

Оглавление книги:
{toc_text}

Тема: {theme}
Страницы:"""
    
    print("\n" + "=" * 80)
    print("CALLING LLM...")
    print("=" * 80)
    
    llm_model = await model_manager.get_llm_model()
    
    response = await llm_model.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.0,
            "num_predict": 50
        }
    )
    
    response_text = response.get('response', '').strip()
    
    print("\nLLM Response:")
    print(response_text)
    
    # Parse ranges
    import re
    page_numbers = []
    
    patterns = re.findall(r'(\d+)(?:-(\d+))?', response_text)
    
    for match in patterns:
        start = int(match[0])
        if match[1]:  # Range
            end = int(match[1])
            for page in range(start, end + 1):
                if 0 <= page <= 200:
                    page_numbers.append(page)
        else:  # Single number
            if 0 <= start <= 200:
                page_numbers.append(start)
    
    page_numbers = sorted(set(page_numbers))
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    
    print(f"\nParsed page numbers: {page_numbers}")
    print(f"Total pages: {len(page_numbers)}")
    
    # Expected pages for strings
    expected = [36, 89]
    print(f"\nExpected pages: {expected}")
    
    found_36 = 36 in page_numbers
    found_89 = 89 in page_numbers
    
    print(f"\nFound page 36 (7.4 Строки): {'✓' if found_36 else '✗'}")
    print(f"Found page 89 (12.8 Ещё о строках): {'✓' if found_89 else '✗'}")
    
    if found_36 and found_89:
        print("\n✅ SUCCESS: Found both string sections!")
    elif found_36 or found_89:
        print("\n📝 PARTIAL: Found one section")
    else:
        print("\n❌ FAILED: Didn't find string sections")
    
    # Show page ranges
    if page_numbers:
        print("\n" + "=" * 80)
        print("PAGE RANGES:")
        print("=" * 80)
        
        # Group into ranges
        ranges = []
        start = page_numbers[0]
        prev = page_numbers[0]
        
        for page in page_numbers[1:]:
            if page == prev + 1:
                prev = page
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = page
                prev = page
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        
        print(f"\nRanges: {', '.join(ranges)}")

if __name__ == '__main__':
    asyncio.run(test_range_prompt())
