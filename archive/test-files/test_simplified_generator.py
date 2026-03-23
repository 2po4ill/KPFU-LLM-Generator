"""
Test simplified generator v2 with OOP lecture
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

async def test_simplified_generator():
    """Test the new simplified generator"""
    
    print("=" * 80)
    print("TESTING SIMPLIFIED GENERATOR V2")
    print("=" * 80)
    
    # Initialize
    print("\n1. Initializing...")
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator()
    await generator.initialize(model_manager=model_manager, pdf_processor=pdf_processor)
    
    # Test data
    theme = "Основы ООП: Классы, объекты, методы, наследование"
    book_ids = ['python_byte_ru']
    rpd_data = {
        'subject_title': 'Программирование на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информатики'
    }
    
    print(f"\n2. Generating lecture...")
    print(f"   Theme: {theme}")
    print(f"   Books: {book_ids}")
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
    
    print(f"\nSources used:")
    for source in result.sources_used:
        print(f"  - {source['title']}")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  ✗ {error}")
    
    if result.success:
        output_file = 'test_oop_lecture_v2.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        
        print(f"\n✓ Lecture saved to: {output_file}")
        print(f"  Content length: {len(result.content)} chars")
        print(f"  Word count: ~{len(result.content.split())} words")
        
        # Content quality check
        print("\n" + "=" * 80)
        print("CONTENT QUALITY CHECK")
        print("=" * 80)
        
        content_lower = result.content.lower()
        
        # Note: Generic examples like "person", "car" etc. may actually be FROM the book
        # Manual verification is needed to confirm if they're hallucinations
        common_examples = [
            'person', 'employee', 'vehicle', 'car', 'animal', 'dog'
        ]
        
        found = [ex for ex in common_examples if ex in content_lower]
        
        if found:
            print(f"\n📝 Note: Found common examples: {found}")
            print("   These may be from the book - check page citations to verify")
        else:
            print("\n✓ No common generic examples found")
        
        if result.confidence_score > 0.6:
            print(f"✓ Good confidence score: {result.confidence_score:.2%}")
        elif result.confidence_score > 0.4:
            print(f"📝 Moderate confidence score: {result.confidence_score:.2%}")
            print("   Manual review recommended")
        else:
            print(f"⚠ Low confidence score: {result.confidence_score:.2%}")
            print("   Manual review required")
        
        print("\n" + "=" * 80)
        print("PREVIEW (first 500 chars)")
        print("=" * 80)
        print(result.content[:500])
        print("...")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(test_simplified_generator())
