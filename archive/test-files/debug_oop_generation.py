"""
Debug OOP lecture generation - step by step with detailed logging
"""
import asyncio
import sys
import time
from app.generation.generator_v2 import ContentGenerator
from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

async def debug_step_by_step():
    """Debug each step of OOP generation"""
    print("DEBUG: OOP LECTURE GENERATION")
    print("="*60)
    
    try:
        # Step 1: Initialize components
        print("Step 1: Initializing components...")
        model_manager = ModelManager()
        await model_manager.initialize()
        print("✓ ModelManager initialized")
        
        pdf_processor = PDFProcessor()
        print("✓ PDFProcessor initialized")
        
        generator = ContentGenerator(use_mock=False)
        await generator.initialize(
            model_manager=model_manager,
            pdf_processor=pdf_processor
        )
        print("✓ ContentGenerator initialized")
        
        # Step 2: Load and process book
        print("\nStep 2: Loading OOP book...")
        book_path = 'ООП_на_питоне.pdf'
        
        pages_data = pdf_processor.extract_text_from_pdf(book_path)
        if not pages_data['success']:
            print(f"❌ Failed to extract pages from {book_path}")
            return False
        
        print(f"✓ Extracted {pages_data['total_pages']} pages")
        
        # Step 3: Detect offset
        print("\nStep 3: Detecting page offset...")
        page_offset = pdf_processor.detect_page_offset(pages_data['pages'])
        print(f"✓ Page offset: {page_offset}")
        
        # Step 4: Find TOC
        print("\nStep 4: Finding TOC...")
        toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
        if not toc_page_numbers:
            print("❌ No TOC found")
            return False
        
        print(f"✓ TOC pages: {toc_page_numbers}")
        
        # Step 5: Extract TOC text
        print("\nStep 5: Extracting TOC text...")
        toc_text = '\n\n'.join([
            p['text'] for p in pages_data['pages'] 
            if p['page_number'] in toc_page_numbers
        ])
        
        if len(toc_text) > 10000:
            toc_text = toc_text[:10000]
        
        print(f"✓ TOC text: {len(toc_text)} chars")
        
        # Save TOC for inspection
        with open('debug_toc_oop.txt', 'w', encoding='utf-8') as f:
            f.write(toc_text)
        print("✓ TOC saved to debug_toc_oop.txt")
        
        # Step 6: Test LLM page selection
        print("\nStep 6: Testing LLM page selection...")
        print("This is where it might hang - testing with timeout...")
        
        theme = "Основы ООП"
        
        # Test with timeout
        try:
            book_page_numbers = await asyncio.wait_for(
                generator._get_page_numbers_from_toc(theme, toc_text),
                timeout=120.0  # 2 minute timeout
            )
            
            print(f"✓ LLM returned: {book_page_numbers}")
            
            if not book_page_numbers or book_page_numbers == [0]:
                print("❌ Book not relevant for theme")
                return False
            
        except asyncio.TimeoutError:
            print("❌ LLM call timed out after 2 minutes")
            print("This suggests Ollama is hanging or very slow")
            return False
        
        # Step 7: Convert to PDF pages
        print("\nStep 7: Converting to PDF pages...")
        pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
        print(f"✓ PDF pages: {pdf_page_numbers}")
        
        # Step 8: Load page content
        print("\nStep 8: Loading page content...")
        selected_pages = []
        
        for page_num in pdf_page_numbers:
            page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
            
            if page_data:
                selected_pages.append({
                    'book_id': 'oop_book',
                    'book_title': 'ООП на Python',
                    'page_number': page_num,
                    'content': page_data['text'],
                    'relevance_score': 1.0
                })
        
        print(f"✓ Selected {len(selected_pages)} pages")
        
        # Step 9: Test outline generation
        print("\nStep 9: Testing outline generation...")
        
        # Prepare context (limit to first 5 pages for testing)
        test_pages = selected_pages[:5]
        context = "\n\n---PAGE BREAK---\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in test_pages
        ])
        
        print(f"Context length: {len(context)} chars")
        
        try:
            outline = await asyncio.wait_for(
                generator._generate_outline(theme, context),
                timeout=60.0  # 1 minute timeout
            )
            
            print(f"✓ Outline generated: {len(outline)} sections")
            for i, section in enumerate(outline, 1):
                print(f"  {i}. {section['title']} ({section['words']} words)")
            
        except asyncio.TimeoutError:
            print("❌ Outline generation timed out")
            return False
        
        # Step 10: Test single section generation
        print("\nStep 10: Testing single section generation...")
        
        if outline:
            first_section = outline[0]
            print(f"Testing section: {first_section['title']}")
            
            try:
                section_content = await asyncio.wait_for(
                    generator._generate_section(theme, first_section, context, 1, len(outline)),
                    timeout=120.0  # 2 minute timeout
                )
                
                word_count = len(section_content.split())
                print(f"✓ Section generated: {word_count} words")
                
                # Save section for inspection
                with open('debug_section_oop.md', 'w', encoding='utf-8') as f:
                    f.write(f"# {first_section['title']}\n\n")
                    f.write(section_content)
                
                print("✓ Section saved to debug_section_oop.md")
                
            except asyncio.TimeoutError:
                print("❌ Section generation timed out")
                return False
        
        print(f"\n✅ ALL STEPS COMPLETED SUCCESSFULLY!")
        print("The system is working - the original hang was likely due to:")
        print("1. Very long LLM generation time")
        print("2. Network issues with Ollama")
        print("3. GPU memory issues")
        
        return True
        
    except Exception as e:
        print(f"\n❌ EXCEPTION in step-by-step debug: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ollama_connection():
    """Test basic Ollama connection"""
    print("\nTesting Ollama connection...")
    
    try:
        model_manager = ModelManager()
        await model_manager.initialize()
        
        llm_model = await model_manager.get_llm_model()
        
        # Simple test
        response = await asyncio.wait_for(
            llm_model.generate(
                model="llama3.1:8b",
                prompt="Привет! Ответь одним словом: работает?",
                options={"temperature": 0.1, "num_predict": 10}
            ),
            timeout=30.0
        )
        
        result = response.get('response', '').strip()
        print(f"✓ Ollama response: '{result}'")
        return True
        
    except asyncio.TimeoutError:
        print("❌ Ollama connection timed out")
        return False
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return False

if __name__ == "__main__":
    print("Starting debug session...")
    
    # First test Ollama
    ollama_ok = asyncio.run(test_ollama_connection())
    
    if ollama_ok:
        print("\nOllama is working, proceeding with full debug...")
        success = asyncio.run(debug_step_by_step())
        print(f"\nFinal Result: {'SUCCESS' if success else 'FAILED'}")
    else:
        print("\n❌ Ollama connection failed - fix this first")