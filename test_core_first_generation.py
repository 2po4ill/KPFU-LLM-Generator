"""
Test Core-First Generation Architecture
Implementation of the optimized approach:
1. Phase 1: Extract core concepts from book pages (60s target)
2. Phase 2: Generate 4 sections in parallel from core concepts (60s target)
Total target: 120s vs current 400-500s for "Изучаем Питон"
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

# Test configuration - using the most challenging book
TEST_THEME = 'Работа со строками'
BOOK_CONFIG = {
    'path': 'Изучаем_Питон.pdf',
    'title': 'Изучаем Python',
    'level': 'intermediate'
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
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    gpu_info = {}
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
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

async def extract_key_concepts_list(theme: str, pages: list, model_manager) -> str:
    """Stage 1: Quick extraction of key concept names only (30s target)"""
    
    print(f"\n📋 Stage 1: Extracting key concepts for '{theme}'")
    print(f"Processing {len(pages)} pages...")
    
    start_time = time.time()
    
    # Build context from all pages
    context = "\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['text'][:2000]}"  # Limit to first 2000 chars per page
        for p in pages
    ])
    
    print(f"Context size: {len(context):,} characters")
    
    prompt = f"""Извлеки ТОЛЬКО НАЗВАНИЯ ключевых концепций по теме "{theme}" из учебного материала.

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ТРЕБОВАНИЯ:
- Максимум 150 слов
- Только названия концепций (без объяснений)
- Список ключевых понятий через запятую
- Фокус на теме "{theme}"

Пример формата: "строковые литералы, методы строк, форматирование, срезы строк, escape-последовательности"

Извлеки ключевые концепции:"""

    try:
        llm_model = await model_manager.get_llm_model()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={
                "temperature": 0.1,  # Very low for factual accuracy
                "num_predict": 200,
                "num_ctx": 32768,
                "top_p": 0.9
            }
        )
        
        concepts_list = response.get('response', '').strip()
        
        stage1_time = time.time() - start_time
        print(f"✓ Stage 1 completed: {stage1_time:.1f}s")
        print(f"Key concepts identified: {concepts_list}")
        
        return concepts_list
        
    except Exception as e:
        print(f"❌ Error in Stage 1: {e}")
        return "строки, методы, форматирование"  # Fallback

async def elaborate_core_concepts(theme: str, concepts_list: str, core_pages: list, model_manager) -> str:
    """Stage 2: Detailed elaboration of identified concepts (30s target)"""
    
    print(f"\n📖 Stage 2: Elaborating core concepts")
    print(f"Using {len(core_pages)} core pages for detailed extraction")
    
    start_time = time.time()
    
    # Build context from core pages only
    context = "\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['text']}"
        for p in core_pages
    ])
    
    print(f"Context size: {len(context):,} characters")
    
    prompt = f"""Создай подробное описание ключевых концепций по теме "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ ДЛЯ РАСКРЫТИЯ:
{concepts_list}

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ТРЕБОВАНИЯ:
- Точно 800 слов
- Подробное объяснение каждой концепции из списка
- ТОЛЬКО факты из предоставленного материала
- Структурированное изложение
- Определения, принципы, особенности

ФОРМАТ:
**Основные концепции: {theme}**

[Подробное структурированное описание каждой концепции из списка]

Начни описание концепций:"""

    try:
        llm_model = await model_manager.get_llm_model()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={
                "temperature": 0.1,  # Very low for factual accuracy
                "num_predict": 1200,
                "num_ctx": 32768,
                "top_p": 0.9
            }
        )
        
        core_concepts = response.get('response', '').strip()
        
        stage2_time = time.time() - start_time
        print(f"✓ Stage 2 completed: {stage2_time:.1f}s")
        print(f"Core concepts generated: {len(core_concepts.split())} words")
        
        return core_concepts
        
    except Exception as e:
        print(f"❌ Error in Stage 2: {e}")
        return f"**Основные концепции: {theme}**\n\n[Ошибка генерации концепций]"

async def generate_section_from_core(section_type: str, theme: str, core_concepts: str, target_words: int, temperature: float, model_manager) -> str:
    """Generate a section based on core concepts"""
    
    section_start = time.time()
    
    if section_type == "introduction":
        prompt = f"""Напиши введение к лекции по теме "{theme}" на основе ключевых концепций.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Точно {target_words} слов
- Введение в тему на основе концепций
- Объясни важность темы
- Что студент узнает из лекции

ФОРМАТ:
**Введение**

[Введение к лекции]"""

    elif section_type == "examples":
        prompt = f"""Создай подробные примеры по теме "{theme}" на основе ключевых концепций.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Точно {target_words} слов
- 5-7 практических примеров
- Каждый пример иллюстрирует концепции
- Подробные объяснения
- От простых к сложным

ФОРМАТ:
**Примеры и демонстрации**

[Подробные примеры с объяснениями]"""

    elif section_type == "tips":
        prompt = f"""Создай практические советы по теме "{theme}" на основе ключевых концепций.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Точно {target_words} слов
- Практические рекомендации
- Типичные ошибки и как их избежать
- Лучшие практики
- Советы по применению

ФОРМАТ:
**Практические советы**

[Практические рекомендации]"""

    elif section_type == "conclusion":
        prompt = f"""Напиши заключение к лекции по теме "{theme}" на основе ключевых концепций.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Точно {target_words} слов
- Резюме ключевых моментов
- Что студент должен запомнить
- Связь с будущими темами

ФОРМАТ:
**Заключение**

[Заключение лекции]"""

    try:
        llm_model = await model_manager.get_llm_model()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={
                "temperature": temperature,
                "num_predict": int(target_words * 1.5),
                "num_ctx": 32768,
                "top_p": 0.9
            }
        )
        
        section_content = response.get('response', '').strip()
        section_time = time.time() - section_start
        
        print(f"    {section_type}: {section_time:.1f}s, {len(section_content.split())} words")
        
        return section_content
        
    except Exception as e:
        print(f"❌ Error generating {section_type}: {e}")
        return f"**{section_type.title()}**\n\n[Ошибка генерации раздела]"

async def generate_sections_parallel_from_core(theme: str, core_concepts: str, model_manager) -> dict:
    """Phase 2: Generate all sections in parallel from core concepts (60s target)"""
    
    print(f"\n🚀 Phase 2: Generating sections in parallel from core concepts")
    
    start_time = time.time()
    
    # Create tasks for parallel generation
    tasks = [
        generate_section_from_core("introduction", theme, core_concepts, 400, 0.3, model_manager),
        generate_section_from_core("examples", theme, core_concepts, 600, 0.4, model_manager),
        generate_section_from_core("tips", theme, core_concepts, 600, 0.4, model_manager),
        generate_section_from_core("conclusion", theme, core_concepts, 400, 0.3, model_manager)
    ]
    
    print(f"Executing 4 sections in parallel...")
    
    # Execute all sections concurrently
    sections = await asyncio.gather(*tasks)
    
    phase2_time = time.time() - start_time
    print(f"✓ Phase 2 completed: {phase2_time:.1f}s")
    
    return {
        'introduction': sections[0],
        'examples': sections[1],
        'tips': sections[2],
        'conclusion': sections[3],
        'generation_time': phase2_time
    }

async def core_first_generation_test(theme: str, book_path: str):
    """Test the complete core-first generation architecture"""
    
    print(f"\n🎯 CORE-FIRST GENERATION TEST")
    print(f"{'='*80}")
    print(f"Theme: {theme}")
    print(f"Book: {book_path}")
    print(f"Target: Phase 1 (60s) + Phase 2 (60s) = 120s total")
    print()
    
    # Monitor resources before
    resources_before = get_system_resources()
    print(f"💻 Resources before: CPU {resources_before['cpu_percent']:.1f}%, "
          f"RAM {resources_before['memory_percent']:.1f}%, "
          f"GPU {resources_before['gpu'].get('memory_percent', 0):.1f}%")
    
    total_start = time.time()
    
    # Get pages for the theme (simulate existing page selection)
    print(f"\n📚 Loading book and selecting pages...")
    pages_data = shared_pdf_processor.extract_text_from_pdf(book_path)
    
    if not pages_data['success']:
        print(f"❌ Failed to extract pages from {book_path}")
        return
    
    # Use first 15 pages for testing (simulate page selection result)
    selected_pages = pages_data['pages'][:15]
    print(f"✓ Selected {len(selected_pages)} pages for processing")
    
    # PHASE 1: Core Concept Extraction (60s target)
    print(f"\n{'='*60}")
    print("PHASE 1: CORE CONCEPT EXTRACTION")
    print("="*60)
    
    phase1_start = time.time()
    
    # Stage 1: Extract key concepts list (30s target)
    concepts_list = await extract_key_concepts_list(theme, selected_pages, shared_model_manager)
    
    # Stage 2: Elaborate concepts using core pages (30s target)
    core_pages = selected_pages[:5]  # Use first 5 pages for detailed extraction
    core_concepts = await elaborate_core_concepts(theme, concepts_list, core_pages, shared_model_manager)
    
    phase1_time = time.time() - phase1_start
    print(f"\n✓ PHASE 1 COMPLETE: {phase1_time:.1f}s")
    print(f"Core concepts size: {len(core_concepts)} chars, {len(core_concepts.split())} words")
    
    # PHASE 2: Parallel Section Generation (60s target)
    print(f"\n{'='*60}")
    print("PHASE 2: PARALLEL SECTION GENERATION")
    print("="*60)
    
    sections_result = await generate_sections_parallel_from_core(theme, core_concepts, shared_model_manager)
    phase2_time = sections_result['generation_time']
    
    # Assemble final lecture
    print(f"\n📝 Assembling final lecture...")
    final_lecture = f"""# Лекция: {theme}

{sections_result['introduction']}

## Основные концепции

{core_concepts}

{sections_result['examples']}

{sections_result['tips']}

{sections_result['conclusion']}
"""
    
    total_time = time.time() - total_start
    
    # Monitor resources after
    resources_after = get_system_resources()
    print(f"\n💻 Resources after: CPU {resources_after['cpu_percent']:.1f}%, "
          f"RAM {resources_after['memory_percent']:.1f}%, "
          f"GPU {resources_after['gpu'].get('memory_percent', 0):.1f}%")
    
    # Results analysis
    print(f"\n{'='*80}")
    print("PERFORMANCE RESULTS")
    print("="*80)
    
    total_words = len(final_lecture.split())
    
    print(f"\n📊 TIMING BREAKDOWN:")
    print(f"  Phase 1 (Core Extraction): {phase1_time:.1f}s")
    print(f"  Phase 2 (Parallel Generation): {phase2_time:.1f}s")
    print(f"  Total Time: {total_time:.1f}s")
    
    print(f"\n📈 PERFORMANCE ANALYSIS:")
    print(f"  Target Time: 120s")
    print(f"  Actual Time: {total_time:.1f}s")
    
    if total_time <= 120:
        improvement = ((120 - total_time) / 120) * 100
        print(f"  ✅ SUCCESS: {improvement:.1f}% better than target!")
    else:
        overage = ((total_time - 120) / 120) * 100
        print(f"  ⚠️ OVER TARGET: {overage:.1f}% slower than target")
    
    # Compare with previous results
    baseline_time = 450  # Approximate time for "Изучаем Питон" from previous tests
    if total_time < baseline_time:
        improvement = ((baseline_time - total_time) / baseline_time) * 100
        print(f"  🚀 vs Baseline: {improvement:.1f}% improvement ({baseline_time}s → {total_time:.1f}s)")
    
    print(f"\n📝 CONTENT ANALYSIS:")
    print(f"  Total Words: {total_words:,}")
    print(f"  Target Words: 2,000")
    
    if total_words >= 2000:
        print(f"  ✅ Word target achieved!")
    else:
        shortage = 2000 - total_words
        print(f"  ⚠️ Word shortage: {shortage} words below target")
    
    print(f"\n🔍 CONTEXT EFFICIENCY:")
    original_context = len(selected_pages) * 15  # 15 pages × 15 sections in old approach
    new_context = len(selected_pages) + (4 * len(core_concepts.split()))  # Phase 1 + Phase 2
    
    context_reduction = ((original_context - new_context) / original_context) * 100
    print(f"  Context Reduction: {context_reduction:.1f}%")
    
    gpu_delta = resources_after['gpu'].get('memory_percent', 0) - resources_before['gpu'].get('memory_percent', 0)
    print(f"  GPU Usage Delta: {gpu_delta:.1f}%")
    
    if gpu_delta < 50:
        print(f"  ✅ Sustainable GPU usage")
    else:
        print(f"  ⚠️ High GPU usage - monitor for stability")
    
    # Save results
    print(f"\n💾 Saving results...")
    
    with open(f"core_first_test_results_{int(time.time())}.md", "w", encoding="utf-8") as f:
        f.write(f"""# Core-First Generation Test Results

**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**Theme**: {theme}
**Book**: {book_path}

## Performance Results

- **Phase 1 Time**: {phase1_time:.1f}s
- **Phase 2 Time**: {phase2_time:.1f}s  
- **Total Time**: {total_time:.1f}s
- **Target Time**: 120s
- **Performance**: {'✅ SUCCESS' if total_time <= 120 else '⚠️ OVER TARGET'}

## Content Results

- **Total Words**: {total_words:,}
- **Target Words**: 2,000
- **Word Achievement**: {'✅ SUCCESS' if total_words >= 2000 else '⚠️ SHORTAGE'}

## Generated Lecture

{final_lecture}
""")
    
    print(f"✓ Results saved to core_first_test_results_{int(time.time())}.md")
    
    print(f"\n✅ CORE-FIRST GENERATION TEST COMPLETE")
    print(f"Total time: {total_time:.1f}s | Words: {total_words:,} | Target: 120s/2000 words")

async def main():
    print("CORE-FIRST GENERATION ARCHITECTURE TEST")
    print("="*80)
    print("Testing theoretical optimizations with real implementation")
    print("Book: Изучаем Питон (most challenging)")
    print("Expected: 60s + 60s = 120s total vs 400-500s baseline")
    print()
    
    # Initialize components
    await initialize_shared_components()
    
    # Run the test
    await core_first_generation_test(TEST_THEME, BOOK_CONFIG['path'])

if __name__ == "__main__":
    asyncio.run(main())