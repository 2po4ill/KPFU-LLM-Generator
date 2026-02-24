"""
Generate a lecture with offset fix and verify accuracy
"""
import asyncio
import sys
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def test_lecture_generation():
    print("Testing lecture generation with offset fix...")
    print("="*80)
    
    # Initialize components
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=model_manager,
        pdf_processor=pdf_processor
    )
    
    # Test with "Работа со строками" theme
    theme = "Работа со строками"
    rpd_data = {
        'subject': 'Программирование на Python',
        'degree': 'Бакалавриат',
        'profession': 'Информатика'
    }
    
    print(f"\nGenerating lecture for theme: {theme}")
    print("This will take ~4-5 minutes with two-stage generation...")
    print()
    
    # Generate lecture
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=['python_book']
    )
    
    print("\n" + "="*80)
    print("Generation Results:")
    print("="*80)
    
    if result.success:
        print(f"\n✓ Success!")
        print(f"  Generation time: {result.generation_time_seconds:.1f}s")
        print(f"  Confidence score: {result.confidence_score:.2%}")
        print(f"  Content length: {len(result.content)} chars")
        print(f"  Word count: ~{len(result.content.split())} words")
        
        print("\n" + "-"*80)
        print("Step Times:")
        for step, time_taken in result.step_times.items():
            print(f"  {step}: {time_taken:.1f}s")
        
        if result.warnings:
            print("\n" + "-"*80)
            print("Warnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
        
        # Save lecture
        with open('test_lecture_with_offset.md', 'w', encoding='utf-8') as f:
            f.write(result.content)
        print("\n✓ Lecture saved to: test_lecture_with_offset.md")
        
        # Show preview
        print("\n" + "="*80)
        print("Content Preview (first 500 chars):")
        print("="*80)
        print(result.content[:500])
        print("...")
        
        # Quick accuracy check
        print("\n" + "="*80)
        print("Quick Accuracy Check:")
        print("="*80)
        
        # Check if content mentions key string concepts from the book
        string_concepts = [
            'одинарные кавычки',
            'двойные кавычки',
            'тройные кавычки',
            'литеральные константы',
            'escape-последовательности',
            'необрабатываемые строки',
            'строки документации'
        ]
        
        found_concepts = []
        for concept in string_concepts:
            if concept.lower() in result.content.lower():
                found_concepts.append(concept)
        
        print(f"\nFound {len(found_concepts)}/{len(string_concepts)} key concepts:")
        for concept in found_concepts:
            print(f"  ✓ {concept}")
        
        if len(found_concepts) >= 4:
            print("\n✓ GOOD: Content appears to use book material!")
        else:
            print("\n⚠ WARNING: Content may still be hallucinated")
        
    else:
        print(f"\n✗ Failed!")
        for error in result.errors:
            print(f"  Error: {error}")
    
    print("\n" + "="*80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_lecture_generation())
