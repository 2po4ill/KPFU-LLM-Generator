"""
Quick optimization test: 1 theme × 3 books = 3 lectures
Compare original vs optimized approach
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

# Single theme for quick test
TEST_THEME = 'Работа со строками'

async def generate_lecture_original_approach(theme, book_id, book_config):
    """Original approach: Create new ModelManager each time"""
    print(f"\n📊 ORIGINAL APPROACH: {book_config['title']}")
    print(f"{'-'*50}")
    
    start_time = time.time()
    
    try:
        # Create NEW instances each time (original approach)
        model_manager = ModelManager()
        await model_manager.initialize()  # ← MODEL LOADING HAPPENS HERE
        
        pdf_processor = PDFProcessor()
        
        generator = ContentGenerator(use_mock=False)
        await generator.initialize(
            model_manager=model_manager,
            pdf_processor=pdf_processor
        )
        
        # Patch generator to use specific book
        import types
        
        async def patched_step1_page_selection(self, theme, book_ids):
            book_path = book_config['path']
            selected_pages = []
            
            print(f"  Using book: {book_path}")
            
            # Load book
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                print(f"  ❌ Failed to extract pages")
                return []
            
            # Detect page offset
            page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
            print(f"  Page offset: {page_offset}")
            
            # Find TOC pages
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                print(f"  ⚠️ No TOC found")
                return []
            
            # Get TOC text
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            # Use LLM to get page numbers
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
            
            if not book_page_numbers or book_page_numbers == [0]:
                print(f"  Book not relevant")
                return []
            
            print(f"  Selected book pages: {len(book_page_numbers)}")
            
            # Apply offset
            pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
            
            # Load content
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
            
            print(f"  Final pages: {len(selected_pages)}")
            return selected_pages
        
        # Apply patch
        generator._step1_smart_page_selection = types.MethodType(patched_step1_page_selection, generator)
        
        rpd_data = {
            'subject': 'Программирование на Python',
            'degree': 'Бакалавриат',
            'profession': 'Информатика'
        }
        
        generation_start = time.time()
        
        result = await generator.generate_lecture(
            theme=theme,
            rpd_data=rpd_data,
            book_ids=[book_id]
        )
        
        generation_time = time.time() - generation_start
        total_time = time.time() - start_time
        
        if result.success:
            word_count = len(result.content.split())
            
            print(f"  ✅ Success!")
            print(f"  Total time: {total_time:.1f}s")
            print(f"  Generation time: {generation_time:.1f}s")
            print(f"  Initialization overhead: {total_time - generation_time:.1f}s")
            print(f"  Words: {word_count:,}")
            
            return {
                'success': True,
                'total_time': total_time,
                'generation_time': generation_time,
                'init_overhead': total_time - generation_time,
                'words': word_count,
                'confidence': result.confidence_score
            }
        else:
            print(f"  ❌ Failed: {result.errors}")
            return {'success': False, 'total_time': total_time}
            
    except Exception as e:
        total_time = time.time() - start_time
        print(f"  ❌ Exception: {e}")
        return {'success': False, 'total_time': total_time}

# Shared components for optimized approach
shared_model_manager = None
shared_pdf_processor = None

async def initialize_shared_components():
    """Initialize shared components once"""
    global shared_model_manager, shared_pdf_processor
    
    print("🔧 Initializing shared components...")
    start_time = time.time()
    
    shared_model_manager = ModelManager()
    await shared_model_manager.initialize()
    
    shared_pdf_processor = PDFProcessor()
    
    init_time = time.time() - start_time
    print(f"✓ Shared components ready ({init_time:.1f}s)")
    return init_time

async def generate_lecture_optimized_approach(theme, book_id, book_config):
    """Optimized approach: Reuse shared ModelManager"""
    print(f"\n🚀 OPTIMIZED APPROACH: {book_config['title']}")
    print(f"{'-'*50}")
    
    start_time = time.time()
    
    try:
        # Use shared components (NO MODEL LOADING)
        generator = ContentGenerator(use_mock=False)
        await generator.initialize(
            model_manager=shared_model_manager,  # ← REUSE SHARED
            pdf_processor=shared_pdf_processor   # ← REUSE SHARED
        )
        
        # Same patching logic as original
        import types
        
        async def patched_step1_page_selection(self, theme, book_ids):
            book_path = book_config['path']
            selected_pages = []
            
            print(f"  Using book: {book_path}")
            
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                print(f"  ❌ Failed to extract pages")
                return []
            
            page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
            print(f"  Page offset: {page_offset}")
            
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                print(f"  ⚠️ No TOC found")
                return []
            
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
            
            if not book_page_numbers or book_page_numbers == [0]:
                print(f"  Book not relevant")
                return []
            
            print(f"  Selected book pages: {len(book_page_numbers)}")
            
            pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
            
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
            
            print(f"  Final pages: {len(selected_pages)}")
            return selected_pages
        
        generator._step1_smart_page_selection = types.MethodType(patched_step1_page_selection, generator)
        
        rpd_data = {
            'subject': 'Программирование на Python',
            'degree': 'Бакалавриат',
            'profession': 'Информатика'
        }
        
        result = await generator.generate_lecture(
            theme=theme,
            rpd_data=rpd_data,
            book_ids=[book_id]
        )
        
        total_time = time.time() - start_time
        
        if result.success:
            word_count = len(result.content.split())
            
            print(f"  ✅ Success!")
            print(f"  Total time: {total_time:.1f}s")
            print(f"  Words: {word_count:,}")
            
            return {
                'success': True,
                'total_time': total_time,
                'words': word_count,
                'confidence': result.confidence_score
            }
        else:
            print(f"  ❌ Failed: {result.errors}")
            return {'success': False, 'total_time': total_time}
            
    except Exception as e:
        total_time = time.time() - start_time
        print(f"  ❌ Exception: {e}")
        return {'success': False, 'total_time': total_time}

async def main():
    print("QUICK OPTIMIZATION TEST")
    print("="*80)
    print(f"Theme: {TEST_THEME}")
    print(f"Books: {len(BOOKS)} books")
    print(f"Total lectures: 3 (1 theme × 3 books)")
    print()
    
    # Expected times based on previous test
    print("📊 EXPECTED TIMES (from previous 52-minute test):")
    expected_times = {
        'byte_of_python': 259.5,
        'learning_python': 426.4,
        'oop_python': 255.0
    }
    
    expected_total = sum(expected_times.values())
    print(f"  A Byte of Python: {expected_times['byte_of_python']:.1f}s")
    print(f"  Изучаем Python: {expected_times['learning_python']:.1f}s")
    print(f"  ООП на Python: {expected_times['oop_python']:.1f}s")
    print(f"  Expected total: {expected_total:.1f}s ({expected_total/60:.1f} minutes)")
    
    # Test 1: Original approach (new ModelManager each time)
    print(f"\n{'='*80}")
    print("TEST 1: ORIGINAL APPROACH (New ModelManager each time)")
    print("="*80)
    
    original_results = {}
    original_total_time = 0
    
    for book_id, book_config in BOOKS.items():
        result = await generate_lecture_original_approach(TEST_THEME, book_id, book_config)
        original_results[book_id] = result
        if result.get('success'):
            original_total_time += result['total_time']
    
    # Test 2: Optimized approach (shared ModelManager)
    print(f"\n{'='*80}")
    print("TEST 2: OPTIMIZED APPROACH (Shared ModelManager)")
    print("="*80)
    
    # Initialize shared components once
    shared_init_time = await initialize_shared_components()
    
    optimized_results = {}
    optimized_generation_time = 0
    
    for book_id, book_config in BOOKS.items():
        result = await generate_lecture_optimized_approach(TEST_THEME, book_id, book_config)
        optimized_results[book_id] = result
        if result.get('success'):
            optimized_generation_time += result['total_time']
    
    optimized_total_time = shared_init_time + optimized_generation_time
    
    # Comparison
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    
    print(f"\n📊 DETAILED RESULTS:")
    print(f"{'Book':<20} {'Original':<12} {'Optimized':<12} {'Improvement':<12}")
    print(f"{'-'*60}")
    
    total_improvement = 0
    successful_comparisons = 0
    
    for book_id in BOOKS.keys():
        orig = original_results.get(book_id, {})
        opt = optimized_results.get(book_id, {})
        
        if orig.get('success') and opt.get('success'):
            orig_time = orig['total_time']
            opt_time = opt['total_time']
            improvement = ((orig_time - opt_time) / orig_time) * 100
            
            print(f"{BOOKS[book_id]['title']:<20} {orig_time:<12.1f} {opt_time:<12.1f} {improvement:<12.1f}%")
            
            total_improvement += improvement
            successful_comparisons += 1
    
    print(f"{'-'*60}")
    
    if successful_comparisons > 0:
        avg_improvement = total_improvement / successful_comparisons
        
        print(f"\n📈 OVERALL PERFORMANCE:")
        print(f"  Original total time: {original_total_time:.1f}s ({original_total_time/60:.1f} min)")
        print(f"  Optimized total time: {optimized_total_time:.1f}s ({optimized_total_time/60:.1f} min)")
        print(f"  Time saved: {original_total_time - optimized_total_time:.1f}s ({(original_total_time - optimized_total_time)/60:.1f} min)")
        print(f"  Average improvement per lecture: {avg_improvement:.1f}%")
        
        overall_improvement = ((original_total_time - optimized_total_time) / original_total_time) * 100
        print(f"  Overall improvement: {overall_improvement:.1f}%")
        
        print(f"\n🎯 EXTRAPOLATION TO FULL 9-LECTURE TEST:")
        original_9_lectures = original_total_time * 3  # 9 lectures = 3 themes × 3 books
        optimized_9_lectures = shared_init_time + (optimized_generation_time * 3)
        
        print(f"  Original 9 lectures: {original_9_lectures:.1f}s ({original_9_lectures/60:.1f} min)")
        print(f"  Optimized 9 lectures: {optimized_9_lectures:.1f}s ({optimized_9_lectures/60:.1f} min)")
        print(f"  Projected time saved: {original_9_lectures - optimized_9_lectures:.1f}s ({(original_9_lectures - optimized_9_lectures)/60:.1f} min)")
        
        full_improvement = ((original_9_lectures - optimized_9_lectures) / original_9_lectures) * 100
        print(f"  Projected improvement: {full_improvement:.1f}%")
        
        print(f"\n✅ OPTIMIZATION VALIDATION:")
        if overall_improvement > 10:
            print(f"  🎉 Significant improvement achieved!")
        elif overall_improvement > 5:
            print(f"  ✅ Moderate improvement achieved")
        else:
            print(f"  ⚠️ Minimal improvement - investigate further")
    
    else:
        print(f"\n❌ No successful comparisons - check for errors")

if __name__ == "__main__":
    asyncio.run(main())