"""
Test Gemma 3 27B chunked TOC implementation
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def test_gemma3_chunked():
    """Test the complete chunked TOC + Gemma 3 27B pipeline"""
    
    print("=" * 80)
    print("Testing Gemma 3 27B Chunked TOC Implementation")
    print("=" * 80)
    
    # Initialize components
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    # Test PDF
    pdf_path = Path('питон_мок_дата.pdf')
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return
    
    print(f"\n1. Extracting PDF: {pdf_path}")
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    if not pages_data['success']:
        print(f"ERROR: Failed to extract PDF")
        return
    
    print(f"   ✓ Extracted {pages_data['total_pages']} pages")
    
    # Find TOC
    print(f"\n2. Finding TOC pages...")
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    print(f"   ✓ TOC pages: {toc_page_numbers}")
    
    # Get TOC text
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    print(f"   ✓ TOC text length: {len(toc_text)} chars")
    
    # Test theme
    theme = "Работа со строками: форматирование, методы строк, срезы"
    print(f"\n3. Testing page selection for theme: '{theme}'")
    print(f"   Using model: Gemma 3 27B (free, local)")
    
    # Call the new method
    page_numbers = await generator._get_page_numbers_from_toc(theme, toc_text)
    
    print(f"\n4. Results:")
    print(f"   Selected pages: {page_numbers}")
    print(f"   Total pages: {len(page_numbers)}")
    
    # Expected: [36, 37, 38, 39, 89, 90, 91]
    expected = [36, 37, 38, 39, 89, 90, 91]
    
    if page_numbers == expected:
        print(f"   ✓ SUCCESS! Matches expected: {expected}")
    else:
        print(f"   ⚠ Different from expected: {expected}")
        print(f"   Missing: {set(expected) - set(page_numbers)}")
        print(f"   Extra: {set(page_numbers) - set(expected)}")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_gemma3_chunked())
