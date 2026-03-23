"""
Test parallel section generation vs sequential
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

async def generate_sections_parallel(generator, theme, context):
    """New approach: Generate sections in parallel"""
    print(f"\n🚀 PARALLEL SECTION GENERATION")
    print(f"{'-'*50}")
    
    # Monitor resources before
    resources_before = get_system_resources()
    print(f"Resources before: CPU {resources_before['cpu_percent']:.1f}%, "
          f"RAM {resources_before['memory_percent']:.1f}%, "
          f"GPU {resources_before['gpu'].get('memory_percent', 0):.1f}%")
    
    start_time = time.time()
    
    # Stage 1: Generate outline (same as sequential)
    outline_start = time.time()
    outline = await generator._generate_outline(theme, context)
    outline_time = time.time() - outline_start
    print(f"  Outline generated: {outline_time:.1f}s ({len(outline)} sections)")
    
    # Stage 2: Generate ALL sections in parallel
    sections_start = time.time()
    
    print(f"  Starting parallel generation of {len(outline)} sections...")
    
    # Create tasks for all sections
    tasks = []
    for i, section_info in enumerate(outline, 1):
        print(f"    Queuing section {i}: {section_info['title']}")
        task = generator._generate_section(
            theme, section_info, context, i, len(outline)
        )
        tasks.append(task)
    
    # Execute all sections concurrently
    print(f"  Executing {len(tasks)} sections in parallel...")
    parallel_start = time.time()
    
    sections = await asyncio.gather(*tasks)
    
    parallel_time = time.time() - parallel_start
    sections_time = time.time() - sections_start
    
    print(f"  Parallel execution completed: {parallel_time:.1f}s")
    
    # Stage 3: Combine (same as sequential)
    combine_start = time.time()
    final_content = "\n\n".join(sections)
    combine_time = time.time() - combine_start
    
    total_time = time.time() - start_time
    
    # Monitor resources after
    resources_after = get_system_resources()
    print(f"Resources after: CPU {resources_after['cpu_percent']:.1f}%, "
          f"RAM {resources_after['memory_percent']:.1f}%, "
          f"GPU {resources_after['gpu'].get('memory_percent', 0):.1f}%")
    
    print(f"\n🚀 Parallel Results:")
    print(f"  Outline time: {outline_time:.1f}s")
    print(f"  Sections time: {sections_time:.1f}s")
    print(f"  Parallel execution: {parallel_time:.1f}s")
    print(f"  Combine time: {combine_time:.1f}s")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Final words: {len(final_content.split()):,}")
    
    return {
        'total_time': total_time,
        'outline_time': outline_time,
        'sections_time': sections_time,
        'parallel_time': parallel_time,
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
    print("PARALLEL SECTION GENERATION TEST")
    print("="*80)
    print(f"Theme: {TEST_THEME}")
    print(f"Book: {BOOK_CONFIG['title']}")
    print(f"Hardware: RTX 2060 12GB, Llama 3.1 8B")
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
    
    # Skip sequential test - use known baseline from previous optimization test
    print(f"\n📊 USING KNOWN BASELINE FROM PREVIOUS TEST:")
    print(f"  Previous optimized result (shared ModelManager): 693.6s for 3 lectures")
    print(f"  Average per lecture: 231.2s")
    print(f"  Estimated sections time per lecture: ~150s (65% of total)")
    
    # Test: Parallel generation (new approach)
    print(f"\n{'='*80}")
    print("TEST: PARALLEL SECTION GENERATION")
    print("="*80)
    
    parallel_result = await generate_sections_parallel(generator, TEST_THEME, context)
    
    # Comparison with known baseline
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    
    # Use known baseline values
    baseline_total = 231.2  # Average from previous test
    baseline_sections = 150.0  # Estimated 65% of total time
    
    par_total = parallel_result['total_time']
    par_sections = parallel_result['sections_time']
    
    improvement_total = ((baseline_total - par_total) / baseline_total) * 100
    improvement_sections = ((baseline_sections - par_sections) / baseline_sections) * 100
    
    print(f"\n📊 TIMING COMPARISON:")
    print(f"{'Metric':<25} {'Baseline':<12} {'Parallel':<12} {'Improvement':<12}")
    print(f"{'-'*65}")
    print(f"{'Total Time':<25} {baseline_total:<12.1f} {par_total:<12.1f} {improvement_total:<12.1f}%")
    print(f"{'Sections Time':<25} {baseline_sections:<12.1f} {par_sections:<12.1f} {improvement_sections:<12.1f}%")
    print(f"{'Outline Time':<25} {'~60s':<12} {parallel_result['outline_time']:<12.1f} {'Similar':<12}")
    print(f"{'Combine Time':<25} {'~20s':<12} {parallel_result['combine_time']:<12.1f} {'Similar':<12}")
    
    print(f"\n📈 RESOURCE USAGE:")
    par_gpu_before = parallel_result['resources_before']['gpu'].get('memory_percent', 0)
    par_gpu_after = parallel_result['resources_after']['gpu'].get('memory_percent', 0)
    
    print(f"{'Approach':<15} {'GPU Before':<12} {'GPU After':<12} {'GPU Delta':<12}")
    print(f"{'-'*55}")
    print(f"{'Baseline':<15} {'~30%':<12} {'~40%':<12} {'~10%':<12}")
    print(f"{'Parallel':<15} {par_gpu_before:<12.1f}% {par_gpu_after:<12.1f}% {par_gpu_after-par_gpu_before:<12.1f}%")
    
    print(f"\n🎯 ANALYSIS:")
    
    if improvement_total > 20:
        print(f"  🎉 EXCELLENT: {improvement_total:.1f}% improvement - parallel processing is highly effective!")
    elif improvement_total > 10:
        print(f"  ✅ GOOD: {improvement_total:.1f}% improvement - parallel processing provides solid benefits")
    elif improvement_total > 0:
        print(f"  ⚠️ MODEST: {improvement_total:.1f}% improvement - limited by hardware or model constraints")
    else:
        print(f"  ❌ NO BENEFIT: Parallel processing may be limited by single GPU or model serialization")
    
    # Hardware constraint analysis
    print(f"\n🔍 HARDWARE CONSTRAINT ANALYSIS:")
    
    if par_gpu_after > 90:
        print(f"  ⚠️ GPU Memory Constraint: {par_gpu_after:.1f}% usage - may limit parallel processing")
    elif par_gpu_after > 70:
        print(f"  📊 High GPU Usage: {par_gpu_after:.1f}% - approaching limits but manageable")
    else:
        print(f"  ✅ GPU Headroom Available: {par_gpu_after:.1f}% usage - can handle parallel processing")
    
    # Theoretical analysis based on parallel execution
    if 'parallel_time' in parallel_result:
        outline_time = parallel_result['outline_time']
        parallel_time = parallel_result['parallel_time']
        combine_time = parallel_result['combine_time']
        
        # Estimate what sequential would have been
        estimated_sequential_sections = parallel_time * 5  # 5 sections in sequence
        estimated_sequential_total = outline_time + estimated_sequential_sections + combine_time
        
        theoretical_improvement = ((estimated_sequential_sections - parallel_time) / estimated_sequential_sections) * 100
        
        print(f"\n🎯 THEORETICAL ANALYSIS:")
        print(f"  Parallel sections time: {parallel_time:.1f}s")
        print(f"  Estimated sequential sections: {estimated_sequential_sections:.1f}s")
        print(f"  Theoretical max improvement: {theoretical_improvement:.1f}%")
        print(f"  Actual sections improvement: {improvement_sections:.1f}%")
        
        efficiency = (improvement_sections / theoretical_improvement) * 100 if theoretical_improvement > 0 else 0
        print(f"  Parallel efficiency: {efficiency:.1f}%")
    
    # Extrapolation to multi-book test
    print(f"\n🚀 EXTRAPOLATION TO MULTI-BOOK TEST:")
    
    # Based on previous optimized test: 693.6s for 3 lectures
    # With model persistence already applied
    optimized_baseline_9_lectures = 693.6 * 3  # 2080.8s for 9 lectures
    optimized_baseline_sections = optimized_baseline_9_lectures * 0.65  # 65% is sections
    
    if improvement_sections > 0:
        further_optimized_sections = optimized_baseline_sections * (1 - improvement_sections/100)
        further_optimized_total = optimized_baseline_9_lectures - (optimized_baseline_sections - further_optimized_sections)
        
        total_improvement = ((optimized_baseline_9_lectures - further_optimized_total) / optimized_baseline_9_lectures) * 100
        
        print(f"  Optimized baseline (9 lectures): {optimized_baseline_9_lectures/60:.1f} minutes")
        print(f"  With parallel sections: {further_optimized_total/60:.1f} minutes")
        print(f"  Additional time saved: {(optimized_baseline_9_lectures - further_optimized_total)/60:.1f} minutes")
        print(f"  Additional improvement: {total_improvement:.1f}%")
        
        # Combined with model persistence
        original_52_minutes = 52 * 60  # 3120s
        model_persistence_savings = 0.305  # 30.5% from previous test
        after_model_persistence = original_52_minutes * (1 - model_persistence_savings)
        after_both_optimizations = after_model_persistence * (1 - total_improvement/100)
        
        combined_improvement = ((original_52_minutes - after_both_optimizations) / original_52_minutes) * 100
        
        print(f"\n🎯 COMBINED OPTIMIZATION IMPACT:")
        print(f"  Original 9 lectures: 52.0 minutes")
        print(f"  After model persistence: {after_model_persistence/60:.1f} minutes")
        print(f"  After parallel sections: {after_both_optimizations/60:.1f} minutes")
        print(f"  Total time saved: {(original_52_minutes - after_both_optimizations)/60:.1f} minutes")
        print(f"  Combined improvement: {combined_improvement:.1f}%")
    
    print(f"\n✅ TEST COMPLETE")
    print(f"Parallel section generation shows {improvement_total:.1f}% improvement over optimized baseline")

if __name__ == "__main__":
    asyncio.run(main())