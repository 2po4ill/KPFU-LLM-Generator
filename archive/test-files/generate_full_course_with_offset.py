"""
Generate full course with offset fix and track accuracy
"""
import asyncio
import sys
import time
import json
from pathlib import Path
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Course themes
THEMES = [
    "Введение в Python",
    "Основы синтаксиса и переменные",
    "Работа со строками",
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
    print("="*80)
    print("FULL COURSE GENERATION WITH OFFSET FIX")
    print("="*80)
    print(f"Generating {len(THEMES)} lectures...")
    print()
    
    # Initialize components
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(
        model_manager=model_manager,
        pdf_processor=pdf_processor
    )
    
    rpd_data = {
        'subject': 'Программирование на Python',
        'degree': 'Бакалавриат',
        'profession': 'Информатика'
    }
    
    # Create output directory
    output_dir = Path('generated_lectures_with_offset')
    output_dir.mkdir(exist_ok=True)
    
    results = []
    total_start = time.time()
    
    for i, theme in enumerate(THEMES, 1):
        print(f"\n{'='*80}")
        print(f"Lecture {i}/12: {theme}")
        print(f"{'='*80}")
        
        lecture_start = time.time()
        
        try:
            result = await generator.generate_lecture(
                theme=theme,
                rpd_data=rpd_data,
                book_ids=['python_book']
            )
            
            lecture_time = time.time() - lecture_start
            
            if result.success:
                # Save lecture
                filename = f"lecture_{i:02d}_{theme.replace(' ', '_')}.md"
                filepath = output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.content)
                
                word_count = len(result.content.split())
                
                print(f"\n✓ SUCCESS")
                print(f"  Time: {lecture_time:.1f}s")
                print(f"  Confidence: {result.confidence_score:.0%}")
                print(f"  Words: {word_count}")
                print(f"  File: {filename}")
                
                results.append({
                    'number': i,
                    'theme': theme,
                    'success': True,
                    'time': lecture_time,
                    'confidence': result.confidence_score,
                    'words': word_count,
                    'chars': len(result.content),
                    'step_times': result.step_times,
                    'warnings': result.warnings,
                    'sources': len(result.sources_used)
                })
            else:
                print(f"\n✗ FAILED")
                for error in result.errors:
                    print(f"  Error: {error}")
                
                results.append({
                    'number': i,
                    'theme': theme,
                    'success': False,
                    'time': lecture_time,
                    'errors': result.errors
                })
        
        except Exception as e:
            lecture_time = time.time() - lecture_start
            print(f"\n✗ EXCEPTION: {e}")
            
            results.append({
                'number': i,
                'theme': theme,
                'success': False,
                'time': lecture_time,
                'errors': [str(e)]
            })
    
    total_time = time.time() - total_start
    
    # Save summary
    summary = {
        'total_lectures': len(THEMES),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'total_time': total_time,
        'results': results
    }
    
    with open(output_dir / 'generation_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print("\n" + "="*80)
    print("GENERATION COMPLETE")
    print("="*80)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\nSuccessful: {len(successful)}/{len(THEMES)}")
    print(f"Failed: {len(failed)}/{len(THEMES)}")
    print(f"Total time: {total_time/60:.1f} minutes")
    
    if successful:
        avg_time = sum(r['time'] for r in successful) / len(successful)
        avg_words = sum(r['words'] for r in successful) / len(successful)
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        
        print(f"\nAverages (successful lectures):")
        print(f"  Time: {avg_time:.1f}s")
        print(f"  Words: {avg_words:.0f}")
        print(f"  Confidence: {avg_confidence:.0%}")
    
    if failed:
        print(f"\nFailed lectures:")
        for r in failed:
            print(f"  {r['number']}. {r['theme']}")
            if 'errors' in r:
                for error in r['errors']:
                    print(f"     Error: {error}")
    
    print(f"\n✓ Results saved to: {output_dir}/")
    print(f"✓ Summary saved to: {output_dir}/generation_summary.json")

if __name__ == "__main__":
    asyncio.run(generate_full_course())
