"""
Test content generation with Gemma 3 27B
Observe the quality and make adjustments
"""

import asyncio
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def test_gemma_content_generation():
    """Test full lecture generation with Gemma 3 27B"""
    
    print("=" * 80)
    print("Testing Content Generation with Gemma 3 27B")
    print("=" * 80)
    
    # Initialize components
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    # Test theme
    theme = "Работа со строками: форматирование, методы строк, срезы"
    
    # RPD data
    rpd_data = {
        'subject_title': 'Основы программирования на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информационных систем'
    }
    
    # Book IDs
    book_ids = ['python_book_1']
    
    print(f"\nTheme: {theme}")
    print(f"Book IDs: {book_ids}")
    print(f"\nStarting generation...")
    print("-" * 80)
    
    start_time = time.time()
    
    # Generate lecture
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=book_ids
    )
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("GENERATION RESULTS")
    print("=" * 80)
    
    print(f"\nSuccess: {result.success}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Confidence Score: {result.confidence_score:.2%}")
    
    print(f"\nStep Times:")
    for step, duration in result.step_times.items():
        print(f"  {step}: {duration:.2f}s")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  - {error}")
    
    print(f"\nSources Used:")
    for source in result.sources_used:
        print(f"  - {source['title']} (ID: {source['book_id']})")
    
    print(f"\nContent Length: {len(result.content)} chars")
    print(f"Word Count: ~{len(result.content.split())} words")
    
    # Save to file
    output_file = Path('test_gemma_lecture.md')
    output_file.write_text(result.content, encoding='utf-8')
    print(f"\n✓ Saved to: {output_file}")
    
    # Show preview
    print("\n" + "=" * 80)
    print("CONTENT PREVIEW (first 1000 chars)")
    print("=" * 80)
    print(result.content[:1000])
    print("...")
    
    print("\n" + "=" * 80)
    print("CONTENT PREVIEW (last 500 chars)")
    print("=" * 80)
    print("...")
    print(result.content[-500:])
    
    print("\n" + "=" * 80)
    print("Test Complete - Review test_gemma_lecture.md for full content")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_gemma_content_generation())
