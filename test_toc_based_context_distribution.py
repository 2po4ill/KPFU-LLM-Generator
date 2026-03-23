"""
Test TOC-based context distribution for parallel processing
Based on user's insight: use TOC structure to tag pages with lecture section types
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

def create_toc_based_page_tags(toc_entries, selected_pages):
    """Create page tags based on TOC structure - user's brilliant idea!"""
    
    print(f"\n🏷️ Creating TOC-based page tags...")
    print(f"TOC entries: {len(toc_entries)}")
    print(f"Selected pages: {[p['page_number'] for p in selected_pages]}")
    
    page_tags = {}
    
    for page in selected_pages:
        page_num = page['page_number']
        
        # Find which TOC section this page belongs to
        toc_section = None
        for entry in toc_entries:
            if entry['page'] <= page_num <= entry.get('end_page', entry['page'] + 10):
                toc_section = entry
                break
        
        if toc_section:
            # Map TOC section title to lecture section type
            lecture_section = map_toc_to_lecture_section(toc_section['title'])
            page_tags[page_num] = {
                'lecture_section': lecture_section,
                'toc_title': toc_section['title'],
                'toc_number': toc_section['number']
            }
            print(f"  Page {page_num}: '{toc_section['title']}' → {lecture_section}")
        else:
            # Fallback: position-based tagging
            lecture_section = get_position_based_tag(page_num, selected_pages)
            page_tags[page_num] = {
                'lecture_section': lecture_section,
                'toc_title': 'Unknown',
                'toc_number': 'N/A'
            }
            print(f"  Page {page_num}: No TOC match → {lecture_section} (fallback)")
    
    return page_tags

def map_toc_to_lecture_section(toc_title):
    """Map TOC section title to lecture section type"""
    title_lower = toc_title.lower()
    
    # Pattern matching for lecture sections
    if any(word in title_lower for word in ['введение', 'основы', 'что такое', 'начало']):
        return "Введение"
    elif any(word in title_lower for word in ['пример', 'код', 'программа', 'листинг', 'демонстрация']):
        return "Примеры кода"
    elif any(word in title_lower for word in ['метод', 'функция', 'операция', 'работа', 'использование']):
        return "Основные концепции"
    elif any(word in title_lower for word in ['совет', 'ошибка', 'практика', 'применение', 'рекомендация']):
        return "Практические советы"
    elif any(word in title_lower for word in ['заключение', 'итог', 'резюме', 'выводы']):
        return "Заключение"
    else:
        # Default based on content keywords
        if any(word in title_lower for word in ['строк', 'текст', 'символ']):
            return "Основные концепции"  # String-related content
        else:
            return "Основные концепции"  # Default to core concepts

def get_position_based_tag(page_num, selected_pages):
    """Fallback: position-based tagging"""
    page_numbers = [p['page_number'] for p in selected_pages]
    page_numbers.sort()
    
    position = page_numbers.index(page_num)
    total_pages = len(page_numbers)
    
    if position == 0:
        return "Введение"
    elif position < total_pages * 0.3:
        return "Основные концепции"
    elif position < total_pages * 0.7:
        return "Примеры кода"
    elif position < total_pages * 0.9:
        return "Практические советы"
    else:
        return "Заключение"

def distribute_pages_toc_aware(selected_pages, outline, page_tags):
    """Distribute pages based on TOC-derived tags"""
    
    print(f"\n📊 Distributing pages using TOC-based tags...")
    
    # Group pages by lecture section type
    section_page_groups = {
        "Введение": [],
        "Основные концепции": [],
        "Примеры кода": [],
        "Практические советы": [],
        "Заключение": []
    }
    
    for page in selected_pages:
        page_num = page['page_number']
        tag_info = page_tags.get(page_num, {'lecture_section': 'Основные концепции'})
        lecture_section = tag_info['lecture_section']
        section_page_groups[lecture_section].append(page)
    
    print(f"Page groups:")
    for section, pages in section_page_groups.items():
        page_nums = [p['page_number'] for p in pages]
        print(f"  {section}: {page_nums}")
    
    # Distribute to lecture sections
    section_contexts = {}
    
    for i, section_info in enumerate(outline):
        section_title = section_info['title']
        
        # Get pages tagged for this section type
        primary_pages = section_page_groups.get(section_title, [])
        
        # Add core pages (always include first 2 pages for context)
        core_pages = selected_pages[:2]
        
        # Combine and deduplicate
        all_pages = core_pages + primary_pages
        unique_pages = []
        seen_pages = set()
        
        for page in all_pages:
            if page['page_number'] not in seen_pages:
                unique_pages.append(page)
                seen_pages.add(page['page_number'])
        
        # Limit to 4-5 pages max
        section_contexts[i] = unique_pages[:4]
        
        # Ensure minimum pages (fallback)
        if len(section_contexts[i]) < 2:
            section_contexts[i] = selected_pages[:3]  # Fallback to first 3 pages
        
        page_nums = [p['page_number'] for p in section_contexts[i]]
        print(f"  Section {i+1} '{section_title}': Pages {page_nums}")
    
    return section_contexts

async def generate_sections_toc_parallel(generator, theme, selected_pages, outline, toc_entries):
    """Generate sections in parallel using TOC-based context distribution"""
    print(f"\n🚀 TOC-BASED PARALLEL SECTION GENERATION")
    print(f"{'-'*60}")
    
    # Monitor resources before
    resources_before = get_system_resources()
    print(f"Resources before: CPU {resources_before['cpu_percent']:.1f}%, "
          f"RAM {resources_before['memory_percent']:.1f}%, "
          f"GPU {resources_before['gpu'].get('memory_percent', 0):.1f}%")
    
    start_time = time.time()
    
    # Stage 1: Generate outline (same as before)
    outline_start = time.time()
    full_context = "\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
        for p in selected_pages
    ])
    outline = await generator._generate_outline(theme, full_context)
    outline_time = time.time() - outline_start
    print(f"  Outline generated: {outline_time:.1f}s ({len(outline)} sections)")
    
    # Stage 2: TOC-based context distribution
    distribution_start = time.time()
    
    # Create page tags based on TOC structure
    page_tags = create_toc_based_page_tags(toc_entries, selected_pages)
    
    # Distribute pages to sections
    section_contexts = distribute_pages_toc_aware(selected_pages, outline, page_tags)
    
    distribution_time = time.time() - distribution_start
    print(f"  Context distribution: {distribution_time:.1f}s")
    
    # Stage 3: Generate sections in parallel with distributed contexts
    sections_start = time.time()
    
    print(f"\n  Generating {len(outline)} sections in parallel with TOC-distributed contexts...")
    
    # Create tasks with section-specific contexts
    tasks = []
    for i, section_info in enumerate(outline):
        relevant_pages = section_contexts[i]
        
        # Build context from relevant pages only
        section_context = "\n\n---PAGE BREAK---\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in relevant_pages
        ])
        
        print(f"    Section {i+1} '{section_info['title']}': {len(section_context)} chars from {len(relevant_pages)} pages")
        
        task = generator._generate_section(
            theme, section_info, section_context, i+1, len(outline)
        )
        tasks.append(task)
    
    # Execute all sections concurrently
    print(f"  Executing {len(tasks)} sections in parallel...")
    parallel_start = time.time()
    
    sections = await asyncio.gather(*tasks)
    
    parallel_time = time.time() - parallel_start
    sections_time = time.time() - sections_start
    
    print(f"  Parallel execution completed: {parallel_time:.1f}s")
    
    # Stage 4: Combine
    combine_start = time.time()
    final_content = "\n\n".join(sections)
    combine_time = time.time() - combine_start
    
    total_time = time.time() - start_time
    
    # Monitor resources after
    resources_after = get_system_resources()
    print(f"\nResources after: CPU {resources_after['cpu_percent']:.1f}%, "
          f"RAM {resources_after['memory_percent']:.1f}%, "
          f"GPU {resources_after['gpu'].get('memory_percent', 0):.1f}%")
    
    # Calculate context reduction
    original_context_size = len(full_context) * len(outline)  # All sections get full context
    distributed_context_size = sum(len("\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['content']}" for p in section_contexts[i]
    ])) for i in range(len(outline)))
    
    context_reduction = ((original_context_size - distributed_context_size) / original_context_size) * 100
    
    print(f"\n🚀 TOC-Based Parallel Results:")
    print(f"  Outline time: {outline_time:.1f}s")
    print(f"  Distribution time: {distribution_time:.1f}s")
    print(f"  Sections time: {sections_time:.1f}s")
    print(f"  Parallel execution: {parallel_time:.1f}s")
    print(f"  Combine time: {combine_time:.1f}s")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Final words: {len(final_content.split()):,}")
    print(f"  Context reduction: {context_reduction:.1f}%")
    
    return {
        'total_time': total_time,
        'outline_time': outline_time,
        'distribution_time': distribution_time,
        'sections_time': sections_time,
        'parallel_time': parallel_time,
        'combine_time': combine_time,
        'words': len(final_content.split()),
        'content': final_content,
        'context_reduction': context_reduction,
        'page_tags': page_tags,
        'section_contexts': section_contexts,
        'resources_before': resources_before,
        'resources_after': resources_after
    }

async def setup_generator_with_toc():
    """Setup generator and extract TOC data"""
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=shared_model_manager,
        pdf_processor=shared_pdf_processor
    )
    
    # Get pages for context
    pages_data = shared_pdf_processor.extract_text_from_pdf(BOOK_CONFIG['path'])
    
    if not pages_data['success']:
        raise Exception("Failed to extract pages")
    
    # Use first 10 pages as context (simplified for testing)
    context_pages = pages_data['pages'][:10]
    
    # Extract TOC data (simulate the TOC parsing process)
    toc_text = shared_pdf_processor.extract_table_of_contents(BOOK_CONFIG['path'])
    if toc_text['success']:
        toc_entries = generator._parse_toc_with_regex(toc_text['toc'])
        print(f"✓ TOC parsed: {len(toc_entries)} entries")
        for entry in toc_entries[:5]:  # Show first 5
            print(f"  {entry['number']} {entry['title']} (page {entry['page']})")
    else:
        # Fallback: create mock TOC entries
        toc_entries = [
            {'number': '7.4', 'title': 'Строки', 'page': 36, 'end_page': 45},
            {'number': '7.5', 'title': 'Методы строк', 'page': 46, 'end_page': 55},
            {'number': '8.1', 'title': 'Примеры работы со строками', 'page': 56, 'end_page': 65}
        ]
        print(f"⚠️ Using mock TOC entries: {len(toc_entries)} entries")
    
    return generator, context_pages, toc_entries

async def main():
    print("TOC-BASED CONTEXT DISTRIBUTION TEST")
    print("="*80)
    print(f"Theme: {TEST_THEME}")
    print(f"Book: {BOOK_CONFIG['title']}")
    print(f"Hardware: RTX 2060 12GB, Llama 3.1 8B")
    print(f"Innovation: TOC-based page tagging for context distribution")
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
    
    # Setup generator and TOC data
    print("🔧 Setting up generator, pages, and TOC data...")
    generator, context_pages, toc_entries = await setup_generator_with_toc()
    print(f"✓ Context prepared: {len(context_pages)} pages")
    
    # Test: TOC-based parallel generation
    print(f"\n{'='*80}")
    print("TEST: TOC-BASED PARALLEL SECTION GENERATION")
    print("="*80)
    
    toc_result = await generate_sections_toc_parallel(
        generator, TEST_THEME, context_pages, [], toc_entries
    )
    
    # Comparison with known baselines
    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print("="*80)
    
    # Known baselines
    original_baseline = 231.2  # From optimized test (shared ModelManager)
    full_parallel_result = 215.8  # From previous full parallel test
    batch_parallel_result = 234.5  # From batch parallel test
    
    toc_total = toc_result['total_time']
    toc_sections = toc_result['sections_time']
    
    improvement_vs_baseline = ((original_baseline - toc_total) / original_baseline) * 100
    improvement_vs_full_parallel = ((full_parallel_result - toc_total) / full_parallel_result) * 100
    improvement_vs_batch_parallel = ((batch_parallel_result - toc_total) / batch_parallel_result) * 100
    
    print(f"\n📊 TIMING COMPARISON:")
    print(f"{'Approach':<25} {'Total Time':<12} {'Sections Time':<15} {'GPU Peak':<12} {'Improvement':<12}")
    print(f"{'-'*85}")
    print(f"{'Original Baseline':<25} {original_baseline:<12.1f} {'~150s':<15} {'~40%':<12} {'Baseline':<12}")
    print(f"{'Full Parallel':<25} {full_parallel_result:<12.1f} {'199.7s':<15} {'79.9%':<12} {'+6.7%':<12}")
    print(f"{'Batch Parallel (3)':<25} {batch_parallel_result:<12.1f} {'212.0s':<15} {'80.1%':<12} {'-1.4%':<12}")
    print(f"{'TOC-Based Parallel':<25} {toc_total:<12.1f} {toc_sections:<15.1f} {toc_result['resources_after']['gpu'].get('memory_percent', 0):<12.1f}% {improvement_vs_baseline:<12.1f}%")
    
    print(f"\n📈 IMPROVEMENT ANALYSIS:")
    print(f"  vs Original Baseline: {improvement_vs_baseline:+.1f}%")
    print(f"  vs Full Parallel: {improvement_vs_full_parallel:+.1f}%")
    print(f"  vs Batch Parallel: {improvement_vs_batch_parallel:+.1f}%")
    
    # Context efficiency analysis
    print(f"\n🔍 CONTEXT EFFICIENCY:")
    print(f"  Context reduction: {toc_result['context_reduction']:.1f}%")
    print(f"  Pages per section: {sum(len(pages) for pages in toc_result['section_contexts'].values()) / len(toc_result['section_contexts']):.1f} avg")
    
    # GPU usage analysis
    gpu_before = toc_result['resources_before']['gpu'].get('memory_percent', 0)
    gpu_after = toc_result['resources_after']['gpu'].get('memory_percent', 0)
    gpu_delta = gpu_after - gpu_before
    
    print(f"\n📊 RESOURCE EFFICIENCY:")
    print(f"  GPU usage increase: {gpu_delta:.1f}%")
    
    if gpu_after < 60:
        print(f"  ✅ EXCELLENT GPU USAGE: {gpu_after:.1f}% - highly sustainable for production")
    elif gpu_after < 75:
        print(f"  ✅ GOOD GPU USAGE: {gpu_after:.1f}% - sustainable for production")
    elif gpu_after < 85:
        print(f"  ⚠️ HIGH GPU USAGE: {gpu_after:.1f}% - manageable but monitor closely")
    else:
        print(f"  🚫 GPU OVERLOAD: {gpu_after:.1f}% - may cause instability")
    
    # TOC tagging analysis
    print(f"\n🏷️ TOC TAGGING ANALYSIS:")
    tag_distribution = {}
    for page_num, tag_info in toc_result['page_tags'].items():
        section = tag_info['lecture_section']
        tag_distribution[section] = tag_distribution.get(section, 0) + 1
    
    for section, count in tag_distribution.items():
        print(f"  {section}: {count} pages")
    
    # Production readiness assessment
    print(f"\n✅ PRODUCTION READINESS ASSESSMENT:")
    
    if improvement_vs_baseline > 25 and gpu_after < 65:
        print(f"  🎉 EXCELLENT: {improvement_vs_baseline:.1f}% improvement with optimal GPU usage")
        print(f"  📋 RECOMMENDATION: Deploy immediately - this is the optimal solution")
    elif improvement_vs_baseline > 15 and gpu_after < 75:
        print(f"  ✅ VERY GOOD: {improvement_vs_baseline:.1f}% improvement with good GPU usage")
        print(f"  📋 RECOMMENDATION: Deploy after brief testing")
    elif improvement_vs_baseline > 10:
        print(f"  ✅ GOOD: {improvement_vs_baseline:.1f}% improvement")
        print(f"  📋 RECOMMENDATION: Implement with monitoring")
    elif improvement_vs_baseline > 0:
        print(f"  ⚠️ MODEST: {improvement_vs_baseline:.1f}% improvement")
        print(f"  📋 RECOMMENDATION: Consider further optimizations")
    else:
        print(f"  ❌ INSUFFICIENT: {improvement_vs_baseline:.1f}% improvement")
        print(f"  📋 RECOMMENDATION: Debug and refine approach")
    
    print(f"\n✅ TEST COMPLETE")
    print(f"TOC-based parallel processing shows {improvement_vs_baseline:.1f}% improvement")
    print(f"Context reduction: {toc_result['context_reduction']:.1f}% - much more efficient!")

if __name__ == "__main__":
    asyncio.run(main())