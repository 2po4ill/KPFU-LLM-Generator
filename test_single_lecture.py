"""
Test single lecture generation with increased token limit
"""
import asyncio
import sys
sys.path.insert(0, 'app')

from core.model_manager import ModelManager
from literature.processor import PDFProcessor
from literature.embeddings import EmbeddingService
from generation.generator import ContentGenerator

async def test_single_lecture():
    """Test generating a single lecture"""
    
    # RPD data
    rpd_data = {
        'subject_title': 'Основы программирования на Python',
        'academic_degree': 'bachelor',
        'profession': 'Прикладная информатика',
        'department': 'Кафедра информационных технологий'
    }
    
    # Theme
    theme = "Функции"
    description = "Определение функций, параметры, возврат значений, области видимости"
    
    print("=" * 80)
    print(f"ТЕСТ ГЕНЕРАЦИИ ЛЕКЦИИ С УВЕЛИЧЕННЫМ ЛИМИТОМ")
    print("=" * 80)
    print(f"\n📝 Тема: {theme}")
    print(f"📋 Описание: {description}")
    print(f"🎯 Целевой размер: 2000-2500 слов")
    print(f"⚙️  Настройки: 6000 токенов, 20 страниц контекста\n")
    
    # Initialize services
    print("🔧 Инициализация сервисов...")
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    embedding_service = EmbeddingService(model_manager)
    
    # Process book
    print("📚 Обработка книги...")
    book_id = 'python_book_1'
    book_data = pdf_processor.process_book('питон_мок_дата.pdf', book_id)
    print(f"✓ Обработано: {book_data['total_pages']} страниц, {len(book_data['chunks'])} чанков")
    
    # Add to embeddings
    print("🔢 Генерация эмбеддингов...")
    await embedding_service.add_chunks_to_vector_store(book_data['chunks'], book_id)
    print(f"✓ Добавлено в векторное хранилище")
    
    # Generate lecture
    print(f"\n📝 Генерация лекции...")
    print("-" * 80)
    
    generator = ContentGenerator()
    await generator.initialize(model_manager, embedding_service, pdf_processor)
    
    result = await generator.generate_lecture(
        theme=f"{theme}: {description}",
        rpd_data=rpd_data,
        book_ids=[book_id]
    )
    
    print("-" * 80)
    
    if result.success:
        # Count words
        word_count = len(result.content.split())
        
        print(f"\n✅ УСПЕШНО СГЕНЕРИРОВАНО")
        print(f"⏱️  Время: {result.generation_time_seconds:.1f}с")
        print(f"📊 Слов: {word_count}")
        print(f"📄 Символов: {len(result.content)}")
        print(f"🎯 Уверенность: {result.confidence_score*100:.0f}%")
        print(f"📚 Источников: {len(result.sources_used)}")
        print(f"📖 Цитат: {len(result.citations)}")
        
        # Save
        filename = f"test_lecture_{theme.lower()}_extended.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"\n💾 Сохранено: {filename}")
        
        # Show preview
        print(f"\n📄 ПРЕВЬЮ (первые 500 символов):")
        print("=" * 80)
        print(result.content[:500] + "...")
        print("=" * 80)
        
        # Analysis
        if word_count < 1500:
            print(f"\n⚠️  Лекция короче ожидаемого ({word_count} < 1500 слов)")
        elif word_count < 2000:
            print(f"\n✓ Лекция приемлемой длины ({word_count} слов)")
        else:
            print(f"\n✅ Отличная длина лекции ({word_count} слов)!")
            
    else:
        print(f"\n❌ ОШИБКА")
        for error in result.errors:
            print(f"   - {error}")

if __name__ == "__main__":
    asyncio.run(test_single_lecture())
