"""
Test multi-book generation - ONE lecture from MULTIPLE books
This is the correct multi-book approach: combine pages from all books into one lecture
"""
import asyncio
import time
from pathlib import Path

from app.core.model_manager import ModelManager
from app.literature.processor import get_pdf_processor
from app.generation.generator_v3 import get_optimized_content_generator


async def test_multi_book_lecture():
    """Test generating ONE lecture from MULTIPLE books"""
    
    print("=" * 80)
    print("MULTI-BOOK SINGLE LECTURE TEST")
    print("=" * 80)
    
    theme = "Работа со строками"
    
    # Multiple books configuration
    books = [
        {"path": "Изучаем_Питон.pdf", "id": "izuchaem_python"},
        {"path": "ООП_на_питоне.pdf", "id": "oop_python"},
        {"path": "питон_мок_дата.pdf", "id": "byte_of_python"}
    ]
    
    book_ids = [book["id"] for book in books]
    
    print(f"\nTheme: {theme}")
    print(f"Books: {len(books)}")
    for book in books:
        print(f"  - {book['id']}: {book['path']}")
    print(f"\nExpected: ONE comprehensive lecture from ALL books combined")
    print(f"Architecture: Batched + Queued + Deduplication")
    
    # Initialize components
    print("\n" + "=" * 80)
    print("INITIALIZATION")
    print("=" * 80)
    
    start_init = time.time()
    
    model_manager = ModelManager()
    await model_manager.initialize()
    pdf_processor = get_pdf_processor()
    generator = await get_optimized_content_generator()
    
    await generator.initialize(model_manager, pdf_processor)
    
    init_time = time.time() - start_init
    print(f"✓ Components initialized ({init_time:.1f}s)")
    
    # Initialize all books
    print(f"\nInitializing {len(books)} books...")
    for book in books:
        start_book = time.time()
        book_result = await generator.initialize_book(book['path'], book['id'])
        book_time = time.time() - start_book
        
        if book_result['success']:
            cached = " (cached)" if book_result.get('cached', False) else ""
            print(f"✓ {book['id']}: {book_time:.1f}s{cached}")
        else:
            print(f"✗ {book['id']}: FAILED - {book_result.get('error', 'Unknown error')}")
            return
    
    # Generate ONE lecture from ALL books
    print("\n" + "=" * 80)
    print("MULTI-BOOK GENERATION")
    print("=" * 80)
    print(f"Generating ONE lecture from {len(books)} books...")
    
    start_gen = time.time()
    
    result = await generator.generate_lecture_optimized(
        theme=theme,
        book_ids=book_ids,  # ALL books at once
        rpd_data={}
    )
    
    gen_time = time.time() - start_gen
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if result.success:
        print(f"✓ SUCCESS - Generated ONE lecture from {len(books)} books")
        
        print(f"\n📊 TIMING:")
        print(f"  Total Time: {gen_time:.1f}s")
        if hasattr(result, 'step_times'):
            for step_name, step_time in result.step_times.items():
                print(f"  {step_name}: {step_time:.1f}s")
        
        print(f"\n📄 CONTENT:")
        print(f"  Length: {len(result.content):,} characters")
        print(f"  Words: {len(result.content.split()):,} words")
        
        print(f"\n📚 SOURCES:")
        if hasattr(result, 'sources_used'):
            for source in result.sources_used:
                print(f"  - {source['book_id']}: {source['title']}")
        
        print(f"\n🔍 OPTIMIZATION METRICS:")
        if hasattr(result, 'cached_pages_used'):
            print(f"  Cached Pages: {result.cached_pages_used}")
        if hasattr(result, 'extracted_pages_count'):
            print(f"  Extracted Pages: {result.extracted_pages_count}")
        if hasattr(result, 'toc_cache_hit'):
            print(f"  TOC Cache Hit: {'Yes' if result.toc_cache_hit else 'No'}")
        
        # Save lecture
        output_filename = f"lecture_{theme.replace(' ', '_')}_multi_book.md"
        output_path = Path(output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Лекция: {theme}\n\n")
            f.write(f"**Источники**: {len(books)} книги\n")
            for book in books:
                f.write(f"- {book['id']}: {book['path']}\n")
            f.write(f"\n**Архитектура**: Multi-Book + Batched + Deduplication\n")
            f.write(f"**Время генерации**: {gen_time:.1f}s\n")
            f.write(f"**Количество слов**: {len(result.content.split()):,}\n\n")
            f.write("---\n\n")
            f.write(result.content)
        
        print(f"\n💾 Lecture saved to: {output_filename}")
        
        # Show content preview
        print(f"\n📖 CONTENT PREVIEW:")
        print("-" * 80)
        print(result.content[:500])
        print("...")
        print("-" * 80)
        
        # Analysis
        print(f"\n📈 ANALYSIS:")
        single_book_words = 2941  # From previous test
        multi_book_words = len(result.content.split())
        improvement = ((multi_book_words - single_book_words) / single_book_words) * 100
        
        print(f"  Single Book (Изучаем Python): {single_book_words} words")
        print(f"  Multi-Book (3 books): {multi_book_words} words")
        if improvement > 0:
            print(f"  Improvement: +{improvement:.1f}% more content")
        else:
            print(f"  Difference: {improvement:.1f}%")
        
        print(f"\n✅ MULTI-BOOK GENERATION SUCCESSFUL")
        print(f"   - Combined pages from {len(books)} books")
        print(f"   - Deduplicated concepts across all sources")
        print(f"   - Generated comprehensive single lecture")
        
    else:
        print(f"✗ FAILED: {result.error}")
        if result.warnings:
            print(f"\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_multi_book_lecture())
