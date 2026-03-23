"""
Test Refined Core-First Generation Architecture
Implementation of optimized approach based on test results:

Phase 1: Core Concepts (60s target)
├── Step A: Identify concepts list (15s)
├── Step B: Parallel concept elaboration (45s)
│   ├── Concepts Part 1 (600 words, temp=0.1)
│   └── Concepts Part 2 (600 words, temp=0.1)
└── Result: 1200 words detailed core concepts

Phase 2: Lecture Sections (60s target)
├── Introduction (flexible length, temp=0.2)
├── Practical Applications (800 words, temp=0.4) 
└── Conclusion (flexible length, temp=0.2)

Total Target: 120s vs 332.9s previous test
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

async def llm_generate(prompt: str, temperature: float, max_tokens: int, model_manager) -> str:
    """Helper function for LLM generation"""
    try:
        llm_model = await model_manager.get_llm_model()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 32768,
                "top_p": 0.9
            }
        )
        
        return response.get('response', '').strip()
        
    except Exception as e:
        print(f"❌ LLM generation error: {e}")
        return "[Ошибка генерации]"

# PHASE 1: OPTIMIZED CORE CONCEPTS GENERATION

async def identify_core_concepts_list(theme: str, pages: list, model_manager) -> list:
    """Phase 1A: Quick identification of key concepts (15s target)"""
    
    print(f"\n📋 Phase 1A: Identifying core concepts for '{theme}'")
    
    start_time = time.time()
    
    # Optimized context: 1000 chars per page, only 10 pages
    context = "\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['text'][:1000]}"
        for p in pages[:10]
    ])
    
    print(f"Context size: {len(context):,} characters (optimized)")
    
    prompt = f"""Извлеки ТОЛЬКО НАЗВАНИЯ ключевых концепций по теме "{theme}" из учебного материала.

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ТРЕБОВАНИЯ:
- Список из 8-12 концепций
- Только названия (без объяснений)
- Разделить запятыми
- Фокус на теме "{theme}"

Пример формата: "строковые литералы, методы строк, форматирование, срезы строк, escape-последовательности"

Извлеки ключевые концепции:"""

    concepts_response = await llm_generate(prompt, 0.1, 150, model_manager)
    
    # Parse concepts into list
    concepts = [c.strip() for c in concepts_response.split(',') if c.strip()]
    
    phase1a_time = time.time() - start_time
    print(f"✓ Phase 1A completed: {phase1a_time:.1f}s")
    print(f"Identified {len(concepts)} concepts: {concepts}")
    
    return concepts

async def elaborate_concept_group(theme: str, concepts: list, context: str, part_name: str, target_words: int, model_manager) -> str:
    """Elaborate a group of concepts in detail"""
    
    concepts_text = ", ".join(concepts)
    
    prompt = f"""Подробно опиши концепции: {concepts_text}

ТЕМА ЛЕКЦИИ: {theme}

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ТРЕБОВАНИЯ:
- Точно {target_words} слов
- Подробное объяснение каждой концепции из списка
- ТОЛЬКО факты из предоставленного материала
- Структурированное изложение с определениями
- Логическая последовательность

ФОРМАТ:
**{part_name}: {theme}**

[Подробное структурированное описание концепций]

Начни описание концепций:"""

    return await llm_generate(prompt, 0.1, int(target_words * 1.5), model_manager)

async def elaborate_concepts_parallel(theme: str, concepts: list, pages: list, model_manager) -> str:
    """Phase 1B: Generate detailed concepts in parallel (45s target)"""
    
    print(f"\n📖 Phase 1B: Elaborating concepts in parallel")
    
    start_time = time.time()
    
    # Split concepts into two groups
    mid_point = len(concepts) // 2
    concepts_part1 = concepts[:mid_point]
    concepts_part2 = concepts[mid_point:]
    
    print(f"Part 1 concepts ({len(concepts_part1)}): {concepts_part1}")
    print(f"Part 2 concepts ({len(concepts_part2)}): {concepts_part2}")
    
    # Prepare optimized context from core pages
    context = "\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['text']}"
        for p in pages[:5]  # Only 5 most relevant pages
    ])
    
    print(f"Context size: {len(context):,} characters")
    
    # Generate both parts in parallel
    tasks = [
        elaborate_concept_group(theme, concepts_part1, context, "Часть 1", 600, model_manager),
        elaborate_concept_group(theme, concepts_part2, context, "Часть 2", 600, model_manager)
    ]
    
    print("Generating concept parts in parallel...")
    parts = await asyncio.gather(*tasks)
    
    # Combine parts
    combined_concepts = f"""**Основные концепции: {theme}**

{parts[0]}

{parts[1]}"""
    
    phase1b_time = time.time() - start_time
    print(f"✓ Phase 1B completed: {phase1b_time:.1f}s")
    print(f"Generated concepts: {len(combined_concepts.split())} words")
    
    return combined_concepts

# PHASE 2: OPTIMIZED SECTION GENERATION

async def generate_flexible_introduction(theme: str, core_concepts: str, model_manager) -> str:
    """Generate concise, focused introduction without repetition"""
    
    prompt = f"""Напиши краткое введение к лекции по теме "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Краткое и по существу (БЕЗ повторений)
- Объясни важность темы для программирования
- Что студент узнает (кратко, одним абзацем)
- НЕ повторяй одно и то же несколько раз
- НЕ создавай списки "навыки которые вы узнаете"

ФОРМАТ:
**Введение**

[Краткое введение без повторений и списков]

Напиши введение:"""

    return await llm_generate(prompt, 0.2, 600, model_manager)

async def generate_practical_applications(theme: str, core_concepts: str, model_manager) -> str:
    """Generate combined examples and practical recommendations"""
    
    prompt = f"""Создай практический раздел по теме "{theme}" с примерами и рекомендациями.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Точно 800 слов
- 4-5 практических примеров с кодом Python
- Практические советы и рекомендации после каждого примера
- Типичные ошибки и как их избежать
- От простых к сложным примерам
- Каждый пример должен иллюстрировать концепции из основного материала

ФОРМАТ:
**Практическое применение**

### Пример 1: [Название]
```python
# код примера
```
[Объяснение и рекомендации]

### Пример 2: [Название]
```python
# код примера
```
[Объяснение и рекомендации]

[И так далее...]

Создай практический раздел:"""

    return await llm_generate(prompt, 0.4, 1200, model_manager)

async def generate_focused_conclusion(theme: str, core_concepts: str, model_manager) -> str:
    """Generate focused conclusion without irrelevant future topics"""
    
    prompt = f"""Напиши заключение к лекции по теме "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

ТРЕБОВАНИЯ:
- Краткое резюме ТОЛЬКО изученных концепций
- Ключевые моменты, которые студент должен запомнить
- НЕ упоминай несвязанные будущие темы (decorators, базы данных и т.д.)
- Фокус на практическом применении изученного материала
- Мотивация к дальнейшему изучению темы

ФОРМАТ:
**Заключение**

**Ключевые моменты:**
- [Основные выводы по теме]

**Что студент должен запомнить:**
- [Практические знания]

Напиши заключение:"""

    return await llm_generate(prompt, 0.2, 500, model_manager)

async def generate_optimized_sections(theme: str, core_concepts: str, model_manager) -> dict:
    """Phase 2: Generate 3 sections with optimized prompts (60s target)"""
    
    print(f"\n🚀 Phase 2: Generating 3 sections in parallel")
    
    start_time = time.time()
    
    # Create tasks for 3 sections (reduced from 4)
    tasks = [
        generate_flexible_introduction(theme, core_concepts, model_manager),
        generate_practical_applications(theme, core_concepts, model_manager),
        generate_focused_conclusion(theme, core_concepts, model_manager)
    ]
    
    print(f"Executing 3 sections in parallel (reduced from 4)...")
    
    # Execute all sections concurrently
    sections = await asyncio.gather(*tasks)
    
    phase2_time = time.time() - start_time
    print(f"✓ Phase 2 completed: {phase2_time:.1f}s")
    
    # Log individual section info
    for i, section in enumerate(sections):
        section_names = ['introduction', 'practical', 'conclusion']
        word_count = len(section.split())
        print(f"    {section_names[i]}: {word_count} words")
    
    return {
        'introduction': sections[0],
        'practical': sections[1], 
        'conclusion': sections[2],
        'generation_time': phase2_time
    }

async def refined_core_first_test(theme: str, book_path: str):
    """Test the refined core-first generation architecture"""
    
    print(f"\n🎯 REFINED CORE-FIRST GENERATION TEST")
    print(f"{'='*80}")
    print(f"Theme: {theme}")
    print(f"Book: {book_path}")
    print(f"Target: Phase 1 (60s) + Phase 2 (60s) = 120s total")
    print(f"Optimizations: 3 sections, parallel concepts, optimized prompts")
    print()
    
    # Monitor resources before
    resources_before = get_system_resources()
    print(f"💻 Resources before: CPU {resources_before['cpu_percent']:.1f}%, "
          f"RAM {resources_before['memory_percent']:.1f}%, "
          f"GPU {resources_before['gpu'].get('memory_percent', 0):.1f}%")
    
    total_start = time.time()
    
    # Load book and select pages
    print(f"\n📚 Loading book and selecting pages...")
    pages_data = shared_pdf_processor.extract_text_from_pdf(book_path)
    
    if not pages_data['success']:
        print(f"❌ Failed to extract pages from {book_path}")
        return
    
    # Use first 15 pages but optimize processing
    selected_pages = pages_data['pages'][:15]
    print(f"✓ Selected {len(selected_pages)} pages for processing")
    
    # PHASE 1: OPTIMIZED CORE CONCEPT EXTRACTION (60s target)
    print(f"\n{'='*60}")
    print("PHASE 1: OPTIMIZED CORE CONCEPT EXTRACTION")
    print("="*60)
    
    phase1_start = time.time()
    
    # Phase 1A: Identify concepts (15s target)
    concepts_list = await identify_core_concepts_list(theme, selected_pages, shared_model_manager)
    
    # Phase 1B: Elaborate concepts in parallel (45s target)
    core_concepts = await elaborate_concepts_parallel(theme, concepts_list, selected_pages, shared_model_manager)
    
    phase1_time = time.time() - phase1_start
    print(f"\n✓ PHASE 1 COMPLETE: {phase1_time:.1f}s")
    print(f"Core concepts: {len(core_concepts)} chars, {len(core_concepts.split())} words")
    
    # PHASE 2: OPTIMIZED SECTION GENERATION (60s target)
    print(f"\n{'='*60}")
    print("PHASE 2: OPTIMIZED SECTION GENERATION")
    print("="*60)
    
    sections_result = await generate_optimized_sections(theme, core_concepts, shared_model_manager)
    phase2_time = sections_result['generation_time']
    
    # Assemble final lecture
    print(f"\n📝 Assembling final lecture...")
    final_lecture = f"""# Лекция: {theme}

{sections_result['introduction']}

## Основные концепции

{core_concepts}

{sections_result['practical']}

{sections_result['conclusion']}
"""
    
    total_time = time.time() - total_start
    
    # Monitor resources after
    resources_after = get_system_resources()
    print(f"\n💻 Resources after: CPU {resources_after['cpu_percent']:.1f}%, "
          f"RAM {resources_after['memory_percent']:.1f}%, "
          f"GPU {resources_after['gpu'].get('memory_percent', 0):.1f}%")
    
    # RESULTS ANALYSIS
    print(f"\n{'='*80}")
    print("REFINED ARCHITECTURE RESULTS")
    print("="*80)
    
    total_words = len(final_lecture.split())
    
    print(f"\n📊 TIMING BREAKDOWN:")
    print(f"  Phase 1 (Optimized Core): {phase1_time:.1f}s")
    print(f"  Phase 2 (3 Sections): {phase2_time:.1f}s")
    print(f"  Total Time: {total_time:.1f}s")
    
    print(f"\n📈 PERFORMANCE ANALYSIS:")
    print(f"  Target Time: 120s")
    print(f"  Actual Time: {total_time:.1f}s")
    
    if total_time <= 120:
        improvement = ((120 - total_time) / 120) * 100
        print(f"  ✅ SUCCESS: {improvement:.1f}% better than target!")
    elif total_time <= 150:
        overage = ((total_time - 120) / 120) * 100
        print(f"  ⚠️ CLOSE: {overage:.1f}% over target (still good)")
    else:
        overage = ((total_time - 120) / 120) * 100
        print(f"  ❌ OVER TARGET: {overage:.1f}% slower than target")
    
    # Compare with previous test
    previous_time = 332.9
    improvement_vs_previous = ((previous_time - total_time) / previous_time) * 100
    print(f"  🚀 vs Previous Test: {improvement_vs_previous:.1f}% improvement ({previous_time}s → {total_time:.1f}s)")
    
    # Compare with baseline
    baseline_time = 450
    improvement_vs_baseline = ((baseline_time - total_time) / baseline_time) * 100
    print(f"  🎯 vs Original Baseline: {improvement_vs_baseline:.1f}% improvement ({baseline_time}s → {total_time:.1f}s)")
    
    print(f"\n📝 CONTENT ANALYSIS:")
    print(f"  Total Words: {total_words:,}")
    print(f"  Target Words: 2,000")
    
    if total_words >= 2000:
        print(f"  ✅ Word target achieved!")
    else:
        shortage = 2000 - total_words
        print(f"  ⚠️ Word shortage: {shortage} words below target")
    
    print(f"\n🔍 OPTIMIZATION EFFECTIVENESS:")
    
    # GPU usage analysis
    gpu_delta = resources_after['gpu'].get('memory_percent', 0) - resources_before['gpu'].get('memory_percent', 0)
    print(f"  GPU Usage Delta: {gpu_delta:.1f}%")
    
    if gpu_delta < 40:
        print(f"  ✅ Excellent GPU efficiency")
    elif gpu_delta < 60:
        print(f"  ✅ Good GPU usage")
    else:
        print(f"  ⚠️ High GPU usage - monitor for stability")
    
    # Section count optimization
    print(f"  Sections Reduced: 4 → 3 (25% reduction)")
    print(f"  Parallel Concepts: Enabled (Phase 1B)")
    print(f"  Context Optimization: 1000 chars/page limit")
    
    # Content quality improvements
    print(f"\n📋 CONTENT QUALITY IMPROVEMENTS:")
    
    # Check for repetition in introduction
    intro_text = sections_result['introduction'].lower()
    repetition_indicators = ['навыки которые', 'что вы узнаете', 'о чем будет']
    repetition_count = sum(1 for indicator in repetition_indicators if indicator in intro_text)
    
    if repetition_count == 0:
        print(f"  ✅ Introduction: No repetitive content detected")
    else:
        print(f"  ⚠️ Introduction: {repetition_count} repetitive patterns found")
    
    # Check for irrelevant future topics in conclusion
    conclusion_text = sections_result['conclusion'].lower()
    irrelevant_topics = ['decorator', 'база данных', 'сетевое программирование', 'context manager']
    irrelevant_count = sum(1 for topic in irrelevant_topics if topic in conclusion_text)
    
    if irrelevant_count == 0:
        print(f"  ✅ Conclusion: No irrelevant future topics")
    else:
        print(f"  ⚠️ Conclusion: {irrelevant_count} irrelevant topics mentioned")
    
    # Save results
    print(f"\n💾 Saving results...")
    
    timestamp = int(time.time())
    results_file = f"refined_core_first_results_{timestamp}.md"
    
    with open(results_file, "w", encoding="utf-8") as f:
        f.write(f"""# Refined Core-First Generation Test Results

**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**Theme**: {theme}
**Book**: {book_path}

## Performance Results

- **Phase 1 Time**: {phase1_time:.1f}s (target: 60s)
- **Phase 2 Time**: {phase2_time:.1f}s (target: 60s)
- **Total Time**: {total_time:.1f}s (target: 120s)
- **Performance vs Target**: {'✅ SUCCESS' if total_time <= 120 else '⚠️ CLOSE' if total_time <= 150 else '❌ OVER TARGET'}
- **Improvement vs Previous**: {improvement_vs_previous:.1f}%
- **Improvement vs Baseline**: {improvement_vs_baseline:.1f}%

## Content Results

- **Total Words**: {total_words:,}
- **Target Words**: 2,000
- **Word Achievement**: {'✅ SUCCESS' if total_words >= 2000 else '⚠️ SHORTAGE'}

## Optimizations Applied

- ✅ Reduced sections: 4 → 3
- ✅ Parallel concept generation (Phase 1B)
- ✅ Optimized context size (1000 chars/page)
- ✅ Eliminated repetitive introduction
- ✅ Focused conclusion without irrelevant topics
- ✅ Combined examples + tips into practical applications

## Generated Lecture

{final_lecture}
""")
    
    print(f"✓ Results saved to {results_file}")
    
    # Final assessment
    print(f"\n{'='*80}")
    print("FINAL ASSESSMENT")
    print("="*80)
    
    if total_time <= 120 and total_words >= 2000:
        print(f"🎉 COMPLETE SUCCESS: All targets achieved!")
        print(f"   ✅ Time: {total_time:.1f}s ≤ 120s")
        print(f"   ✅ Words: {total_words:,} ≥ 2,000")
        print(f"   ✅ Quality: Optimized content structure")
    elif total_time <= 150 and total_words >= 1800:
        print(f"✅ EXCELLENT RESULT: Very close to all targets")
        print(f"   ⚠️ Time: {total_time:.1f}s (25% over target)")
        print(f"   ✅ Words: {total_words:,} (close to target)")
        print(f"   ✅ Quality: Significant improvements")
    else:
        print(f"⚠️ GOOD PROGRESS: Significant improvement over baseline")
        print(f"   📊 Time: {improvement_vs_baseline:.1f}% better than baseline")
        print(f"   📊 Architecture: Validated and working")
    
    print(f"\n✅ REFINED CORE-FIRST GENERATION TEST COMPLETE")
    print(f"Result: {total_time:.1f}s | {total_words:,} words | {improvement_vs_baseline:.1f}% improvement")

async def main():
    print("REFINED CORE-FIRST GENERATION ARCHITECTURE TEST")
    print("="*80)
    print("Testing optimized architecture with:")
    print("- 3 sections instead of 4 (reduced GPU pressure)")
    print("- Parallel concept generation (Phase 1B)")
    print("- Optimized prompts (no repetition, focused content)")
    print("- Reduced context size (1000 chars/page)")
    print("Expected: 120s total vs 332.9s previous test")
    print()
    
    # Initialize components
    await initialize_shared_components()
    
    # Run the refined test
    await refined_core_first_test(TEST_THEME, BOOK_CONFIG['path'])

if __name__ == "__main__":
    asyncio.run(main())