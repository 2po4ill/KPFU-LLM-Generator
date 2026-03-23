"""
TOC Analysis Performance Test
Testing the hypothesis that large TOC context to LLM is the major bottleneck

HYPOTHESIS: Problem 4 (Large Context to LLM) is the major bottleneck
- Large TOC context (10,000+ chars) causes slow LLM processing
- PDF processing might be cached or faster than expected
- TOC parsing is likely fast (regex operations)

TEST PLAN:
1. Measure each step individually
2. Test different TOC context sizes
3. Identify the real bottleneck
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

# Test configuration
TEST_THEME = 'Работа со строками'
BOOK_PATH = 'Изучаем_Питон.pdf'

async def initialize_components():
    """Initialize components for testing"""
    print("🔧 Initializing components...")
    start_time = time.time()
    
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    
    generator = ContentGenerator()
    await generator.initialize(model_manager, pdf_processor)
    
    init_time = time.time() - start_time
    print(f"✓ Components ready ({init_time:.1f}s)")
    
    return generator, model_manager, pdf_processor

async def test_step_by_step_performance(generator, pdf_processor):
    """Test each step of TOC analysis individually"""
    
    print(f"\n🔍 STEP-BY-STEP TOC ANALYSIS PERFORMANCE TEST")
    print(f"{'='*60}")
    print(f"Theme: {TEST_THEME}")
    print(f"Book: {BOOK_PATH}")
    print()
    
    step_times = {}
    
    # STEP 1: PDF Processing
    print("📚 STEP 1: PDF Processing")
    step1_start = time.time()
    
    pages_data = pdf_processor.extract_text_from_pdf(BOOK_PATH)
    if not pages_data['success']:
        print(f"❌ Failed to extract pages from {BOOK_PATH}")
        return
    
    step_times['pdf_processing'] = time.time() - step1_start
    print(f"✓ PDF Processing: {step_times['pdf_processing']:.1f}s")
    print(f"  Pages extracted: {len(pages_data['pages'])}")
    
    # STEP 2: Page Offset Detection
    print("\n🔍 STEP 2: Page Offset Detection")
    step2_start = time.time()
    
    page_offset = pdf_processor.detect_page_offset(pages_data['pages'])
    
    step_times['offset_detection'] = time.time() - step2_start
    print(f"✓ Offset Detection: {step_times['offset_detection']:.1f}s")
    print(f"  Page offset: {page_offset}")
    
    # STEP 3: TOC Page Finding
    print("\n📖 STEP 3: TOC Page Finding")
    step3_start = time.time()
    
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    
    step_times['toc_finding'] = time.time() - step3_start
    print(f"✓ TOC Finding: {step_times['toc_finding']:.1f}s")
    print(f"  TOC pages: {toc_page_numbers}")
    
    if not toc_page_numbers:
        print("❌ No TOC found, cannot continue test")
        return
    
    # STEP 4: TOC Text Extraction
    print("\n📄 STEP 4: TOC Text Extraction")
    step4_start = time.time()
    
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    # Limit TOC text size (as in original code)
    if len(toc_text) > 10000:
        toc_text = toc_text[:10000]
    
    step_times['toc_extraction'] = time.time() - step4_start
    print(f"✓ TOC Extraction: {step_times['toc_extraction']:.1f}s")
    print(f"  TOC text length: {len(toc_text):,} characters")
    
    # STEP 5: TOC Parsing with Regex
    print("\n🔧 STEP 5: TOC Parsing with Regex")
    step5_start = time.time()
    
    sections = generator._parse_toc_with_regex(toc_text)
    
    step_times['toc_parsing'] = time.time() - step5_start
    print(f"✓ TOC Parsing: {step_times['toc_parsing']:.1f}s")
    print(f"  Sections parsed: {len(sections)}")
    
    # STEP 6: TOC Formatting for LLM
    print("\n📝 STEP 6: TOC Formatting for LLM")
    step6_start = time.time()
    
    formatted_sections = []
    for section in sections:
        formatted_sections.append(
            f"{section['number']} {section['title']} (pages {section['page']}-{section['end_page']})"
        )
    
    full_toc = '\n'.join(formatted_sections)
    
    step_times['toc_formatting'] = time.time() - step6_start
    print(f"✓ TOC Formatting: {step_times['toc_formatting']:.1f}s")
    print(f"  Formatted TOC length: {len(full_toc):,} characters")
    
    # STEP 7: LLM Processing (THE SUSPECTED BOTTLENECK)
    print(f"\n🤖 STEP 7: LLM Processing (SUSPECTED BOTTLENECK)")
    step7_start = time.time()
    
    llm_model = await generator.model_manager.get_llm_model()
    
    prompt = f"""Тема: "{TEST_THEME}"

Выбери разделы, которые учат этой теме.

Оглавление:
{full_toc}

Ответ (номера разделов):"""
    
    print(f"  Prompt length: {len(prompt):,} characters")
    print(f"  Processing with LLM...")
    
    response = await llm_model.generate(
        model="llama3.1:8b",
        prompt=prompt,
        options={
            "temperature": 0.1,
            "num_predict": 100
        }
    )
    
    step_times['llm_processing'] = time.time() - step7_start
    print(f"✓ LLM Processing: {step_times['llm_processing']:.1f}s")
    
    response_text = response.get('response', '').strip()
    print(f"  LLM response: {response_text}")
    
    # STEP 8: Response Parsing
    print(f"\n🔍 STEP 8: Response Parsing")
    step8_start = time.time()
    
    section_numbers = generator._parse_section_numbers(response_text)
    
    step_times['response_parsing'] = time.time() - step8_start
    print(f"✓ Response Parsing: {step_times['response_parsing']:.1f}s")
    print(f"  Section numbers: {section_numbers}")
    
    # TOTAL TIME
    total_time = sum(step_times.values())
    
    # RESULTS ANALYSIS
    print(f"\n{'='*60}")
    print("STEP-BY-STEP PERFORMANCE RESULTS")
    print("="*60)
    
    print(f"\n📊 TIMING BREAKDOWN:")
    for step, duration in step_times.items():
        percentage = (duration / total_time) * 100
        print(f"  {step.replace('_', ' ').title()}: {duration:.1f}s ({percentage:.1f}%)")
    
    print(f"\n  TOTAL TIME: {total_time:.1f}s")
    
    # IDENTIFY BOTTLENECK
    print(f"\n🎯 BOTTLENECK ANALYSIS:")
    
    bottleneck_step = max(step_times.items(), key=lambda x: x[1])
    bottleneck_name, bottleneck_time = bottleneck_step
    bottleneck_percentage = (bottleneck_time / total_time) * 100
    
    print(f"  MAJOR BOTTLENECK: {bottleneck_name.replace('_', ' ').title()}")
    print(f"  Time: {bottleneck_time:.1f}s ({bottleneck_percentage:.1f}% of total)")
    
    if bottleneck_name == 'llm_processing':
        print(f"  ✅ HYPOTHESIS CONFIRMED: LLM processing is the bottleneck")
    elif bottleneck_name == 'pdf_processing':
        print(f"  ❌ HYPOTHESIS REJECTED: PDF processing is the bottleneck")
    else:
        print(f"  🤔 UNEXPECTED: {bottleneck_name} is the bottleneck")
    
    return step_times, full_toc

async def test_toc_context_size_impact(generator):
    """Test how TOC context size affects LLM processing time"""
    
    print(f"\n🔍 TOC CONTEXT SIZE IMPACT TEST")
    print(f"{'='*60}")
    
    # Create different sized TOC contexts
    base_toc_line = "7.4 Работа со строками (pages 36-38)"
    
    test_sizes = [
        (10, "Small TOC"),
        (50, "Medium TOC"), 
        (100, "Large TOC"),
        (200, "Very Large TOC"),
        (500, "Huge TOC")
    ]
    
    llm_model = await generator.model_manager.get_llm_model()
    
    results = []
    
    for num_lines, size_name in test_sizes:
        print(f"\n📏 Testing {size_name} ({num_lines} lines)")
        
        # Create TOC of specified size
        toc_lines = []
        for i in range(num_lines):
            toc_lines.append(f"{i+1}.{i%10} Section {i+1} (pages {i*2+10}-{i*2+12})")
        
        full_toc = '\n'.join(toc_lines)
        
        prompt = f"""Тема: "{TEST_THEME}"

Выбери разделы, которые учат этой теме.

Оглавление:
{full_toc}

Ответ (номера разделов):"""
        
        context_size = len(prompt)
        print(f"  Context size: {context_size:,} characters")
        
        # Measure LLM processing time
        start_time = time.time()
        
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={
                "temperature": 0.1,
                "num_predict": 100
            }
        )
        
        processing_time = time.time() - start_time
        
        results.append({
            'size_name': size_name,
            'num_lines': num_lines,
            'context_size': context_size,
            'processing_time': processing_time
        })
        
        print(f"  Processing time: {processing_time:.1f}s")
    
    # ANALYZE RESULTS
    print(f"\n📊 CONTEXT SIZE IMPACT ANALYSIS:")
    print(f"{'Size':<15} {'Lines':<8} {'Context':<12} {'Time':<8} {'Rate':<12}")
    print(f"{'-'*60}")
    
    for result in results:
        chars_per_sec = result['context_size'] / result['processing_time']
        print(f"{result['size_name']:<15} {result['num_lines']:<8} {result['context_size']:,<12} {result['processing_time']:<8.1f} {chars_per_sec:,.0f}/s")
    
    # Check if processing time scales with context size
    if len(results) >= 2:
        time_increase = results[-1]['processing_time'] / results[0]['processing_time']
        size_increase = results[-1]['context_size'] / results[0]['context_size']
        
        print(f"\n🔍 SCALING ANALYSIS:")
        print(f"  Context size increase: {size_increase:.1f}x")
        print(f"  Processing time increase: {time_increase:.1f}x")
        
        if time_increase > size_increase * 0.8:
            print(f"  ✅ CONFIRMED: Processing time scales with context size")
            print(f"  💡 OPTIMIZATION: Reduce TOC context size for faster processing")
        else:
            print(f"  🤔 UNEXPECTED: Processing time doesn't scale linearly with context")
    
    return results

async def main():
    print("TOC ANALYSIS PERFORMANCE TEST")
    print("="*60)
    print("Testing hypothesis: Large TOC context to LLM is the major bottleneck")
    print()
    
    # Initialize components
    generator, model_manager, pdf_processor = await initialize_components()
    
    # Test 1: Step-by-step performance
    step_times, full_toc = await test_step_by_step_performance(generator, pdf_processor)
    
    # Test 2: Context size impact
    context_results = await test_toc_context_size_impact(generator)
    
    # FINAL CONCLUSIONS
    print(f"\n{'='*60}")
    print("FINAL CONCLUSIONS")
    print("="*60)
    
    bottleneck_step = max(step_times.items(), key=lambda x: x[1])
    bottleneck_name, bottleneck_time = bottleneck_step
    
    print(f"\n🎯 BOTTLENECK IDENTIFICATION:")
    print(f"  Primary bottleneck: {bottleneck_name.replace('_', ' ').title()} ({bottleneck_time:.1f}s)")
    
    if bottleneck_name == 'llm_processing':
        print(f"  ✅ Your hypothesis was CORRECT!")
        print(f"  💡 Optimization strategy: Reduce TOC context size")
        
        # Calculate potential improvement
        current_context_size = len(full_toc)
        if context_results:
            small_time = context_results[0]['processing_time']
            large_time = context_results[-1]['processing_time']
            potential_improvement = (large_time - small_time) / large_time * 100
            
            print(f"  📈 Potential improvement: {potential_improvement:.0f}% faster with smaller context")
    else:
        print(f"  ❌ Hypothesis was incorrect - {bottleneck_name} is the real bottleneck")
    
    print(f"\n🚀 RECOMMENDED OPTIMIZATIONS:")
    
    if bottleneck_name == 'llm_processing':
        print(f"  1. Reduce TOC context size (current: {len(full_toc):,} chars)")
        print(f"  2. Pre-filter TOC sections before sending to LLM")
        print(f"  3. Use chunked processing for very large TOCs")
    elif bottleneck_name == 'pdf_processing':
        print(f"  1. Implement PDF processing cache")
        print(f"  2. Pre-process and store extracted pages")
        print(f"  3. Use incremental PDF processing")
    else:
        print(f"  1. Optimize {bottleneck_name} specifically")
        print(f"  2. Consider caching strategies")
        print(f"  3. Profile deeper into the bottleneck")
    
    print(f"\n✅ TOC ANALYSIS PERFORMANCE TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())