"""
Test OOP lecture generation with new TOC-based page selection
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.literature.embeddings import EmbeddingService
from app.generation.generator import ContentGenerator

async def test_oop_lecture():
    """Generate OOP lecture with new approach"""
    
    print("=" * 80)
    print("TESTING OOP LECTURE GENERATION WITH NEW TOC APPROACH")
    print("=" * 80)
    
    # Initialize components
    print("\n1. Initializing components...")
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    embedding_service = EmbeddingService()
    
    # Initialize embedding model
    await embedding_service.initialize(model_manager)
    
    # Process book
    print("\n2. Processing book...")
    book_path = Path('питон_мок_дата.pdf')
    book_id = 'python_byte_ru'
    
    result = await pdf_processor.process_book(book_path, book_id, model_manager)
    
    if not result['success']:
        print(f"ERROR: {result}")
        return
    
    print(f"   ✓ Processed {result['total_pages']} pages")
    print(f"   ✓ Created {result['chunks_count']} chunks")
    print(f"   ✓ TOC pages: {result.get('toc_page_numbers', [])}")
    
    # Generate embeddings
    print("\n3. Generating embeddings...")
    embedding_service.add_chunks_to_vector_store(result['chunks'], book_id)
    print(f"   ✓ Generated embeddings for {len(result['chunks'])} chunks")
    
    # Initialize generator
    print("\n4. Initializing content generator...")
    generator = ContentGenerator()
    await generator.initialize(
        model_manager=model_manager,
        embedding_service=embedding_service,
        pdf_processor=pdf_processor
    )
    
    # Generate lecture
    theme = "Основы ООП: Классы, объекты, методы, наследование"
    rpd_data = {
        'subject_title': 'Программирование на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информатики'
    }
    
    print(f"\n5. Generating lecture for theme: {theme}")
    print("   This will take ~2-3 minutes...")
    
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=[book_id]
    )
    
    print("\n" + "=" * 80)
    print("GENERATION RESULTS")
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
    
    # Save lecture
    if result.success:
        output_file = 'test_oop_lecture_new_approach.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        
        print(f"\n✓ Lecture saved to: {output_file}")
        print(f"  Content length: {len(result.content)} chars")
        print(f"  Word count: ~{len(result.content.split())} words")
        
        # Check for hallucination indicators
        print("\n" + "=" * 80)
        print("HALLUCINATION CHECK")
        print("=" * 80)
        
        content_lower = result.content.lower()
        
        # Check for generic examples that indicate hallucination
        hallucination_indicators = [
            ('person', 'Generic Person class'),
            ('employee', 'Generic Employee class'),
            ('vehicle', 'Generic Vehicle class'),
            ('car', 'Generic Car class'),
            ('animal', 'Generic Animal class'),
            ('dog', 'Generic Dog class')
        ]
        
        found_indicators = []
        for indicator, description in hallucination_indicators:
            if indicator in content_lower:
                found_indicators.append(description)
        
        if found_indicators:
            print("\n⚠ WARNING: Possible hallucination detected!")
            print("  Found generic examples:")
            for indicator in found_indicators:
                print(f"    - {indicator}")
        else:
            print("\n✓ No obvious hallucination indicators found")
        
        # Check if content mentions the book
        if 'питон' in content_lower or 'byte of python' in content_lower:
            print("✓ Content references the source book")
        else:
            print("⚠ Content doesn't reference the source book")
        
        # Show first 500 chars
        print("\n" + "=" * 80)
        print("LECTURE PREVIEW (first 500 chars)")
        print("=" * 80)
        print(result.content[:500])
        print("...")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(test_oop_lecture())
