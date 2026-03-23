"""
Complete End-to-End Test: RPD → Book Upload → Content Generation
Using the Python beginner book (питон_мок_дата.pdf)

Run with: python test_complete_pipeline.py
"""

import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from literature.processor import get_pdf_processor
from literature.embeddings import get_embedding_service
from generation.generator import get_content_generator
from core.database import generate_request_fingerprint


async def test_complete_pipeline():
    """Test the complete content generation pipeline"""
    
    print("=" * 70)
    print("KPFU LLM Generator - Complete Pipeline Test")
    print("=" * 70)
    
    # ========== STEP 1: Submit RPD Data ==========
    print("\n📋 STEP 1: Submitting RPD Data")
    print("-" * 70)
    
    rpd_data = {
        "subject_title": "Основы программирования на Python",
        "academic_degree": "bachelor",
        "profession": "Прикладная информатика",
        "total_hours": 144,
        "department": "Кафедра информационных технологий",
        "faculty": "Институт вычислительной математики и информационных технологий",
        "lecture_themes": [
            {
                "title": "Введение в Python",
                "order": 1,
                "hours": 4,
                "description": "Основы языка Python, установка, первая программа"
            },
            {
                "title": "Переменные и типы данных",
                "order": 2,
                "hours": 4,
                "description": "Числа, строки, списки, словари"
            },
            {
                "title": "Функции в Python",
                "order": 3,
                "hours": 6,
                "description": "Определение функций, параметры, возвращаемые значения"
            }
        ],
        "literature_references": [
            {
                "authors": "Swaroop C H",
                "title": "A Byte of Python",
                "year": 2013,
                "publisher": "Open Source"
            }
        ]
    }
    
    # Generate fingerprint
    fingerprint = generate_request_fingerprint(rpd_data)
    print(f"✓ RPD Data prepared")
    print(f"  Subject: {rpd_data['subject_title']}")
    print(f"  Degree: {rpd_data['academic_degree']}")
    print(f"  Themes: {len(rpd_data['lecture_themes'])}")
    print(f"  Fingerprint: {fingerprint}")
    
    # ========== STEP 2: Process and Upload Book ==========
    print(f"\n📚 STEP 2: Processing Book")
    print("-" * 70)
    
    pdf_path = Path("питон_мок_дата.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Book not found: {pdf_path}")
        return
    
    # Process PDF
    pdf_processor = get_pdf_processor()
    book_id = "python_byte_001"
    
    print(f"  Processing: {pdf_path.name}")
    processing_result = pdf_processor.process_book(pdf_path, book_id)
    
    if not processing_result['success']:
        print(f"❌ PDF processing failed: {processing_result.get('error')}")
        return
    
    print(f"✓ Book processed successfully")
    print(f"  Pages: {processing_result['total_pages']}")
    print(f"  Chunks: {processing_result['chunks_count']}")
    print(f"  TOC entries: {len(processing_result['toc_entries'])}")
    print(f"  Keywords: {', '.join([w for w, _ in processing_result['keywords'][:5]])}")
    
    # ========== STEP 3: Generate Embeddings ==========
    print(f"\n🔢 STEP 3: Generating Embeddings")
    print("-" * 70)
    
    # Initialize embedding service (mock mode for now)
    embedding_service = await get_embedding_service(use_mock=True)
    
    book_metadata = {
        'title': 'A Byte of Python (Russian)',
        'authors': 'Swaroop C H',
        'year': 2013
    }
    
    print(f"  Adding {processing_result['chunks_count']} chunks to vector store...")
    embedding_result = embedding_service.add_chunks_to_vector_store(
        processing_result['chunks'],
        book_metadata
    )
    
    if embedding_result['success']:
        print(f"✓ Embeddings generated")
        print(f"  Chunks added: {embedding_result['chunks_added']}")
        if embedding_result.get('mock'):
            print(f"  ⚠️  Using mock embeddings (for testing)")
    else:
        print(f"❌ Embedding generation failed: {embedding_result.get('error')}")
        return
    
    # ========== STEP 4: Test Semantic Search ==========
    print(f"\n🔍 STEP 4: Testing Semantic Search")
    print("-" * 70)
    
    test_queries = [
        "Введение в Python",
        "Функции в Python",
        "Переменные и типы данных"
    ]
    
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        similar_chunks = embedding_service.search_similar_chunks(
            query=query,
            book_id=book_id,
            top_k=3
        )
        
        if similar_chunks:
            print(f"  ✓ Found {len(similar_chunks)} relevant chunks")
            for i, chunk in enumerate(similar_chunks[:2], 1):
                preview = chunk['content'][:100].replace('\n', ' ')
                print(f"    {i}. Page {chunk['metadata']['page_number']}: {preview}...")
        else:
            print(f"  ⚠️  No chunks found (mock mode)")
    
    # ========== STEP 5: Generate Content ==========
    print(f"\n✨ STEP 5: Generating Lecture Content")
    print("-" * 70)
    
    # Initialize content generator
    generator = await get_content_generator(
        model_manager=None,  # Using mock
        embedding_service=embedding_service,
        pdf_processor=pdf_processor,
        use_mock=True
    )
    
    # Generate lecture for first theme
    theme = rpd_data['lecture_themes'][0]['title']
    print(f"  Theme: {theme}")
    print(f"  Generating content...")
    
    generation_result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=[book_id]
    )
    
    if generation_result.success:
        print(f"\n✓ Content generated successfully!")
        print(f"\n  Performance Metrics:")
        print(f"    Total time: {generation_result.generation_time_seconds:.2f}s")
        print(f"    Confidence: {generation_result.confidence_score:.2%}")
        
        print(f"\n  Step Breakdown:")
        for step_name, step_time in generation_result.step_times.items():
            step_label = step_name.replace('_', ' ').title()
            print(f"    {step_label}: {step_time:.2f}s")
        
        print(f"\n  Sources Used:")
        for source in generation_result.sources_used:
            print(f"    - {source['title']}")
        
        print(f"\n  Citations: {len(generation_result.citations)}")
        
        if generation_result.warnings:
            print(f"\n  ⚠️  Warnings:")
            for warning in generation_result.warnings:
                print(f"    - {warning}")
        
        # Show content preview
        print(f"\n📄 Generated Content Preview:")
        print("-" * 70)
        content_lines = generation_result.content.split('\n')
        preview_lines = content_lines[:20]  # First 20 lines
        for line in preview_lines:
            print(f"  {line}")
        
        if len(content_lines) > 20:
            print(f"  ... ({len(content_lines) - 20} more lines)")
        
    else:
        print(f"\n❌ Content generation failed")
        if generation_result.errors:
            print(f"  Errors:")
            for error in generation_result.errors:
                print(f"    - {error}")
    
    # ========== STEP 6: Summary ==========
    print(f"\n" + "=" * 70)
    print("📊 PIPELINE TEST SUMMARY")
    print("=" * 70)
    
    print(f"\n✓ RPD Data: Fingerprint {fingerprint}")
    print(f"✓ Book Processing: {processing_result['total_pages']} pages, {processing_result['chunks_count']} chunks")
    print(f"✓ Embeddings: {embedding_result['chunks_added']} chunks indexed")
    print(f"✓ Content Generation: {generation_result.generation_time_seconds:.2f}s")
    
    if generation_result.success:
        print(f"\n🎉 Complete pipeline test PASSED!")
        print(f"\nNext steps:")
        print(f"  1. Integrate real Ollama LLM for better content")
        print(f"  2. Add real embeddings (sentence-transformers)")
        print(f"  3. Enhance semantic validation")
        print(f"  4. Add lab work generation")
    else:
        print(f"\n⚠️  Pipeline test completed with issues")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())
