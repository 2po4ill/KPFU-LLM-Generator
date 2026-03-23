"""
Test batch parallel section generation (3 sections at a time)
Compare performance with current hardware resources (RTX 2060 12GB)
"""
import asyncio
import sys
import time
import psutil
import GPUtil
from pathlib import Path
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Test configuration
TEST_THEME = 'Работа со строками'
BOOK_CONFIG = {
    'path': 'питон_мок_дата.pdf',
    'title': 'A Byte of Python',
    'level': 'beginner'
}

# Shared components
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

def get_system_resources():
    """Get current system resource usage"""
    # CPU and Memory
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # GPU (if available)
    gpu_info = {}
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # RTX 2060
            gpu_info = {
                'name': gpu.name,
                'memory_used': gpu.memoryUsed,
                'memory_total': gpu.memoryTotal,
                'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                'gpu_load': gpu.load * 100
            }
    except:
        gpu_info = {'name': 'Not available'}
    
    return {
        'cpu_percent': cpu_percent,
        'memory_used_gb': memory.used / (1024**3),
        'memory_total_gb': memory.total / (1024**3),
        'memory_percent': memory.percent,
        'gpu': gpu_info
    }

async def generate_sections_batch_parallel(generator, theme, context):
    """Batch parallel approach: Generate sections in batches of 3"""
    print(f"\n🚀 BATCH PARALLEL SECTION GENERATION (3 at a time)")
    print(f"{'-'*60}")
    
    # Monitor resources before
    resources_before = get_system_resources()
    print(f"Resources before: CPU {resources_before['cpu_percent']:.1f}%, "
          f"RAM {resources_before['memory_percent']:.1f}%, "
          f"GPU {resources_before['gpu'].get('memory_percent', 0):.1f}%")
    
    start_time = time.time()
    
    # Stage 1: Generate outline (same as before)
    outline_start = time.time()
    outline = await generator._generate_outline(theme, context)
    outline_time = time.time() - outline_start
    print(f"  Outline generated: {outline_time:.1f}s ({len(outline)} sections)")
    
    # Stage 2: Generate sections in batches of 3
    sections_start = time.time()
    
    print(f"  Processing {len(outline)} sections in batches of 3...")
    
    all_sections = []
    batch_times = []
    
    # Split sections into batches of 3
    batch_size = 3
    for batch_start in range(0, len(outline), batch_size):
        batch_end = min(batch_start + batch_size, len(outline))
        batch_sections = outline[batch_start:batch_end]
        batch_num = (batch_start // batch_size) + 1
        
        print(f"\n  📦 Batch {batch_num}: Processing sections {batch_start+1}-{batch_end}")
        
        # Monitor GPU before batch
        gpu_before_batch = get_system_resources()['gpu'].get('memory_percent', 0)
        
        batch_time_start = time.time()
        
        # Create tasks for this batch
        batch_tasks = []
        for i, section_info in enumerate(batch_sections):
            section_index = batch_start + i + 1
            print(f"    Queuing section {section_index}: {section_info['title']}")
            
            task = generator._generate_section(
                theme, section_info, context, section_index, len(outline)
            )
            batch_tasks.append(task)
        
        # Execute batch in parallel
        print(f"    Executing {len(batch_tasks)} sections in parallel...")
        batch_results = await asyncio.gather(*batch_tasks)
        
        batch_time = time.time() - batch_time_start
        batch_times.append(batch_time)
        
        # Monitor GPU after batch
        gpu_after_batch = get_system_resources()['gpu'].get('memory_percent', 0)
        
        print(f"    Batch {batch_num} completed: {batch_time:.1f}s")
        print(f"    GPU usage: {gpu_before_batch:.1f}% → {gpu_after_batch:.1f}%")
        
        # Add results to all sections
        all_sections.extend(batch_results)
        
        # Brief pause between batches to let GPU cool down
        if batch_end < len(outline):
            print(f"    Cooling down GPU for 2s...")
            await asyncio.sleep(2)
    
    sections_time = time.time() - sections_start
    
    # Stage 3: Combine
    combine_start = time.time()
    final_content = "\n\n".join(all_sections)
    combine_time = time.time() - combine_start
    
    total_time = time.time() - start_time
    
    # Monitor resources after
    resources_after = get_system_resources()
    print(f"\nResources after: CPU {resources_after['cpu_percent']:.1f}%, "
          f"RAM {resources_after['memory_percent']:.1f}%, "
          f"GPU {resources_after['gpu'].get('memory_percent', 0):.1f}%")
    
    print(f"\n🚀 Batch Parallel Results:")
    print(f"  Outline time: {outline_time:.1f}s")
    print(f"  Sections time: {sections_time:.1f}s")
    print(f"  Batch times: {[f'{t:.1f}s' for t in batch_times]}")
    print(f"  Combine time: {combine_time:.1f}s")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Final words: {len(final_content.split()):,}")
    
    return {
        'total_time': total_time,
        'outline_time': outline_time,
        'sections_time': sections_time,
        'batch_times': batch_times,
        'combine_time': combine_time,
        'words': len(final_content.split()),
        'content': final_content,
        'resources_before': resources_before,
        'resources_after': resources_after
    }

async def setup_generator():
    """Setup generator with patched page selection"""
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=shared_model_manager,
        pdf_processor=shared_pdf_processor
    )
    
    # Get pages for context (simplified)
    pages_data = shared_pdf_processor.extract_text_from_pdf(BOOK_CONFIG['path'])
    
    if not pages_data['success']:
        raise Exception("Failed to extract pages")
    
    # Use first 10 pages as context (simplified for testing)
    context_pages = pages_data['pages'][:10]
    context = "\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['text']}"
        for p in context_pages
    ])
    
    return generator, context

async def main():
    print("BATCH PARALLEL SECTION GENERATION TEST")
    print("="*80)
    print(f"Theme: {TEST_THEME}")
    print(f"Book: {BOOK_CONFIG['title']}")
    print(f"Hardware: RTX 2060 12GB, Llama 3.1 8B")
    print(f"Batch Size: 3 sections at a time")
    print()
    
    # System info
    resources = get_system_resources()
    print(f"💻 SYSTEM RESOURCES:")
    print(f"  CPU: {psutil.cpu_count()} cores")
    print(f"  RAM: {resources['memory_total_gb']:.1f}GB total")
    print(f"  GPU: {resources['gpu'].get('name', 'Not detected')}")
    if 'memory_total' in resources['gpu']:
        print(f"  GPU Memory: {resources['gpu']['memory_total']}MB")
    print()
    
    # Initialize shared components
    await initialize_shared_components()
    
    # Setup generator and context
    print("🔧 Setting up generator and context...")
    generator, context = await setup_generator()
    print(f"✓ Context prepared: {len(context)} chars")
    
    # Test: Batch parallel generation
    print(f"\n{'='*80}")
    print("TEST: BATCH PARALLEL SECTION GENERATION")
    print("="*80)
    
    batch_result = await generate_sections_batch_parallel(generator, TEST_THEME, context)
    
    # Comparison with known baselines
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    
    # Known baselines
    original_baseline = 231.2  # From optimized test (shared ModelManager)
    full_parallel_result = 215.8  # From previous full parallel test
    
    batch_total = batch_result['total_time']
    batch_sections = batch_result['sections_time']
    
    improvement_vs_baseline = ((original_baseline - batch_total) / original_baseline) * 100
    improvement_vs_full_parallel = ((full_parallel_result - batch_total) / full_parallel_result) * 100
    
    print(f"\n📊 TIMING COMPARISON:")
    print(f"{'Approach':<25} {'Total Time':<12} {'Sections Time':<15} {'GPU Peak':<12}")
    print(f"{'-'*70}")
    print(f"{'Original Baseline':<25} {original_baseline:<12.1f} {'~150s':<15} {'~40%':<12}")
    print(f"{'Full Parallel':<25} {full_parallel_result:<12.1f} {'199.7s':<15} {'79.9%':<12}")
    print(f"{'Batch Parallel (3)':<25} {batch_total:<12.1f} {batch_sections:<15.1f} {batch_result['resources_after']['gpu'].get('memory_percent', 0):<12.1f}%")
    
    print(f"\n📈 IMPROVEMENT ANALYSIS:")
    print(f"  vs Original Baseline: {improvement_vs_baseline:+.1f}%")
    print(f"  vs Full Parallel: {improvement_vs_full_parallel:+.1f}%")
    
    # Batch efficiency analysis
    if len(batch_result['batch_times']) > 0:
        avg_batch_time = sum(batch_result['batch_times']) / len(batch_result['batch_times'])
        total_batch_time = sum(batch_result['batch_times'])
        
        print(f"\n🔍 BATCH ANALYSIS:")
        print(f"  Number of batches: {len(batch_result['batch_times'])}")
        print(f"  Average batch time: {avg_batch_time:.1f}s")
        print(f"  Total batch time: {total_batch_time:.1f}s")
        print(f"  Batch efficiency: {(batch_sections / total_batch_time) * 100:.1f}%")
    
    # GPU usage analysis
    gpu_before = batch_result['resources_before']['gpu'].get('memory_percent', 0)
    gpu_after = batch_result['resources_after']['gpu'].get('memory_percent', 0)
    gpu_delta = gpu_after - gpu_before
    
    print(f"\n📊 RESOURCE EFFICIENCY:")
    print(f"  GPU usage increase: {gpu_delta:.1f}% (vs 66.4% for full parallel)")
    
    if gpu_after < 70:
        print(f"  ✅ GPU HEADROOM: {gpu_after:.1f}% usage - sustainable for production")
    elif gpu_after < 85:
        print(f"  ⚠️ HIGH GPU USAGE: {gpu_after:.1f}% - manageable but monitor closely")
    else:
        print(f"  🚫 GPU OVERLOAD: {gpu_after:.1f}% - may cause instability")
    
    # Extrapolation to multi-book test
    print(f"\n🚀 EXTRAPOLATION TO MULTI-BOOK TEST:")
    
    # Previous results: 693.6s for 3 lectures with shared ModelManager
    optimized_baseline_3_lectures = 693.6
    optimized_baseline_9_lectures = optimized_baseline_3_lectures * 3  # 2080.8s
    
    if improvement_vs_baseline > 0:
        batch_optimized_9_lectures = optimized_baseline_9_lectures * (1 - improvement_vs_baseline/100)
        
        print(f"  Current optimized (9 lectures): {optimized_baseline_9_lectures/60:.1f} minutes")
        print(f"  With batch parallel: {batch_optimized_9_lectures/60:.1f} minutes")
        print(f"  Additional time saved: {(optimized_baseline_9_lectures - batch_optimized_9_lectures)/60:.1f} minutes")
        print(f"  Additional improvement: {improvement_vs_baseline:.1f}%")
        
        # Combined with model persistence (from original 52 minutes)
        original_52_minutes = 52 * 60  # 3120s
        model_persistence_improvement = 0.305  # 30.5% from previous test
        after_model_persistence = original_52_minutes * (1 - model_persistence_improvement)
        after_both_optimizations = after_model_persistence * (1 - improvement_vs_baseline/100)
        
        combined_improvement = ((original_52_minutes - after_both_optimizations) / original_52_minutes) * 100
        
        print(f"\n🎯 COMBINED OPTIMIZATION IMPACT:")
        print(f"  Original 9 lectures: 52.0 minutes")
        print(f"  After model persistence: {after_model_persistence/60:.1f} minutes")
        print(f"  After batch parallel: {after_both_optimizations/60:.1f} minutes")
        print(f"  Total time saved: {(original_52_minutes - after_both_optimizations)/60:.1f} minutes")
        print(f"  Combined improvement: {combined_improvement:.1f}%")
    
    # Production readiness assessment
    print(f"\n✅ PRODUCTION READINESS ASSESSMENT:")
    
    if improvement_vs_baseline > 15 and gpu_after < 70:
        print(f"  🎉 EXCELLENT: {improvement_vs_baseline:.1f}% improvement with sustainable GPU usage")
        print(f"  📋 RECOMMENDATION: Implement immediately in production")
    elif improvement_vs_baseline > 10 and gpu_after < 80:
        print(f"  ✅ GOOD: {improvement_vs_baseline:.1f}% improvement with manageable GPU usage")
        print(f"  📋 RECOMMENDATION: Implement with monitoring")
    elif improvement_vs_baseline > 5:
        print(f"  ⚠️ MODEST: {improvement_vs_baseline:.1f}% improvement - consider other optimizations first")
        print(f"  📋 RECOMMENDATION: Test in staging environment")
    else:
        print(f"  ❌ INSUFFICIENT: {improvement_vs_baseline:.1f}% improvement - not worth the complexity")
        print(f"  📋 RECOMMENDATION: Focus on other optimization strategies")
    
    print(f"\n✅ TEST COMPLETE")
    print(f"Batch parallel (3 sections) shows {improvement_vs_baseline:.1f}% improvement over baseline")

if __name__ == "__main__":
    asyncio.run(main())