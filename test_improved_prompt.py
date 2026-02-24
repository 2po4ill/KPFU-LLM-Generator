"""
Test improved TOC prompt to find string pages
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

async def test_prompt():
    print("=" * 80)
    print("TESTING IMPROVED TOC PROMPT")
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
    
    # Limit TOC size
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    print(f"\nTOC length: {len(toc_text)} chars")
    print(f"TOC pages: {toc_page_numbers}")
    
    # Test with string theme
    theme = "Работа со строками: форматирование, методы строк, срезы"
    
    prompt = f"""Вот оглавление книги по Python:

{toc_text}

Тема лекции: "{theme}"

ЗАДАЧА: Найди ВСЕ разделы в оглавлении, которые относятся к этой теме.

Ищи разделы по ключевым словам:
- Для "строки": ищи "Строки", "строк", "String"
- Для "ООП": ищи "Объектно-ориентированное", "Классы", "класс"
- Для "функции": ищи "Функции", "функц"
- Для "циклы": ищи "Цикл", "for", "while"

Посмотри на номера страниц справа от названий разделов.

Верни ТОЛЬКО номера страниц через запятую.
Пример: 36, 89

Номера страниц:"""
    
    print("\n" + "=" * 80)
    print("PROMPT:")
    print("=" * 80)
    print(prompt[:500])
    print("...")
    
    print("\n" + "=" * 80)
    print("CALLING LLM...")
    print("=" * 80)
    
    llm_model = await model_manager.get_llm_model()
    
    response = await llm_model.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.1,
            "num_predict": 200
        }
    )
    
    response_text = response.get('response', '').strip()
    
    print("\nLLM Response:")
    print(response_text)
    
    # Extract numbers
    import re
    numbers = re.findall(r'\d+', response_text)
    page_numbers = [int(n) for n in numbers if 0 <= int(n) <= 200]
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    
    print(f"\nExtracted page numbers: {page_numbers}")
    
    # Expected pages for strings
    expected = [36, 89]
    print(f"Expected pages: {expected}")
    
    # Check if we found them
    found_36 = 36 in page_numbers
    found_89 = 89 in page_numbers
    
    print(f"\nFound page 36 (7.4 Строки): {'✓' if found_36 else '✗'}")
    print(f"Found page 89 (12.8 Ещё о строках): {'✓' if found_89 else '✗'}")
    
    if found_36 and found_89:
        print("\n✅ SUCCESS: Found both string sections!")
    elif found_36 or found_89:
        print("\n📝 PARTIAL: Found one section, missing the other")
    else:
        print("\n❌ FAILED: Didn't find string sections")
    
    # Show what pages would be after expansion
    if page_numbers:
        print("\n" + "=" * 80)
        print("AFTER EXPANSION:")
        print("=" * 80)
        
        # Simulate expansion
        expanded = []
        for i, page in enumerate(page_numbers):
            expanded.append(page)
            if i < len(page_numbers) - 1:
                next_page = page_numbers[i + 1]
                gap = next_page - page
                if gap <= 10:
                    for p in range(page + 1, next_page):
                        expanded.append(p)
            else:
                for p in range(page + 1, page + 5):
                    expanded.append(p)
        
        expanded = sorted(set(expanded))
        print(f"\nExpanded pages: {expanded}")
        print(f"Total pages: {len(expanded)}")

if __name__ == '__main__':
    asyncio.run(test_prompt())
