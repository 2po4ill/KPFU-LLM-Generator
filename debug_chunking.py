"""
Debug script to show exactly what chunks and prompts are being sent
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def debug_chunking():
    """Show exactly what's happening in the chunking process"""
    
    print("=" * 80)
    print("DEBUG: Chunking Process")
    print("=" * 80)
    
    # Initialize
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    # Extract PDF
    pdf_path = Path('питон_мок_дата.pdf')
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    # Get TOC
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    print(f"\n1. Original TOC length: {len(toc_text)} chars")
    
    # Step 1: Clean TOC
    cleaned_toc = generator._clean_toc_text(toc_text)
    print(f"\n2. After cleaning: {len(cleaned_toc)} chars")
    
    # Step 2: Chunk TOC
    chunks = generator._chunk_toc_by_chapters(cleaned_toc, chapters_per_chunk=5)
    print(f"\n3. Split into {len(chunks)} chunks")
    
    # Show each chunk
    theme = "Работа со строками: форматирование, методы строк, срезы"
    
    for i, chunk in enumerate(chunks):
        print(f"\n{'='*80}")
        print(f"CHUNK {i+1}/{len(chunks)}")
        print(f"{'='*80}")
        print(f"Length: {len(chunk)} chars")
        print(f"\nFirst 500 chars:")
        print(chunk[:500])
        print(f"\n... (truncated) ...")
        print(f"\nLast 500 chars:")
        print(chunk[-500:])
        
        # Build prompt
        prompt = f"""Найди в предоставленном оглавлении разделы, названия которых соответствуют теме "{theme}".

Правило определения страниц для раздела:
Номер страницы, указанный после названия раздела в оглавлении, является номером его начала. Раздел занимает все страницы от начальной страницы включительно и до страницы, СООТВЕТСТВУЮЩЕЙ началу следующего раздела того же или высшего уровня.

В ответе укажи номера ВСЕХ страниц, которые занимают эти разделы. Если раздел занимает несколько страниц подряд, укажи этот диапазон через дефис (например, 36-39).

ИГНОРИРУЙ СТАНДАРТНУЮ ЛОГИКУ ОГЛАВЛЕНИЙ. Если в оглавлении для раздела указан только один номер, но по правилу выше ему принадлежит несколько страниц, все равно укажи диапазон.

Раздели информацию по разным разделам запятой.

Формат ответа: строка с числами и дефисами. Например: 36-39, 89-91

Оглавление:
{chunk}

ТОЛЬКО диапазоны через запятую:"""
        
        print(f"\n{'='*80}")
        print(f"PROMPT FOR CHUNK {i+1}")
        print(f"{'='*80}")
        print(prompt)
        
        # Query LLM
        print(f"\n{'='*80}")
        print(f"QUERYING GEMMA 3 27B...")
        print(f"{'='*80}")
        
        llm_model = await model_manager.get_llm_model()
        response = await llm_model.generate(
            model="gemma3:27b",
            prompt=prompt,
            options={
                "temperature": 0.1,
                "num_predict": 100
            }
        )
        
        response_text = response.get('response', '').strip()
        print(f"\nRESPONSE: {response_text}")
        
        # Parse ranges
        ranges = generator._parse_page_ranges(response_text)
        print(f"PARSED RANGES: {ranges}")
        
        # Add buffer
        pages = generator._add_buffer_to_ranges(ranges, buffer_pages=1)
        print(f"PAGES WITH BUFFER: {pages}")
        
        print(f"\n{'='*80}\n")
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_chunking())
