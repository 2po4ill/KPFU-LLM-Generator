"""
Generate complete 12-lecture Python course
Using real Ollama LLM and the Python book

Run with: python generate_full_course.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from literature.processor import get_pdf_processor
from literature.embeddings import get_embedding_service
from generation.generator import get_content_generator
from core.database import generate_request_fingerprint
from core.model_manager import ModelManager


# 12-lecture curriculum
PYTHON_COURSE_THEMES = [
    {
        "title": "Введение в Python",
        "order": 1,
        "hours": 12,
        "description": "История Python, установка, первая программа Hello World"
    },
    {
        "title": "Основы синтаксиса и переменные",
        "order": 2,
        "hours": 12,
        "description": "Переменные, типы данных, операторы"
    },
    {
        "title": "Строки и форматирование",
        "order": 3,
        "hours": 12,
        "description": "Работа со строками, методы строк, форматирование"
    },
    {
        "title": "Числа и математические операции",
        "order": 4,
        "hours": 12,
        "description": "Целые числа, float, математические функции"
    },
    {
        "title": "Условные операторы",
        "order": 5,
        "hours": 12,
        "description": "if, elif, else, логические операторы"
    },
    {
        "title": "Циклы",
        "order": 6,
        "hours": 12,
        "description": "for, while, break, continue"
    },
    {
        "title": "Списки и кортежи",
        "order": 7,
        "hours": 12,
        "description": "Создание, индексация, методы списков"
    },
    {
        "title": "Словари и множества",
        "order": 8,
        "hours": 12,
        "description": "Работа со словарями, множества, операции"
    },
    {
        "title": "Функции",
        "order": 9,
        "hours": 12,
        "description": "Определение функций, параметры, возврат значений"
    },
    {
        "title": "Модули и импорт",
        "order": 10,
        "hours": 12,
        "description": "Импорт модулей, создание своих модулей"
    },
    {
        "title": "Работа с файлами",
        "order": 11,
        "hours": 12,
        "description": "Чтение и запись файлов, обработка исключений"
    },
    {
        "title": "Основы ООП",
        "order": 12,
        "hours": 12,
        "description": "Классы, объекты, методы, наследование"
    }
]


async def generate_full_course():
    """Generate all 12 lectures"""
    
    print("=" * 80)
    print("ГЕНЕРАЦИЯ ПОЛНОГО КУРСА ПО PYTHON")
    print("12 лекций для начинающих")
    print("=" * 80)
    
    # RPD Data
    rpd_data = {
        "subject_title": "Основы программирования на Python",
        "academic_degree": "bachelor",
        "profession": "Прикладная информатика",
        "total_hours": 144,
        "department": "Кафедра информационных технологий",
        "faculty": "Институт вычислительной математики и информационных технологий",
        "lecture_themes": PYTHON_COURSE_THEMES
    }
    
    fingerprint = generate_request_fingerprint(rpd_data)
    print(f"\n📋 Курс: {rpd_data['subject_title']}")
    print(f"   Уровень: {rpd_data['academic_degree']}")
    print(f"   Часов: {rpd_data['total_hours']}")
    print(f"   Лекций: {len(PYTHON_COURSE_THEMES)}")
    print(f"   Fingerprint: {fingerprint}")
    
    # Process book
    print(f"\n📚 Обработка книги...")
    pdf_path = Path("питон_мок_дата.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Книга не найдена: {pdf_path}")
        return
    
    pdf_processor = get_pdf_processor()
    book_id = "python_byte_001"
    
    processing_result = pdf_processor.process_book(pdf_path, book_id)
    
    if not processing_result['success']:
        print(f"❌ Ошибка обработки PDF")
        return
    
    print(f"✓ Книга обработана: {processing_result['total_pages']} страниц, {processing_result['chunks_count']} чанков")
    
    # Initialize services
    print(f"\n🔧 Инициализация сервисов...")
    
    model_manager = ModelManager(use_mock_services=False)
    await model_manager.initialize()
    print(f"✓ ModelManager инициализирован")
    
    embedding_service = await get_embedding_service(
        model_manager=model_manager,
        use_mock=False
    )
    print(f"✓ Embedding service инициализирован")
    
    # Add chunks to vector store
    print(f"\n🔢 Генерация эмбеддингов...")
    book_metadata = {
        'title': 'A Byte of Python (Russian)',
        'authors': 'Swaroop C H',
        'year': 2013
    }
    
    embedding_result = embedding_service.add_chunks_to_vector_store(
        processing_result['chunks'],
        book_metadata
    )
    
    if embedding_result['success']:
        print(f"✓ {embedding_result['chunks_added']} чанков добавлено в векторное хранилище")
    
    # Initialize content generator
    generator = await get_content_generator(
        model_manager=model_manager,
        embedding_service=embedding_service,
        pdf_processor=pdf_processor,
        use_mock=False  # REAL LLM!
    )
    print(f"✓ Content generator инициализирован")
    
    # Create output directory
    output_dir = Path("generated_lectures")
    output_dir.mkdir(exist_ok=True)
    
    # Generate all lectures
    print(f"\n" + "=" * 80)
    print(f"ГЕНЕРАЦИЯ ЛЕКЦИЙ")
    print(f"=" * 80)
    
    all_results = []
    total_time = 0
    
    for i, theme in enumerate(PYTHON_COURSE_THEMES, 1):
        print(f"\n📝 Лекция {i}/12: {theme['title']}")
        print(f"   {theme['description']}")
        print(f"   Генерация...")
        
        try:
            result = await generator.generate_lecture(
                theme=theme['title'],
                rpd_data=rpd_data,
                book_ids=[book_id]
            )
            
            if result.success:
                print(f"   ✓ Сгенерировано за {result.generation_time_seconds:.1f}с")
                print(f"     Уверенность: {result.confidence_score:.1%}")
                print(f"     Источников: {len(result.sources_used)}")
                print(f"     Цитат: {len(result.citations)}")
                
                # Save to file
                filename = f"lecture_{i:02d}_{theme['title'].replace(' ', '_')}.md"
                filepath = output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.content)
                
                print(f"     💾 Сохранено: {filename}")
                
                all_results.append({
                    'lecture_number': i,
                    'theme': theme['title'],
                    'success': True,
                    'time': result.generation_time_seconds,
                    'confidence': result.confidence_score,
                    'file': str(filepath)
                })
                
                total_time += result.generation_time_seconds
                
            else:
                print(f"   ❌ Ошибка генерации")
                for error in result.errors:
                    print(f"      - {error}")
                
                all_results.append({
                    'lecture_number': i,
                    'theme': theme['title'],
                    'success': False,
                    'errors': result.errors
                })
        
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
            all_results.append({
                'lecture_number': i,
                'theme': theme['title'],
                'success': False,
                'errors': [str(e)]
            })
    
    # Summary
    print(f"\n" + "=" * 80)
    print(f"📊 ИТОГИ ГЕНЕРАЦИИ")
    print(f"=" * 80)
    
    successful = sum(1 for r in all_results if r['success'])
    failed = len(all_results) - successful
    
    print(f"\n✓ Успешно: {successful}/12")
    print(f"❌ Ошибок: {failed}/12")
    print(f"⏱️  Общее время: {total_time:.1f}с ({total_time/60:.1f} мин)")
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"⏱️  Среднее время: {avg_time:.1f}с на лекцию")
    
    print(f"\n📁 Лекции сохранены в: {output_dir.absolute()}")
    
    # Save summary
    summary_file = output_dir / "generation_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'course': rpd_data['subject_title'],
            'fingerprint': fingerprint,
            'total_lectures': len(PYTHON_COURSE_THEMES),
            'successful': successful,
            'failed': failed,
            'total_time_seconds': total_time,
            'average_time_seconds': total_time / successful if successful > 0 else 0,
            'generated_at': datetime.now().isoformat(),
            'results': all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Сводка сохранена: {summary_file}")
    
    # Cleanup
    await model_manager.cleanup()
    
    print(f"\n" + "=" * 80)
    print(f"🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
    print(f"=" * 80)


if __name__ == "__main__":
    asyncio.run(generate_full_course())
