"""
Test page offset in full generation pipeline
"""
import asyncio
import sys
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def test_offset():
    print("Testing page offset in generation pipeline...")
    print("="*80)
    
    # Initialize components
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=model_manager,
        pdf_processor=pdf_processor
    )
    
    # Test with "Работа со строками" theme
    theme = "Работа со строками"
    print(f"\nTheme: {theme}")
    print("Expected: Should select pages around book page 36 (PDF page 44)")
    print()
    
    # Run page selection only
    selected_pages = await generator._step1_smart_page_selection(
        theme=theme,
        book_ids=['python_book']
    )
    
    print("\n" + "="*80)
    print("Results:")
    print("="*80)
    
    if selected_pages:
        pdf_pages = sorted(set([p['page_number'] for p in selected_pages]))
        print(f"\n✓ Selected {len(selected_pages)} pages")
        print(f"  PDF page numbers: {pdf_pages}")
        
        # Calculate book page numbers (reverse the offset)
        # We know offset = 8, so book_page = pdf_page - 8
        book_pages = [p - 8 for p in pdf_pages]
        print(f"  Book page numbers: {book_pages}")
        
        # Check if we got the right content
        print("\n" + "="*80)
        print("Content verification:")
        print("="*80)
        
        for page in selected_pages[:3]:  # Check first 3 pages
            text = page['content']
            has_strings = any(word in text for word in ['Строки', 'строк', 'string'])
            status = "✓" if has_strings else "✗"
            
            print(f"\n{status} PDF page {page['page_number']} (book page {page['page_number'] - 8})")
            print(f"  Contains string-related content: {has_strings}")
            print(f"  First 150 chars: {text[:150].replace(chr(10), ' ')}")
    else:
        print("\n✗ No pages selected")
    
    print("\n" + "="*80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_offset())
