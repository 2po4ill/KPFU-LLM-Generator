"""
Compare lecture generation across multiple books
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
        'level': 'beginner',
        'expected_strengths': ['basics', 'syntax', 'introduction']
    },
    'learning_python': {
        'path': 'Изучаем_Питон.pdf',
        'title': 'Изучаем Python',
        'level': 'intermediate',
        'expected_strengths': ['data_structures', 'functions', 'advanced_topics']
    },
    'oop_python': {
        'path': 'ООП_на_питоне.pdf',
        'title': 'ООП на Python',
        'level': 'advanced',
        'expected_strengths': ['classes', 'objects', 'oop_concepts']
    }
}

# Test themes for comparison
TEST_THEMES = [
    {
        'name': 'Работа со строками',
        'expected_best': 'learning_python',
        'reason': 'More comprehensive string coverage'
    },
    {
        'name': 'Функции',
        'expected_best': 'learning_python',
        'reason': 'Advanced function concepts'
    },
    {
        'name': 'Основы ООП',
        'expected_best': 'oop_python',
        'reason': 'Specialized OOP book'
    }
]

async def generate_lecture_with_book(theme, book_id, book_config):
    """Generate a lecture using a specific book"""
    print(f"\n{'-'*60}")
    print(f"Generating '{theme}' with {book_config['title']}")
    print(f"{'-'*60}")
    
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
        
        # Modify generator to use specific book
        original_book_path = 'питон_мок_дата.pdf'  # Default
        
        # Update the hardcoded path in generator (temporary hack)
        import types
        
        async def patched_step1_page_selection(self, theme, book_ids):
            # Use the specific book path
            book_path = book_config['path']
            
            selected_pages = []
            
            logger = self.pdf_processor.__class__.__module__.split('.')[0]  # Get logger
            
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
        
        # Patch the method
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
            print(f"  Words: {word_count}")
            print(f"  Confidence: {result.confidence_score:.0%}")
            
            # Save lecture for comparison
            safe_theme = theme.replace(' ', '_').replace('/', '_')
            filename = f"comparison_{safe_theme}_{book_id}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {theme}\n")
                f.write(f"**Book**: {book_config['title']}\n")
                f.write(f"**Level**: {book_config['level']}\n")
                f.write(f"**Generation Time**: {generation_time:.1f}s\n")
                f.write(f"**Word Count**: {word_count}\n")
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

async def compare_books_for_theme(theme_config):
    """Compare all books for a specific theme"""
    theme = theme_config['name']
    
    print(f"\n{'='*80}")
    print(f"MULTI-BOOK COMPARISON: {theme}")
    print(f"{'='*80}")
    
    results = {}
    
    for book_id, book_config in BOOKS.items():
        result = await generate_lecture_with_book(theme, book_id, book_config)
        results[book_id] = result
    
    # Analyze results
    print(f"\n{'='*80}")
    print(f"COMPARISON RESULTS: {theme}")
    print(f"{'='*80}")
    
    successful_results = {k: v for k, v in results.items() if v.get('success')}
    
    if successful_results:
        print(f"\n📊 Results Summary:")
        
        for book_id, result in successful_results.items():
            book_title = BOOKS[book_id]['title']
            print(f"\n{book_title}:")
            print(f"  Words: {result['words']:,}")
            print(f"  Confidence: {result['confidence']:.0%}")
            print(f"  Time: {result['time']:.1f}s")
            print(f"  File: {result['filename']}")
        
        # Determine best book
        if len(successful_results) > 1:
            # Score based on confidence and word count
            scored_results = []
            for book_id, result in successful_results.items():
                score = result['confidence'] * 0.7 + (result['words'] / 3000) * 0.3
                scored_results.append((book_id, score, result))
            
            scored_results.sort(key=lambda x: x[1], reverse=True)
            best_book_id, best_score, best_result = scored_results[0]
            
            print(f"\n🏆 BEST BOOK for '{theme}': {BOOKS[best_book_id]['title']}")
            print(f"   Score: {best_score:.2f}")
            print(f"   Confidence: {best_result['confidence']:.0%}")
            print(f"   Words: {best_result['words']:,}")
            
            # Compare with expectation
            expected_best = theme_config.get('expected_best')
            if expected_best == best_book_id:
                print(f"   ✅ Matches expectation!")
            else:
                expected_title = BOOKS.get(expected_best, {}).get('title', expected_best)
                print(f"   ⚠️ Expected: {expected_title}")
        
    else:
        print(f"\n❌ No successful results for '{theme}'")
    
    return results

async def main():
    print("MULTI-BOOK LECTURE COMPARISON")
    print("="*80)
    print("Testing lecture generation with different books")
    print("This will take ~15-20 minutes (3 themes × 3 books × ~5 min each)")
    print()
    
    all_results = {}
    
    for theme_config in TEST_THEMES:
        results = await compare_books_for_theme(theme_config)
        all_results[theme_config['name']] = results
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL MULTI-BOOK COMPARISON SUMMARY")
    print("="*80)
    
    for theme, results in all_results.items():
        successful = {k: v for k, v in results.items() if v.get('success')}
        
        print(f"\n{theme}:")
        
        if successful:
            # Find best book
            best_book = max(successful.items(), 
                          key=lambda x: x[1]['confidence'] * 0.7 + (x[1]['words'] / 3000) * 0.3)
            
            print(f"  Best: {BOOKS[best_book[0]]['title']}")
            print(f"  Quality: {best_book[1]['confidence']:.0%} confidence, {best_book[1]['words']:,} words")
            print(f"  Files generated: {len(successful)}")
        else:
            print(f"  ❌ No successful generations")
    
    print(f"\n📁 All comparison files saved in current directory")
    print(f"📊 Ready for detailed content analysis!")

if __name__ == "__main__":
    asyncio.run(main())