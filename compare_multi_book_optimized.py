"""
Optimized multi-book comparison with shared model manager
"""
import asyncio
import sys
import time
from pathlib import Path
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Book configurations
BOOKS = {
    'byte_of_python': {
        'path': 'питон_мок_дата.pdf',
        'title': 'A Byte of Python',
        'level': 'beginner'
    },
    'learning_python': {
        'path': 'Изучаем_Питон.pdf',
        'title': 'Изучаем Python',
        'level': 'intermediate'
    },
    'oop_python': {
        'path': 'ООП_на_питоне.pdf',
        'title': 'ООП на Python',
        'level': 'advanced'
    }
}

# Test themes
TEST_THEMES = ['Работа со строками', 'Функции', 'Основы ООП']

# SHARED INSTANCES (KEY OPTIMIZATION)
shared_model_manager = None
shared_pdf_processor = None

async def initialize_shared_components():
    """Initialize shared components once"""
    global shared_model_manager, shared_pdf_processor
    
    print("🔧 Initializing shared components...")
    start_time = time.time()
    
    # Initialize model manager once
    shared_model_manager = ModelManager()
    await shared_model_manager.initialize()
    print(f"✓ ModelManager initialized ({time.time() - start_time:.1f}s)")
    
    # Initialize PDF processor once
    shared_pdf_processor = PDFProcessor()
    print(f"✓ PDFProcessor initialized")
    
    total_time = time.time() - start_time
    print(f"✓ Shared components ready ({total_time:.1f}s)")
    return total_time

async def generate_lecture_optimized(theme, book_id, book_config):
    """Generate lecture using shared components"""
    print(f"\n{'-'*60}")
    print(f"Generating '{theme}' with {book_config['title']}")
    print(f"{'-'*60}")
    
    try:
        # Use shared components (NO MODEL LOADING)
        generator = ContentGenerator(use_mock=False)
        await generator.initialize(
            model_manager=shared_model_manager,  # ← REUSE SHARED INSTANCE
            pdf_processor=shared_pdf_processor   # ← REUSE SHARED INSTANCE
        )
        
        # Patch generator to use specific book
        import types
        
        async def patched_step1_page_selection(self, theme, book_ids):
            book_path = book_config['path']
            selected_pages = []
            
            print(f"Using book: {book_path}")
            
            # Load book
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                print(f"❌ Failed to extract pages from {book_path}")
                return []
            
            # Detect page offset
            page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
            print(f"Page offset detected: {page_offset}")
            
            # Find TOC pages
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                print(f"⚠️ No TOC found for book, skipping")
                return []
            
            # Get raw TOC text
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            # Limit TOC text size
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            print(f"Using TOC text ({len(toc_text)} chars)")
            
            # Use LLM to get page numbers
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
            
            if not book_page_numbers or book_page_numbers == [0]:
                print(f"Book not relevant for theme '{theme}' (LLM returned 0)")
                return []
            
            print(f"LLM selected book page numbers: {book_page_numbers}")
            
            # Apply offset to convert book pages to PDF pages
            pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
            print(f"Converted to PDF page numbers: {pdf_page_numbers}")
            
            # Load content from these pages
            book_title = pages_data['metadata'].get('title', book_id)
            
            for page_num in pdf_page_numbers:
                page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
                
                if page_data:
                    selected_pages.append({
                        'book_id': book_id,
                        'book_title': book_title,
                        'page_number': page_num,
                        'content': page_data['text'],
                        'relevance_score': 1.0
                    })
                else:
                    print(f"⚠️ PDF page {page_num} not found")
            
            print(f"Selected {len(selected_pages)} pages: {sorted(set([p['page_number'] for p in selected_pages]))}")
            
            return selected_pages
        
        # Apply patch
        generator._step1_smart_page_selection = types.MethodType(patched_step1_page_selection, generator)
        
        rpd_data = {
            'subject': 'Программирование на Python',
            'degree': 'Бакалавриат',
            'profession': 'Информатика'
        }
        
        start_time = time.time()
        
        result = await generator.generate_lecture(
            theme=theme,
            rpd_data=rpd_data,
            book_ids=[book_id]
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            word_count = len(result.content.split())
            
            print(f"✅ Success!")
            print(f"  Time: {generation_time:.1f}s")
            print(f"  Words: {word_count:,}")
            print(f"  Confidence: {result.confidence_score:.0%}")
            
            # Save lecture for comparison
            safe_theme = theme.replace(' ', '_').replace('/', '_')
            filename = f"optimized_{safe_theme}_{book_id}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {theme}\n")
                f.write(f"**Book**: {book_config['title']}\n")
                f.write(f"**Level**: {book_config['level']}\n")
                f.write(f"**Generation Time**: {generation_time:.1f}s\n")
                f.write(f"**Word Count**: {word_count:,}\n")
                f.write(f"**Confidence**: {result.confidence_score:.0%}\n\n")
                f.write("---\n\n")
                f.write(result.content)
            
            print(f"  Saved: {filename}")
            
            return {
                'success': True,
                'time': generation_time,
                'words': word_count,
                'confidence': result.confidence_score,
                'content': result.content,
                'filename': filename
            }
        else:
            print(f"❌ Failed: {result.errors}")
            return {
                'success': False,
                'errors': result.errors
            }
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'errors': [str(e)]
        }

async def main():
    print("OPTIMIZED MULTI-BOOK LECTURE COMPARISON")
    print("="*80)
    print("Testing with shared model manager (no repeated model loading)")
    print()
    
    # Initialize shared components once
    init_time = await initialize_shared_components()
    
    all_results = {}
    total_generation_time = 0
    
    for theme in TEST_THEMES:
        print(f"\n{'='*80}")
        print(f"THEME: {theme}")
        print(f"{'='*80}")
        
        theme_results = {}
        
        for book_id, book_config in BOOKS.items():
            result = await generate_lecture_optimized(theme, book_id, book_config)
            theme_results[book_id] = result
            
            if result.get('success'):
                total_generation_time += result['time']
        
        all_results[theme] = theme_results
    
    # Final summary
    print(f"\n{'='*80}")
    print("OPTIMIZED PERFORMANCE SUMMARY")
    print("="*80)
    
    successful_generations = 0
    total_words = 0
    
    for theme, results in all_results.items():
        successful = {k: v for k, v in results.items() if v.get('success')}
        successful_generations += len(successful)
        
        if successful:
            avg_time = sum(r['time'] for r in successful.values()) / len(successful)
            total_words += sum(r['words'] for r in successful.values())
            
            print(f"\n{theme}:")
            print(f"  Successful: {len(successful)}/3")
            print(f"  Avg time: {avg_time:.1f}s")
            print(f"  Total words: {sum(r['words'] for r in successful.values()):,}")
    
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"  Initialization time: {init_time:.1f}s")
    print(f"  Total generation time: {total_generation_time:.1f}s")
    print(f"  Total time: {init_time + total_generation_time:.1f}s")
    print(f"  Successful generations: {successful_generations}/9")
    print(f"  Average per lecture: {total_generation_time/successful_generations:.1f}s")
    print(f"  Total words generated: {total_words:,}")
    
    print(f"\n🚀 IMPROVEMENT vs ORIGINAL:")
    original_total = 52 * 60  # 52 minutes in seconds
    new_total = init_time + total_generation_time
    improvement = ((original_total - new_total) / original_total) * 100
    print(f"  Original: {original_total/60:.1f} minutes")
    print(f"  Optimized: {new_total/60:.1f} minutes")
    print(f"  Improvement: {improvement:.1f}% faster")

if __name__ == "__main__":
    asyncio.run(main())