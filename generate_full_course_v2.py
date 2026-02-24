"""
Generate complete 12-lecture Python course using generator_v2
Uses Gemma 3 27B for TOC selection + Llama 3.1 8B for content generation

Run with: python generate_full_course_v2.py
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


# 12-lecture curriculum
PYTHON_COURSE_THEMES = [
    "Введение в Python",
    "Основы синтаксиса и переменные",
    "Строки и форматирование",
    "Числа и математические операции",
    "Условные операторы",
    "Циклы",
    "Списки и кортежи",
    "Словари и множества",
    "Функции",
    "Модули и импорт",
    "Работа с файлами",
    "Основы ООП"
]


async def generate_full_course():
    """Generate all 12 lectures"""
    
    print("=" * 80)
    print("ГЕНЕРАЦИЯ ПОЛНОГО КУРСА ПО PYTHON (V2)")
    print("12 лекций для начинающих")
    print("=" * 80)
    
    # RPD Data
    rpd_data = {
        "subject_title": "Основы программирования на Python",
        "academic_degree": "bachelor",
        "profession": "Прикладная информатика",
        "total_hours": 144,
        "department": "Кафедра информационных технологий",
        "faculty": "Институт вычислительной математики и информационных технологий"
    }
    
    print(f"\n📋 Курс: {rpd_data['subject_title']}")
    print(f"   Уровень: {rpd_data['academic_degree']}")
    print(f"   Часов: {rpd_data['total_hours']}")
    print(f"   Лекций: {len(PYTHON_COURSE_THEMES)}")
    
    # Initialize services
    print(f"\n🔧 Инициализация сервисов...")
    
    model_manager = ModelManager()
    await model_manager.initialize()
    print(f"✓ ModelManager инициализирован")
    
    pdf_processor = PDFProcessor()
    print(f"✓ PDFProcessor инициализирован")
    
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager=model_manager, pdf_processor=pdf_processor)
    print(f"✓ ContentGenerator V2 инициализирован")
    
    # Create output directory
    output_dir = Path("generated_lectures_v2")
    output_dir.mkdir(exist_ok=True)
    
    # Generate all lectures
    print(f"\n" + "=" * 80)
    print(f"ГЕНЕРАЦИЯ ЛЕКЦИЙ")
    print(f"=" * 80)
    print(f"\nМодели:")
    print(f"  - TOC selection: Gemma 3 27B (free, local)")
    print(f"  - Content generation: Llama 3.1 8B (free, local)")
    print(f"\nОжидаемое время: ~60-90 секунд на лекцию")
    print(f"Общее время: ~12-18 минут для всего курса")
    
    all_results = []
    total_time = 0
    book_ids = ['python_byte_ru']
    
    for i, theme in enumerate(PYTHON_COURSE_THEMES, 1):
        print(f"\n{'='*80}")
        print(f"📝 Лекция {i}/12: {theme}")
        print(f"{'='*80}")
        
        try:
            result = await generator.generate_lecture(
                theme=theme,
                rpd_data=rpd_data,
                book_ids=book_ids
            )
            
            if result.success:
                print(f"\n✓ Сгенерировано за {result.generation_time_seconds:.1f}с")
                print(f"  Уверенность: {result.confidence_score:.1%}")
                print(f"  Источников: {len(result.sources_used)}")
                
                # Step times
                print(f"\n  Время по этапам:")
                for step, time_taken in result.step_times.items():
                    print(f"    - {step}: {time_taken:.1f}с")
                
                # Save to file
                filename = f"lecture_{i:02d}_{theme.replace(' ', '_')}.md"
                filepath = output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.content)
                
                print(f"\n  💾 Сохранено: {filename}")
                print(f"     Размер: {len(result.content)} символов")
                print(f"     Слов: ~{len(result.content.split())} слов")
                
                all_results.append({
                    'lecture_number': i,
                    'theme': theme,
                    'success': True,
                    'time': result.generation_time_seconds,
                    'confidence': result.confidence_score,
                    'step_times': result.step_times,
                    'file': str(filepath),
                    'warnings': result.warnings
                })
                
                total_time += result.generation_time_seconds
                
                if result.warnings:
                    print(f"\n  ⚠️  Предупреждения:")
                    for warning in result.warnings:
                        print(f"     - {warning}")
                
            else:
                print(f"\n❌ Ошибка генерации")
                for error in result.errors:
                    print(f"   - {error}")
                
                all_results.append({
                    'lecture_number': i,
                    'theme': theme,
                    'success': False,
                    'errors': result.errors
                })
        
        except Exception as e:
            print(f"\n❌ Исключение: {e}")
            import traceback
            traceback.print_exc()
            
            all_results.append({
                'lecture_number': i,
                'theme': theme,
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
        
        # Average step times
        avg_steps = {}
        for result in all_results:
            if result['success'] and 'step_times' in result:
                for step, time_val in result['step_times'].items():
                    if step not in avg_steps:
                        avg_steps[step] = []
                    avg_steps[step].append(time_val)
        
        if avg_steps:
            print(f"\n  Среднее время по этапам:")
            for step, times in avg_steps.items():
                avg = sum(times) / len(times)
                print(f"    - {step}: {avg:.1f}с")
    
    print(f"\n📁 Лекции сохранены в: {output_dir.absolute()}")
    
    # Save summary
    summary_file = output_dir / "generation_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'course': rpd_data['subject_title'],
            'version': 'v2',
            'models': {
                'toc_selection': 'gemma3:27b',
                'content_generation': 'llama3.1:8b'
            },
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
