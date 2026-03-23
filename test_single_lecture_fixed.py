"""
Single lecture test with batched queued generation
"""
import asyncio
import time
import psutil
from pathlib import Path

from app.core.model_manager import ModelManager
from app.literature.processor import get_pdf_processor
from app.generation.generator_v3 import get_optimized_content_generator


def get_gpu_usage():
    """Get GPU usage if available"""
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            gpu_util, mem_used = result.stdout.strip().split(',')
            return float(gpu_util.strip()), float(mem_used.strip())
    except:
        pass
    return None, None


async def test_single_lecture():
    """Test single lecture generation with batched queued processing"""
    
    print("=" * 80)
    print("BATCHED QUEUED GENERATION TEST")
    print("=" * 80)
    
    theme = "Работа со строками"
    book_path = "Изучаем_Питон.pdf"
    book_id = "izuchaem_python"
    
    print(f"\nTheme: {theme}")
    print(f"Book: {book_path}")
    print(f"Architecture: Batched (5 pages) + Queued (2 parallel)")
    
    # Initialize components
    print("\nInitializing components...")
    start_init = time.time()
    
    model_manager = ModelManager()
    await model_manager.initialize()
    pdf_processor = get_pdf_processor()
    generator = await get_optimized_content_generator()
    
    await generator.initialize(model_manager, pdf_processor)
    
    init_time = time.time() - start_init
    print(f"Components initialized ({init_time:.1f}s)")
    
    # Initialize book (TOC caching)
    print(f"\nInitializing book: {book_id}")
    start_book = time.time()
    
    book_result = await generator.initialize_book(book_path, book_id)
    
    book_time = time.time() - start_book
    
    if book_result['success']:
        print(f"Book initialized ({book_time:.1f}s)")
    else:
        print(f"Book initialization failed: {book_result.get('error', 'Unknown error')}")
        return
    
    # Generate lecture with GPU monitoring
    print(f"\nGenerating lecture: {theme}")
    print("=" * 80)
    
    # Monitor GPU before
    gpu_before, mem_before = get_gpu_usage()
    if gpu_before is not None:
        print(f"GPU before: {gpu_before}% utilization, {mem_before}MB memory")
    
    start_gen = time.time()
    
    result = await generator.generate_lecture_optimized(
        theme=theme,
        book_ids=[book_id],
        rpd_data={}
    )
    
    gen_time = time.time() - start_gen
    
    # Monitor GPU after
    gpu_after, mem_after = get_gpu_usage()
    if gpu_after is not None:
        print(f"GPU after: {gpu_after}% utilization, {mem_after}MB memory")
        print(f"GPU delta: {gpu_after - gpu_before:.1f}%")
    
    print("=" * 80)
    print(f"\nGENERATION RESULTS")
    print("=" * 80)
    
    if result.success:
        print(f"SUCCESS")
        print(f"\nTIMING:")
        print(f"  Total Time: {gen_time:.1f}s")
        if hasattr(result, 'step_times'):
            for step_name, step_time in result.step_times.items():
                print(f"  {step_name}: {step_time:.1f}s")
        
        print(f"\nCONTENT:")
        print(f"  Length: {len(result.content):,} characters")
        print(f"  Words: {len(result.content.split()):,} words")
        if hasattr(result, 'validation_confidence'):
            print(f"  Validation: {result.validation_confidence:.1f}%")
        
        # Save lecture to file
        output_filename = f"lecture_{theme.replace(' ', '_')}_batched.md"
        output_path = Path(output_filename)
        
        validation_str = f"{result.validation_confidence:.1f}%" if hasattr(result, 'validation_confidence') else "N/A"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Лекция: {theme}\n\n")
            f.write(f"**Книга**: {book_path}\n")
            f.write(f"**Архитектура**: Batched + Queued\n")
            f.write(f"**Время генерации**: {gen_time:.1f}s\n")
            f.write(f"**Количество слов**: {len(result.content.split()):,}\n")
            f.write(f"**Валидация**: {validation_str}\n\n")
            f.write("---\n\n")
            f.write(result.content)
        
        print(f"\nLecture saved to: {output_filename}")
        
        # Show first 500 chars of content
        print(f"\nCONTENT PREVIEW:")
        print("-" * 80)
        print(result.content[:500])
        print("...")
        print("-" * 80)
        
    else:
        print(f"FAILED: {result.error}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_single_lecture())
