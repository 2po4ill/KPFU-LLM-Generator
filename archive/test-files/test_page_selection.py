"""
Test page selection to see which pages are being used
"""
import asyncio
import sys
import logging
sys.path.insert(0, 'app')

# Enable debug logging
logging.basicConfig(level=logging.INFO)

from core.model_manager import ModelManager
from literature.processor import PDFProcessor
from literature.embeddings import EmbeddingService
from generation.generator import ContentGenerator

async def test_page_selection():
    """Test page selection for OOP theme"""
    
    print("=" * 80)
    print("ТЕСТ ВЫБОРА СТРАНИЦ ДЛЯ ТЕМЫ ООП")
    print("=" * 80)
    
    # RPD data
    rpd_data = {
        'subject_title': 'Основы программирования на Python',
        'academic_degree': 'bachelor',
        'profession': 'Прикладная информатика',
        'department': 'Кафедра информационных технологий'
    }
    
    # OOP theme
    theme = "Основы ООП: Классы, объекты, методы, наследование"
    
    print(f"\n📝 Тема: {theme}")
    print(f"📖 Ожидаемые страницы: 101+ (где начинается ООП в книге)\n")
    
    # Initialize services
    print("🔧 Инициализация сервисов...")
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    embedding_service = EmbeddingService()
    await embedding_service.initialize(model_manager)
    
    # Process book
    print("📚 Обработка книги...")
    book_id = 'python_book_1'
    
    # Call async process_book (we're already in async context)
    book_data = await pdf_processor.process_book(
        'питон_мок_дата.pdf',
        book_id,
        model_manager=model_manager
    )
    print(f"✓ Обработано: {book_data['total_pages']} страниц")
    print(f"✓ TOC записей: {len(book_data['toc_entries'])}")
    
    # Add to embeddings
    print("🔢 Генерация эмбеддингов...")
    embedding_service.add_chunks_to_vector_store(
        book_data['chunks'],
        {
            'title': 'A Byte of Python',
            'authors': 'Swaroop C H',
            'book_id': book_id
        }
    )
    print(f"✓ Добавлено в векторное хранилище")
    
    # Test semantic search directly
    print(f"\n🔍 Поиск релевантных чанков для темы '{theme}'...")
    similar_chunks = embedding_service.search_similar_chunks(
        query=theme,
        book_id=book_id,
        top_k=20
    )
    
    print(f"\n📊 Найдено {len(similar_chunks)} релевантных чанков:")
    print("-" * 80)
    for i, chunk in enumerate(similar_chunks[:10], 1):
        page = chunk['metadata']['page_number']
        distance = chunk['distance']
        content_preview = chunk['content'][:100].replace('\n', ' ')
        print(f"{i}. Страница {page} (distance: {distance:.2f})")
        print(f"   {content_preview}...")
        print()
    
    # Now generate lecture
    print("\n📝 Генерация лекции...")
    print("=" * 80)
    
    generator = ContentGenerator()
    await generator.initialize(model_manager, embedding_service, pdf_processor)
    
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=[book_id]
    )
    
    print("=" * 80)
    
    if result.success:
        print(f"\n✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
        print(f"⏱️  Время: {result.generation_time_seconds:.1f}с")
        print(f"🎯 Уверенность: {result.confidence_score*100:.1f}%")
        
        # Check citations
        print(f"\n📚 ЦИТАТЫ В ЛЕКЦИИ:")
        for citation in result.citations[:5]:
            print(f"   - {citation['book_title']}, стр. {citation['page_number']}")
        
        # Save
        filename = "test_oop_lecture_debug.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"\n💾 Сохранено: {filename}")
        
    else:
        print(f"\n❌ ОШИБКА")
        for error in result.errors:
            print(f"   - {error}")

if __name__ == "__main__":
    asyncio.run(test_page_selection())
