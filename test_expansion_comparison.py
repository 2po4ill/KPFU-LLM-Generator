"""
Test page expansion improvement
Compare string lecture generation before and after expansion
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator

async def test_expansion():
    """Test the page expansion improvement"""
    
    print("=" * 80)
    print("TESTING PAGE EXPANSION IMPROVEMENT")
    print("=" * 80)
    
    # Initialize
    print("\n1. Initializing...")
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator()
    await generator.initialize(model_manager=model_manager, pdf_processor=pdf_processor)
    
    # Test with strings theme (the problematic one)
    theme = "Работа со строками: форматирование, методы строк, срезы"
    book_ids = ['python_byte_ru']
    rpd_data = {
        'subject_title': 'Программирование на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информатики'
    }
    
    print(f"\n2. Generating lecture with page expansion...")
    print(f"   Theme: {theme}")
    print(f"   Expected improvement:")
    print(f"   - Before: 7 pages (2, 3, 8, 12, 13, 15, 16)")
    print(f"   - After: 12-15 pages (expanded ranges)")
    print(f"   This will take ~2-3 minutes...")
    
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=book_ids
    )
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print(f"\nSuccess: {result.success}")
    print(f"Generation time: {result.generation_time_seconds:.2f}s")
    print(f"Confidence score: {result.confidence_score:.2%}")
    
    print(f"\nStep times:")
    for step, time_taken in result.step_times.items():
        print(f"  {step}: {time_taken:.2f}s")
    
    if result.success:
        # Extract page numbers from citations
        pages = sorted(set([c['page_number'] for c in result.citations]))
        
        print(f"\n" + "=" * 80)
        print("PAGE SELECTION ANALYSIS")
        print("=" * 80)
        
        print(f"\nPages selected: {pages}")
        print(f"Total pages: {len(pages)}")
        
        # Check for continuous ranges
        ranges = []
        start = pages[0]
        prev = pages[0]
        
        for page in pages[1:]:
            if page == prev + 1:
                prev = page
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = page
                prev = page
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        
        print(f"Page ranges: {', '.join(ranges)}")
        
        # Compare with previous test
        print(f"\n" + "=" * 80)
        print("COMPARISON WITH PREVIOUS TEST")
        print("=" * 80)
        
        print("\nBefore expansion:")
        print("  - Pages: 2, 3, 8, 12, 13, 15, 16 (7 pages, scattered)")
        print("  - Content: ~500 words")
        print("  - Quality: Generic examples")
        
        print("\nAfter expansion:")
        print(f"  - Pages: {', '.join(map(str, pages))} ({len(pages)} pages)")
        print(f"  - Content: ~{len(result.content.split())} words")
        print(f"  - Quality: {'Better' if len(pages) > 10 else 'Check manually'}")
        
        # Content analysis
        print(f"\n" + "=" * 80)
        print("CONTENT ANALYSIS")
        print("=" * 80)
        
        word_count = len(result.content.split())
        print(f"\nWord count: {word_count}")
        print(f"Character count: {len(result.content)}")
        
        if word_count > 1000:
            print("✓ Good length (>1000 words)")
        elif word_count > 500:
            print("📝 Moderate length (500-1000 words)")
        else:
            print("⚠ Short length (<500 words)")
        
        # Save output
        output_file = 'test_string_lecture_expanded.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        
        print(f"\n✓ Lecture saved to: {output_file}")
        
        # Preview
        print(f"\n" + "=" * 80)
        print("PREVIEW (first 800 chars)")
        print("=" * 80)
        print(result.content[:800])
        print("...")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  ✗ {error}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    # Summary
    if result.success:
        improvement = len(pages) / 7  # 7 was the old count
        print(f"\n📊 Page count improvement: {improvement:.1f}x ({len(pages)} vs 7 pages)")
        
        if len(pages) >= 12:
            print("✅ SUCCESS: Page expansion working well!")
        elif len(pages) >= 10:
            print("📝 GOOD: Significant improvement, may need tuning")
        else:
            print("⚠ LIMITED: Some improvement, check parameters")

if __name__ == '__main__':
    asyncio.run(test_expansion())
