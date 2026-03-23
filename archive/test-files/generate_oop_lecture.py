"""
Generate OOP lecture with correct theme
"""
import asyncio
import sys
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def generate_oop():
    print("="*80)
    print("GENERATING OOP LECTURE")
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
    
    rpd_data = {
        'subject': 'Программирование на Python',
        'degree': 'Бакалавриат',
        'profession': 'Информатика'
    }
    
    # Try different theme variations
    themes_to_try = [
        "Объектно-ориентированное программирование",
        "Классы и объекты",
        "ООП в Python",
        "Классы, объекты и методы"
    ]
    
    for i, theme in enumerate(themes_to_try, 1):
        print(f"\n{'='*80}")
        print(f"Attempt {i}/{len(themes_to_try)}: {theme}")
        print(f"{'='*80}")
        
        try:
            result = await generator.generate_lecture(
                theme=theme,
                rpd_data=rpd_data,
                book_ids=['python_book']
            )
            
            if result.success:
                # Save lecture
                filename = f"lecture_12_Основы_ООП.md"
                
                with open(f"generated_lectures_with_offset/{filename}", 'w', encoding='utf-8') as f:
                    f.write(result.content)
                
                word_count = len(result.content.split())
                
                print(f"\n✓ SUCCESS!")
                print(f"  Theme: {theme}")
                print(f"  Time: {result.generation_time_seconds:.1f}s")
                print(f"  Confidence: {result.confidence_score:.0%}")
                print(f"  Words: {word_count}")
                print(f"  File: {filename}")
                
                return True
            else:
                print(f"\n✗ Failed with theme: {theme}")
                for error in result.errors:
                    print(f"  Error: {error}")
                print(f"  Trying next theme...")
        
        except Exception as e:
            print(f"\n✗ Exception: {e}")
            print(f"  Trying next theme...")
    
    print(f"\n{'='*80}")
    print("All attempts failed")
    print("="*80)
    return False

if __name__ == "__main__":
    success = asyncio.run(generate_oop())
    sys.exit(0 if success else 1)
