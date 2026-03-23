"""
Test lecture generation with a single book
"""
import asyncio
import sys
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def test_single_book(book_path, book_name, theme):
    """Test lecture generation with a specific book"""
    print(f"TESTING LECTURE GENERATION")
    print(f"Book: {book_name}")
    print(f"File: {book_path}")
    print(f"Theme: {theme}")
    print("="*60)
    
    try:
        # Initialize components
        model_manager = ModelManager()
        await model_manager.initialize()
        
        pdf_processor = PDFProcessor()
        
        generator = ContentGenerator(use_mock=False)
        await generator.initialize(
            model_manager=model_manager,
            pdf_processor=pdf_processor
        )
        
        # Temporarily modify the hardcoded book path
        # This is a hack - in production we'd have proper book management
        original_method = generator._step1_smart_page_selection
        
        async def patched_method(self, theme_arg, book_ids):
            # Replace hardcoded path with our test book
            import types
            
            # Get the original method code but use our book path
            selected_pages = []
            
            print(f"Loading book: {book_path}")
            
            # Load book
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                print(f"❌ Failed to extract pages from {book_path}")
                return []
            
            # Detect page offset
            page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
            print(f"✓ Page offset detected: {page_offset}")
            
            # Find TOC pages
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                print(f"❌ No TOC found")
                return []
            
            print(f"✓ TOC pages found: {toc_page_numbers}")
            
            # Get raw TOC text
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            # Limit TOC text size
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            print(f"✓ TOC text extracted: {len(toc_text)} chars")
            
            # Use LLM to get page numbers
            book_page_numbers = await self._get_page_numbers_from_toc(theme_arg, toc_text)
            
            if not book_page_numbers or book_page_numbers == [0]:
                print(f"❌ Book not relevant for theme '{theme_arg}'")
                return []
            
            print(f"✓ LLM selected book pages: {book_page_numbers}")
            
            # Apply offset
            pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
            print(f"✓ PDF pages (with offset): {pdf_page_numbers}")
            
            # Load content
            book_title = pages_data['metadata'].get('title', book_name)
            
            for page_num in pdf_page_numbers:
                page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
                
                if page_data:
                    selected_pages.append({
                        'book_id': 'test_book',
                        'book_title': book_title,
                        'page_number': page_num,
                        'content': page_data['text'],
                        'relevance_score': 1.0
                    })
            
            print(f"✓ Selected {len(selected_pages)} pages")
            return selected_pages
        
        # Patch the method
        import types
        generator._step1_smart_page_selection = types.MethodType(patched_method, generator)
        
        rpd_data = {
            'subject': 'Программирование на Python',
            'degree': 'Бакалавриат',
            'profession': 'Информатика'
        }
        
        print(f"\nGenerating lecture...")
        
        result = await generator.generate_lecture(
            theme=theme,
            rpd_data=rpd_data,
            book_ids=['test_book']
        )
        
        if result.success:
            word_count = len(result.content.split())
            
            print(f"\n✅ SUCCESS!")
            print(f"Time: {result.generation_time_seconds:.1f}s")
            print(f"Words: {word_count:,}")
            print(f"Confidence: {result.confidence_score:.0%}")
            
            # Save lecture
            safe_book = book_name.replace(' ', '_').replace('/', '_')
            safe_theme = theme.replace(' ', '_').replace('/', '_')
            filename = f"test_{safe_book}_{safe_theme}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {theme}\n")
                f.write(f"**Book**: {book_name}\n")
                f.write(f"**File**: {book_path}\n")
                f.write(f"**Words**: {word_count:,}\n")
                f.write(f"**Confidence**: {result.confidence_score:.0%}\n\n")
                f.write("---\n\n")
                f.write(result.content)
            
            print(f"Saved: {filename}")
            
            return True
        else:
            print(f"\n❌ FAILED!")
            for error in result.errors:
                print(f"Error: {error}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    # Test configurations
    tests = [
        ('Изучаем_Питон.pdf', 'Изучаем Python', 'Функции'),
        ('ООП_на_питоне.pdf', 'ООП на Python', 'Основы ООП'),
        ('питон_мок_дата.pdf', 'A Byte of Python', 'Работа со строками')  # Baseline
    ]
    
    print("SINGLE BOOK LECTURE TESTING")
    print("="*80)
    
    results = []
    
    for book_path, book_name, theme in tests:
        print(f"\n{'='*80}")
        success = await test_single_book(book_path, book_name, theme)
        results.append((book_name, theme, success))
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    successful = 0
    for book_name, theme, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {book_name:20s} - {theme}")
        if success:
            successful += 1
    
    print(f"\nSuccessful: {successful}/{len(tests)}")
    
    if successful > 0:
        print(f"\n🎉 Multi-book system is working!")
        print(f"Ready for comprehensive comparison testing")
    else:
        print(f"\n⚠️ Need to fix issues before proceeding")

if __name__ == "__main__":
    asyncio.run(main())