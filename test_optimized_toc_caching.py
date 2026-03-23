"""
Test Optimized TOC Caching System
Validates the targeted page extraction strategy for massive performance improvement

EXPECTED RESULTS:
- Initialization: ~7s (vs 144s full PDF extraction)
- First lecture: ~12s total (7s init + 5s generation)
- Subsequent lectures: ~5s (cached TOC + targeted pages)
- 97% improvement for subsequent lectures
"""
import asyncio
import sys
import time
from pathlib import Path
from app.generation.generator_v3 import get_optimized_content_generator
from app.core.model_manager import ModelManager
from app.literature.processor import get_pdf_processor
from app.core.toc_cache import get_toc_cache

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Test configuration
TEST_THEMES = [
    'Работа со строками',
    'Основы ООП',
    'Функции в Python'
]
BOOK_CONFIG = {
    'path': 'Изучаем_Питон.pdf',
    'id': 'izuchaem_python',
    'title': 'Изучаем Python'
}

async def initialize_components():
    """Initialize components for testing"""
    print("🔧 Initializing components...")
    start_time = time.time()
    
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = get_pdf_processor()
    
    generator = await get_optimized_content_generator(model_manager, pdf_processor)
    
    init_time = time.time() - start_time
    print(f"✓ Components ready ({init_time:.1f}s)")
    
    return generator, model_manager, pdf_processor

async def test_book_initialization(generator):
    """Test book initialization performance"""
    
    print(f"\n📚 BOOK INITIALIZATION TEST")
    print(f"{'='*50}")
    print(f"Book: {BOOK_CONFIG['title']}")
    print(f"Expected: ~7s (vs 144s full extraction)")
    print()
    
    start_time = time.time()
    
    result = await generator.initialize_book(BOOK_CONFIG['path'], BOOK_CONFIG['id'])
    
    init_time = time.time() - start_time
    
    print(f"📊 INITIALIZATION RESULTS:")
    print(f"  Success: {result['success']}")
    print(f"  Time: {init_time:.1f}s")
    print(f"  Cached: {result.get('cached', False)}")
    
    if result['success'] and not result.get('cached', False):
        print(f"  TOC Pages: {result.get('toc_pages', [])}")
        print(f"  Page Offset: {result.get('page_offset', 0)}")
        
        # Performance analysis
        target_time = 7
        if init_time <= target_time:
            improvement = ((144 - init_time) / 144) * 100
            print(f"  ✅ SUCCESS: {improvement:.1f}% faster than full extraction!")
        else:
            overage = ((init_time - target_time) / target_time) * 100
            print(f"  ⚠️ OVER TARGET: {overage:.1f}% slower than expected")
    
    return result

async def test_optimized_generation(generator, theme_index, theme):
    """Test optimized lecture generation"""
    
    print(f"\n🚀 LECTURE GENERATION TEST #{theme_index + 1}")
    print(f"{'='*50}")
    print(f"Theme: {theme}")
    print(f"Expected: ~5s (cached TOC + targeted pages)")
    print()
    
    start_time = time.time()
    
    # Mock RPD data
    rpd_data = {
        'subject_title': 'Программирование на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информатики'
    }
    
    result = await generator.generate_lecture_optimized(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=[BOOK_CONFIG['id']]
    )
    
    generation_time = time.time() - start_time
    
    print(f"📊 GENERATION RESULTS:")
    print(f"  Success: {result.success}")
    print(f"  Total Time: {generation_time:.1f}s")
    print(f"  Content Length: {len(result.content):,} characters")
    print(f"  Word Count: {len(result.content.split()):,} words")
    
    if result.success:
        print(f"\n🔍 OPTIMIZATION METRICS:")
        print(f"  Cached Pages Used: {result.cached_pages_used}")
        print(f"  Extracted Pages: {result.extracted_pages_count}")
        print(f"  TOC Cache Hit: {result.toc_cache_hit}")
        
        print(f"\n⏱️ STEP TIMING:")
        for step, duration in result.step_times.items():
            print(f"    {step.replace('_', ' ').title()}: {duration:.1f}s")
        
        # Performance analysis
        if theme_index == 0:
            # First lecture (might include some initialization overhead)
            target_time = 12
            comparison_time = 147  # Original full approach
        else:
            # Subsequent lectures (should be very fast)
            target_time = 5
            comparison_time = 147
        
        if generation_time <= target_time:
            improvement = ((comparison_time - generation_time) / comparison_time) * 100
            print(f"\n  ✅ SUCCESS: {improvement:.1f}% faster than original approach!")
        else:
            overage = ((generation_time - target_time) / target_time) * 100
            print(f"\n  ⚠️ OVER TARGET: {overage:.1f}% slower than expected")
        
        # Cache efficiency
        total_pages = result.cached_pages_used + result.extracted_pages_count
        if total_pages > 0:
            cache_efficiency = (result.cached_pages_used / total_pages) * 100
            print(f"  📈 Cache Efficiency: {cache_efficiency:.1f}% ({result.cached_pages_used}/{total_pages} pages cached)")
    
    return result

async def test_cache_performance():
    """Test cache performance and statistics"""
    
    print(f"\n📊 CACHE PERFORMANCE TEST")
    print(f"{'='*50}")
    
    toc_cache = get_toc_cache()
    cache_stats = toc_cache.get_cache_stats()
    
    print(f"Cache Statistics:")
    print(f"  Total Books Cached: {cache_stats['total_books']}")
    print(f"  Total Cached Pages: {cache_stats['total_cached_pages']}")
    print(f"  Cache File Exists: {cache_stats['cache_file_exists']}")
    print(f"  Cached Books: {cache_stats['books']}")
    
    return cache_stats

async def main():
    print("OPTIMIZED TOC CACHING SYSTEM TEST")
    print("="*80)
    print("Testing targeted page extraction strategy:")
    print("• Book initialization: Extract first 30 pages, detect TOC, cache")
    print("• Lecture generation: Use cached TOC + extract only needed pages")
    print("• Expected: 97% performance improvement for subsequent lectures")
    print()
    
    # Initialize components
    generator, model_manager, pdf_processor = await initialize_components()
    
    # Test 1: Book initialization
    init_result = await test_book_initialization(generator)
    
    if not init_result['success']:
        print("❌ Book initialization failed, cannot continue tests")
        return
    
    # Test 2: Multiple lecture generations
    generation_results = []
    
    for i, theme in enumerate(TEST_THEMES):
        result = await test_optimized_generation(generator, i, theme)
        generation_results.append(result)
        
        if not result.success:
            print(f"❌ Generation failed for theme: {theme}")
    
    # Test 3: Cache performance
    cache_stats = await test_cache_performance()
    
    # COMPREHENSIVE ANALYSIS
    print(f"\n{'='*80}")
    print("COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("="*80)
    
    successful_generations = [r for r in generation_results if r.success]
    
    if successful_generations:
        # Calculate averages
        avg_time = sum(r.generation_time_seconds for r in successful_generations) / len(successful_generations)
        avg_cached_pages = sum(r.cached_pages_used for r in successful_generations) / len(successful_generations)
        avg_extracted_pages = sum(r.extracted_pages_count for r in successful_generations) / len(successful_generations)
        
        print(f"\n📈 PERFORMANCE SUMMARY:")
        print(f"  Successful Generations: {len(successful_generations)}/{len(TEST_THEMES)}")
        print(f"  Average Generation Time: {avg_time:.1f}s")
        print(f"  Average Cached Pages: {avg_cached_pages:.1f}")
        print(f"  Average Extracted Pages: {avg_extracted_pages:.1f}")
        
        # Compare with original approach
        original_time = 147  # From our previous tests
        improvement = ((original_time - avg_time) / original_time) * 100
        
        print(f"\n🚀 OPTIMIZATION IMPACT:")
        print(f"  Original Approach: {original_time}s per lecture")
        print(f"  Optimized Approach: {avg_time:.1f}s per lecture")
        print(f"  Performance Improvement: {improvement:.1f}%")
        
        if improvement >= 90:
            print(f"  🎉 EXCELLENT: Achieved target 90%+ improvement!")
        elif improvement >= 80:
            print(f"  ✅ VERY GOOD: Strong performance improvement")
        elif improvement >= 60:
            print(f"  ⚠️ GOOD: Significant improvement, room for optimization")
        else:
            print(f"  ❌ NEEDS WORK: Improvement below expectations")
        
        # Cache efficiency analysis
        total_pages_used = sum(r.cached_pages_used + r.extracted_pages_count for r in successful_generations)
        total_cached_pages = sum(r.cached_pages_used for r in successful_generations)
        
        if total_pages_used > 0:
            overall_cache_efficiency = (total_cached_pages / total_pages_used) * 100
            print(f"\n📊 CACHE EFFICIENCY:")
            print(f"  Overall Cache Hit Rate: {overall_cache_efficiency:.1f}%")
            
            if overall_cache_efficiency >= 80:
                print(f"  ✅ Excellent cache utilization")
            elif overall_cache_efficiency >= 60:
                print(f"  ⚠️ Good cache utilization")
            else:
                print(f"  ❌ Poor cache utilization - needs optimization")
    
    # Get detailed optimization stats
    opt_stats = generator.get_optimization_stats()
    
    print(f"\n🔍 DETAILED OPTIMIZATION STATS:")
    print(f"  Books Initialized: {len(opt_stats['initialization_times'])}")
    print(f"  Total Generations: {opt_stats['generation_count']}")
    
    if opt_stats['initialization_times']:
        for book_id, init_time in opt_stats['initialization_times'].items():
            print(f"    {book_id}: {init_time:.1f}s initialization")
    
    # FINAL ASSESSMENT
    print(f"\n{'='*80}")
    print("FINAL ASSESSMENT")
    print("="*80)
    
    if successful_generations and improvement >= 80:
        print(f"🎉 OPTIMIZATION SUCCESS!")
        print(f"   ✅ Performance: {improvement:.1f}% improvement achieved")
        print(f"   ✅ Cache: {overall_cache_efficiency:.1f}% efficiency")
        print(f"   ✅ Reliability: {len(successful_generations)}/{len(TEST_THEMES)} successful")
        print(f"   🚀 Ready for production deployment!")
    elif successful_generations and improvement >= 60:
        print(f"✅ GOOD OPTIMIZATION RESULTS")
        print(f"   ⚠️ Performance: {improvement:.1f}% improvement (target: 90%+)")
        print(f"   ✅ Functionality: System working correctly")
        print(f"   📈 Recommendation: Fine-tune for better performance")
    else:
        print(f"❌ OPTIMIZATION NEEDS WORK")
        print(f"   📊 Performance: {improvement:.1f}% improvement (below target)")
        print(f"   🔧 Recommendation: Review caching strategy and implementation")
    
    print(f"\n✅ OPTIMIZED TOC CACHING TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())