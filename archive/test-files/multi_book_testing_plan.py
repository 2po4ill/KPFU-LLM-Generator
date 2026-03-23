"""
Multi-book testing implementation plan
"""
import asyncio
import sys
from pathlib import Path
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Book configuration
BOOKS = {
    'byte_of_python': {
        'path': 'питон_мок_дата.pdf',
        'title': 'A Byte of Python (Russian)',
        'level': 'beginner',
        'strengths': ['basics', 'syntax', 'introduction'],
        'themes': [1, 2, 3, 4, 5, 6]  # Best for these themes
    },
    # Future books to add:
    'lutz_learning_python': {
        'path': 'изучаем_python_лутц.pdf',  # When available
        'title': 'Изучаем Python (Mark Lutz)',
        'level': 'intermediate',
        'strengths': ['data_structures', 'functions', 'modules'],
        'themes': [7, 8, 9, 10, 11]
    },
    'oop_python': {
        'path': 'ооп_на_python.pdf',  # When available
        'title': 'ООП на Python',
        'level': 'advanced',
        'strengths': ['classes', 'objects', 'inheritance'],
        'themes': [12]
    }
}

# Test themes for multi-book comparison
TEST_THEMES = [
    {
        'name': 'Работа со строками',
        'number': 3,
        'expected_books': ['byte_of_python', 'lutz_learning_python'],
        'complexity': 'intermediate'
    },
    {
        'name': 'Функции',
        'number': 9,
        'expected_books': ['byte_of_python', 'lutz_learning_python'],
        'complexity': 'advanced'
    },
    {
        'name': 'Основы ООП',
        'number': 12,
        'expected_books': ['byte_of_python', 'oop_python'],
        'complexity': 'advanced'
    }
]

async def test_book_compatibility(book_config):
    """Test if a book is compatible with our system"""
    print(f"\n{'='*80}")
    print(f"Testing Book Compatibility: {book_config['title']}")
    print(f"{'='*80}")
    
    book_path = book_config['path']
    
    if not Path(book_path).exists():
        print(f"❌ Book not found: {book_path}")
        return False
    
    try:
        # Test PDF extraction
        pdf_processor = PDFProcessor()
        data = pdf_processor.extract_text_from_pdf(book_path)
        
        if not data['success']:
            print(f"❌ PDF extraction failed: {data.get('error', 'Unknown error')}")
            return False
        
        print(f"✓ PDF extraction successful")
        print(f"  Pages: {data['total_pages']}")
        print(f"  Characters: {data['total_chars']:,}")
        
        # Test offset detection
        offset = pdf_processor.detect_page_offset(data['pages'])
        print(f"✓ Offset detection: {offset}")
        
        # Test TOC detection
        toc_pages = pdf_processor.find_toc_pages(data['pages'])
        print(f"✓ TOC pages found: {toc_pages}")
        
        if not toc_pages:
            print(f"⚠️ Warning: No TOC pages detected")
            return False
        
        # Test TOC content
        toc_text = '\n\n'.join([
            p['text'] for p in data['pages'] 
            if p['page_number'] in toc_pages
        ])
        
        print(f"✓ TOC text extracted: {len(toc_text)} chars")
        
        # Show sample TOC content
        print(f"\nSample TOC content:")
        print("-" * 40)
        print(toc_text[:500] + "..." if len(toc_text) > 500 else toc_text)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing book: {e}")
        return False

async def compare_books_for_theme(theme_config, available_books):
    """Compare multiple books for the same theme"""
    print(f"\n{'='*80}")
    print(f"Multi-Book Comparison: {theme_config['name']}")
    print(f"{'='*80}")
    
    theme = theme_config['name']
    results = {}
    
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
    
    for book_id in theme_config['expected_books']:
        if book_id not in available_books:
            print(f"⚠️ Book not available: {book_id}")
            continue
        
        book_config = BOOKS[book_id]
        print(f"\n{'-'*60}")
        print(f"Testing with: {book_config['title']}")
        print(f"{'-'*60}")
        
        try:
            # Temporarily modify generator to use specific book
            original_path = generator.pdf_processor
            
            result = await generator.generate_lecture(
                theme=theme,
                rpd_data=rpd_data,
                book_ids=[book_id]
            )
            
            if result.success:
                word_count = len(result.content.split())
                
                results[book_id] = {
                    'success': True,
                    'words': word_count,
                    'confidence': result.confidence_score,
                    'time': result.generation_time_seconds,
                    'content': result.content
                }
                
                print(f"✓ Success: {word_count} words, {result.confidence_score:.0%} confidence")
                
                # Save for comparison
                filename = f"comparison_{theme_config['number']:02d}_{book_id}.md"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# {theme} - {book_config['title']}\n\n")
                    f.write(result.content)
                
                print(f"  Saved: {filename}")
                
            else:
                results[book_id] = {
                    'success': False,
                    'errors': result.errors
                }
                print(f"❌ Failed: {result.errors}")
                
        except Exception as e:
            results[book_id] = {
                'success': False,
                'errors': [str(e)]
            }
            print(f"❌ Exception: {e}")
    
    # Compare results
    print(f"\n{'='*80}")
    print(f"COMPARISON RESULTS: {theme}")
    print(f"{'='*80}")
    
    successful_results = {k: v for k, v in results.items() if v.get('success')}
    
    if len(successful_results) >= 2:
        print(f"\n✓ Successfully compared {len(successful_results)} books:")
        
        for book_id, result in successful_results.items():
            book_title = BOOKS[book_id]['title']
            print(f"\n{book_title}:")
            print(f"  Words: {result['words']}")
            print(f"  Confidence: {result['confidence']:.0%}")
            print(f"  Time: {result['time']:.1f}s")
        
        # Identify best book
        best_book = max(successful_results.items(), 
                       key=lambda x: (x[1]['confidence'], x[1]['words']))
        
        print(f"\n🏆 Best book for '{theme}': {BOOKS[best_book[0]]['title']}")
        print(f"   Reason: {best_book[1]['confidence']:.0%} confidence, {best_book[1]['words']} words")
        
    else:
        print(f"⚠️ Not enough successful results for comparison")
    
    return results

async def test_multi_book_system():
    """Main testing function"""
    print("="*80)
    print("MULTI-BOOK TESTING SYSTEM")
    print("="*80)
    
    # Step 1: Test book compatibility
    print("\nSTEP 1: Testing Book Compatibility")
    print("-" * 40)
    
    available_books = []
    
    for book_id, book_config in BOOKS.items():
        if await test_book_compatibility(book_config):
            available_books.append(book_id)
            print(f"✓ {book_id}: Compatible")
        else:
            print(f"❌ {book_id}: Not compatible or not available")
    
    print(f"\nAvailable books: {len(available_books)}/{len(BOOKS)}")
    
    if len(available_books) < 2:
        print("⚠️ Need at least 2 books for comparison testing")
        print("\nRecommendations:")
        print("1. Add 'Изучаем Python' (Mark Lutz) - Russian PDF")
        print("2. Add 'ООП на Python' - Russian PDF")
        print("3. Ensure PDFs are in correct format with TOC")
        return
    
    # Step 2: Multi-book comparison
    print(f"\nSTEP 2: Multi-Book Theme Comparison")
    print("-" * 40)
    
    comparison_results = {}
    
    for theme_config in TEST_THEMES:
        results = await compare_books_for_theme(theme_config, available_books)
        comparison_results[theme_config['name']] = results
    
    # Step 3: Summary and recommendations
    print(f"\n{'='*80}")
    print("FINAL RECOMMENDATIONS")
    print("="*80)
    
    for theme_name, results in comparison_results.items():
        successful = {k: v for k, v in results.items() if v.get('success')}
        
        if successful:
            best = max(successful.items(), key=lambda x: (x[1]['confidence'], x[1]['words']))
            print(f"\n{theme_name}:")
            print(f"  Best book: {BOOKS[best[0]]['title']}")
            print(f"  Quality: {best[1]['confidence']:.0%} confidence, {best[1]['words']} words")
        else:
            print(f"\n{theme_name}: No successful results")

if __name__ == "__main__":
    print("Multi-Book Testing Plan")
    print("=" * 40)
    print("\nThis script will test multiple books for content generation.")
    print("Currently only 'A Byte of Python' is available.")
    print("\nTo run full testing, add these books:")
    print("1. изучаем_python_лутц.pdf")
    print("2. ооп_на_python.pdf")
    print("\nRunning compatibility test with available books...")
    
    asyncio.run(test_multi_book_system())