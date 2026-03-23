"""
Final test: Simple prompt with keywords
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

async def test():
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    
    book_path = 'питон_мок_дата.pdf'
    pages_data = pdf_processor.extract_text_from_pdf(book_path)
    
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    theme = "Работа со строками: форматирование, методы строк, срезы"
    
    prompt = f"""Оглавление:
{toc_text}

Тема: {theme}

Найди разделы про эту тему. Верни номера страниц этих разделов. ТОЛЬКО цифры через запятую.

Цифры:"""
    
    print("PROMPT:")
    print(prompt[:300])
    print("...\n")
    
    llm_model = await model_manager.get_llm_model()
    
    response = await llm_model.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.0,
            "num_predict": 150
        }
    )
    
    response_text = response.get('response', '').strip()
    print(f"LLM Response: {response_text}\n")
    
    import re
    numbers = re.findall(r'\d+', response_text)
    page_numbers = sorted(set([int(n) for n in numbers if 0 <= int(n) <= 200]))
    
    print(f"Extracted pages: {page_numbers}")
    print(f"Found 36: {'✓' if 36 in page_numbers else '✗'}")
    print(f"Found 89: {'✓' if 89 in page_numbers else '✗'}")

if __name__ == '__main__':
    asyncio.run(test())
