"""
Test direct page number selection from raw TOC
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.literature.processor import PDFProcessor
from app.core.model_manager import ModelManager
from app.generation.generator import ContentGenerator

async def test_page_selection():
    """Test page selection from raw TOC"""
    
    # Initialize
    pdf_path = Path('питон_мок_дата.pdf')
    processor = PDFProcessor()
    model_manager = ModelManager()
    generator = ContentGenerator()
    await generator.initialize(model_manager=model_manager, pdf_processor=processor)
    
    print("=" * 80)
    print("TESTING PAGE SELECTION FROM RAW TOC")
    print("=" * 80)
    
    # Extract text
    print("\n1. Extracting text from PDF...")
    result = processor.extract_text_from_pdf(pdf_path)
    
    if not result['success']:
        print(f"ERROR: {result['error']}")
        return
    
    print(f"   ✓ Extracted {result['total_pages']} pages")
    
    # Find TOC pages
    print("\n2. Finding TOC pages...")
    toc_pages = processor.find_toc_pages(result['pages'])
    print(f"   ✓ Found TOC on pages: {toc_pages}")
    
    # Get raw TOC text
    toc_text = '\n\n'.join([
        p['text'] for p in result['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    print(f"   ✓ TOC text: {len(toc_text)} chars")
    
    # Test with OOP theme
    theme = "Основы ООП: Классы, объекты, методы, наследование"
    
    print(f"\n3. Asking LLM for page numbers about: {theme}")
    page_numbers = await generator._get_page_numbers_from_toc(theme, toc_text)
    
    print(f"\n   ✓ LLM returned {len(page_numbers)} page numbers:")
    print(f"      {page_numbers}")
    
    # Check if we got the correct OOP pages (should be around 101-112)
    if any(100 <= p <= 115 for p in page_numbers):
        print("\n   ✓ SUCCESS: Got pages in OOP range (101-112)!")
    else:
        print("\n   ✗ WARNING: No pages in expected OOP range (101-112)")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(test_page_selection())
