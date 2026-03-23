"""
Test semantic validation with claim extraction
"""
import asyncio
import sys
sys.path.insert(0, 'app')

from core.model_manager import ModelManager
from literature.processor import PDFProcessor
from literature.embeddings import EmbeddingService
from generation.generator import ContentGenerator

async def test_validation():
    """Test semantic validation"""
    
    print("=" * 80)
    print("ТЕСТ СЕМАНТИЧЕСКОЙ ВАЛИДАЦИИ С ИЗВЛЕЧЕНИЕМ УТВЕРЖДЕНИЙ")
    print("=" * 80)
    
    # RPD data
    rpd_data = {
        'subject_title': 'Основы программирования на Python',
        'academic_degree': 'bachelor',
        'profession': 'Прикладная информатика',
        'department': 'Кафедра информационных технологий'
    }
    
    # Theme
    theme = "Функции: Определение функций, параметры, возврат значений"
    
    print(f"\n📝 Тема: {theme}")
    print(f"🎯 Цель: Проверить извлечение и валидацию утверждений\n")
    
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
    book_data = pdf_processor.process_book('питон_мок_дата.pdf', book_id)
    print(f"✓ Обработано: {book_data['total_pages']} страниц")
    
    # Add to embeddings
    print("🔢 Генерация эмбеддингов...")
    embedding_service.add_chunks_to_vector_store(
        book_data['chunks'],
        {
            'title': book_data.get('title', 'A Byte of Python'),
            'authors': book_data.get('authors', 'Swaroop C H'),
            'book_id': book_id
        }
    )
    print(f"✓ Добавлено в векторное хранилище")
    
    # Generate lecture with validation
    print(f"\n📝 Генерация лекции с валидацией...")
    print("-" * 80)
    
    generator = ContentGenerator()
    await generator.initialize(model_manager, embedding_service, pdf_processor)
    
    import time
    start_time = time.time()
    
    result = await generator.generate_lecture(
        theme=theme,
        rpd_data=rpd_data,
        book_ids=[book_id]
    )
    
    elapsed = time.time() - start_time
    
    print("-" * 80)
    
    if result.success:
        print(f"\n✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА")
        print(f"⏱️  Общее время: {elapsed:.1f}с")
        print(f"\n📊 ДЕТАЛИ ВАЛИДАЦИИ:")
        print(f"   Уверенность: {result.confidence_score*100:.1f}%")
        
        # Show step times
        print(f"\n⏱️  ВРЕМЯ ПО ШАГАМ:")
        for step, time_taken in result.step_times.items():
            print(f"   {step}: {time_taken:.1f}с")
        
        # Check for validation warnings
        if result.warnings:
            print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for warning in result.warnings:
                print(f"   - {warning}")
        
        # Check for unsupported claims in content
        unsupported_count = result.content.count('[ТРЕБУЕТ ПРОВЕРКИ')
        if unsupported_count > 0:
            print(f"\n⚠️  НАЙДЕНО НЕПОДТВЕРЖДЕННЫХ УТВЕРЖДЕНИЙ: {unsupported_count}")
            print(f"   Эти утверждения помечены в тексте для проверки преподавателем")
        else:
            print(f"\n✅ ВСЕ УТВЕРЖДЕНИЯ ПОДТВЕРЖДЕНЫ ИСТОЧНИКАМИ")
        
        # Save result
        filename = "test_lecture_with_validation.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"\n💾 Сохранено: {filename}")
        
        # Show preview
        print(f"\n📄 ПРЕВЬЮ (первые 800 символов):")
        print("=" * 80)
        print(result.content[:800])
        if '[ТРЕБУЕТ ПРОВЕРКИ' in result.content[:800]:
            print("\n⚠️  Видны помеченные утверждения!")
        print("=" * 80)
        
    else:
        print(f"\n❌ ОШИБКА")
        for error in result.errors:
            print(f"   - {error}")

if __name__ == "__main__":
    asyncio.run(test_validation())
