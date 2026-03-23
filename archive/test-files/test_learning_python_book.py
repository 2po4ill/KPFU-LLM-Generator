"""
Test the Learning Python book
"""
import asyncio
import sys
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def test_learning_python():
    """Test Learning Python book"""
    print("TESTING LEARNING PYTHON BOOK")
    print("="*50)
    
    # Initialize
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=model_manager,
        pdf_processor=pdf_processor
    )
    
    # Test TOC parsing
    print("1. Testing TOC parsing...")
    data = pdf_processor.extract_text_from_pdf('Изучаем_Питон.pdf')
    
    if not data['success']:
        print("❌ Failed to extract PDF")
        return
    
    toc_pages = pdf_processor.find_toc_pages(data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in data['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    print(f"TOC text length: {len(toc_text)} chars")
    
    # Test generator's parsing
    sections = generator._parse_toc_with_regex(toc_text)
    print(f"✓ Generator parsed {len(sections)} sections")
    
    if sections:
        print("Sample sections:")
        for section in sections[:5]:
            print(f"  {section['number']:6s} {section['title'][:40]:40s} → page {section['page']}")
        
        # Test LLM selection for Functions
        print(f"\n2. Testing LLM page selection for 'Функции'...")
        theme = "Функции"
        
        try:
            page_numbers = await generator._get_page_numbers_from_toc(theme, toc_text)
            print(f"✓ LLM selected pages: {page_numbers}")
            
            if page_numbers and page_numbers != [0]:
                print(f"✅ SUCCESS! Book is relevant for '{theme}'")
                return True
            else:
                print(f"❌ LLM says book not relevant")
                return False
        except Exception as e:
            print(f"❌ LLM selection failed: {e}")
            return False
    else:
        print("❌ No sections parsed")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_learning_python())
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")