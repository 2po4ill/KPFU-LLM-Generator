"""
Test page selection with OOP theme
Expected: pages 101-112 (Chapter 14: Object-Oriented Programming)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def test_oop_selection():
    print("=" * 80)
    print("Testing Gemma 3 27B - OOP Theme")
    print("=" * 80)
    
    # Initialize
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    # Extract PDF
    pdf_path = Path('питон_мок_дата.pdf')
    print(f"\n1. Extracting PDF: {pdf_path}")
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    print(f"   ✓ Extracted {len(pages_data['pages'])} pages")
    
    # Get TOC
    print(f"\n2. Finding TOC pages...")
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    print(f"   ✓ TOC pages: {toc_page_numbers}")
    
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    print(f"   ✓ TOC text length: {len(toc_text)} chars")
    
    # Test page selection
    theme = "Объектно-ориентированное программирование: классы, объекты, наследование"
    print(f"\n3. Testing page selection for theme: '{theme}'")
    
    page_numbers = await generator._get_page_numbers_from_toc(theme, toc_text)
    
    print(f"\n4. Results:")
    print(f"   Selected pages: {page_numbers}")
    print(f"   Total pages: {len(page_numbers)}")
    
    # Expected: Chapter 14 is on pages 101-112
    expected = list(range(101, 113))  # 101-112 inclusive
    
    if page_numbers == expected:
        print(f"   ✓ SUCCESS! Matches expected: {expected}")
    else:
        print(f"   ⚠ Different from expected: {expected}")
        missing = set(expected) - set(page_numbers)
        extra = set(page_numbers) - set(expected)
        if missing:
            print(f"   Missing: {missing}")
        if extra:
            print(f"   Extra: {extra}")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_oop_selection())
