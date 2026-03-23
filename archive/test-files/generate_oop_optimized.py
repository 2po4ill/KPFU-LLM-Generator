"""
Generate OOP lecture with optimized settings (faster)
"""
import asyncio
import sys
import time
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def generate_oop_optimized():
    """Generate OOP lecture with optimized settings"""
    print("OPTIMIZED OOP LECTURE GENERATION")
    print("="*60)
    print("Book: ООП на Python")
    print("Theme: Основы ООП")
    print("Optimization: Limited to 10 pages max")
    print()
    
    # Initialize
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=model_manager,
        pdf_processor=pdf_processor
    )
    
    # Patch generator to use OOP book with page limit
    import types
    
    async def optimized_page_selection(self, theme, book_ids):
        book_path = 'ООП_на_питоне.pdf'
        
        print(f"Loading book: {book_path}")
        
        # Load book
        pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
        
        if not pages_data['success']:
            print(f"❌ Failed to extract pages")
            return []
        
        # Detect offset
        page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
        print(f"✓ Page offset: {page_offset}")
        
        # Find TOC
        toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
        
        if not toc_page_numbers:
            print(f"❌ No TOC found")
            return []
        
        print(f"✓ TOC pages: {toc_page_numbers}")
        
        # Get TOC text
        toc_text = '\n\n'.join([
            p['text'] for p in pages_data['pages'] 
            if p['page_number'] in toc_page_numbers
        ])
        
        if len(toc_text) > 10000:
            toc_text = toc_text[:10000]
        
        print(f"✓ TOC text: {len(toc_text)} chars")
        
        # Get page numbers from LLM
        book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
        
        if not book_page_numbers or book_page_numbers == [0]:
            print(f"❌ Book not relevant")
            return []
        
        print(f"✓ LLM selected book pages: {book_page_numbers}")
        
        # OPTIMIZATION: Limit to first 10 pages for faster generation
        if len(book_page_numbers) > 10:
            book_page_numbers = book_page_numbers[:10]
            print(f"✓ Limited to first 10 pages: {book_page_numbers}")
        
        # Apply offset
        pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
        print(f"✓ PDF pages (with offset): {pdf_page_numbers}")
        
        # Load content
        selected_pages = []
        book_title = "ООП на Python"
        
        for page_num in pdf_page_numbers:
            page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
            
            if page_data:
                selected_pages.append({
                    'book_id': 'oop_book',
                    'book_title': book_title,
                    'page_number': page_num,
                    'content': page_data['text'],
                    'relevance_score': 1.0
                })
        
        print(f"✓ Selected {len(selected_pages)} pages")
        return selected_pages
    
    # Apply patch
    generator._step1_smart_page_selection = types.MethodType(optimized_page_selection, generator)
    
    rpd_data = {
        'subject': 'Программирование на Python',
        'degree': 'Бакалавриат',
        'profession': 'Информатика'
    }
    
    print("Generating lecture...")
    start_time = time.time()
    
    try:
        result = await generator.generate_lecture(
            theme="Основы ООП",
            rpd_data=rpd_data,
            book_ids=['oop_book']
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            word_count = len(result.content.split())
            
            print(f"\n✅ SUCCESS!")
            print(f"Time: {generation_time:.1f}s")
            print(f"Words: {word_count:,}")
            print(f"Confidence: {result.confidence_score:.0%}")
            
            # Save lecture
            filename = "oop_lecture_optimized.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Основы ООП\n")
                f.write(f"**Book**: ООП на Python (specialized book)\n")
                f.write(f"**Pages Used**: Limited to 10 pages for optimization\n")
                f.write(f"**Generation Time**: {generation_time:.1f}s\n")
                f.write(f"**Word Count**: {word_count:,}\n")
                f.write(f"**Confidence**: {result.confidence_score:.0%}\n\n")
                f.write("---\n\n")
                f.write(result.content)
            
            print(f"Saved: {filename}")
            
            # Compare with baseline
            print(f"\n📊 COMPARISON WITH BASELINE:")
            print(f"Baseline (A Byte of Python): 1,819 words")
            print(f"Optimized OOP book: {word_count:,} words")
            
            if word_count > 1819:
                improvement = ((word_count - 1819) / 1819) * 100
                print(f"Improvement: +{improvement:.1f}% more content")
            else:
                decrease = ((1819 - word_count) / 1819) * 100
                print(f"Change: -{decrease:.1f}% less content")
            
            # Show step times
            print(f"\n⏱️ STEP TIMES:")
            for step, time_taken in result.step_times.items():
                print(f"  {step}: {time_taken:.1f}s")
            
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

if __name__ == "__main__":
    success = asyncio.run(generate_oop_optimized())
    print(f"\nFinal Result: {'SUCCESS' if success else 'FAILED'}")