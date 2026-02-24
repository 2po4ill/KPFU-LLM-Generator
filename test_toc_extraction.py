"""
Test TOC extraction with LLM
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.literature.processor import PDFProcessor
from app.core.model_manager import ModelManager

async def test_toc_extraction():
    """Test TOC extraction with LLM"""
    
    # Initialize
    pdf_path = Path('питон_мок_дата.pdf')
    processor = PDFProcessor()
    model_manager = ModelManager()
    
    print("=" * 80)
    print("TESTING TOC EXTRACTION WITH LLM")
    print("=" * 80)
    
    # Extract text
    print("\n1. Extracting text from PDF...")
    result = processor.extract_text_from_pdf(pdf_path)
    
    if not result['success']:
        print(f"ERROR: {result['error']}")
        return
    
    print(f"   ✓ Extracted {result['total_pages']} pages")
    
    # Find TOC pages
    print("\n2. Finding TOC pages...")
    toc_pages = processor.find_toc_pages(result['pages'])
    print(f"   ✓ Found TOC on pages: {toc_pages}")
    
    # Show TOC text sample
    print("\n3. TOC text sample (first 500 chars):")
    toc_text = '\n\n'.join([
        p['text'] for p in result['pages'] 
        if p['page_number'] in toc_pages
    ])
    print("-" * 80)
    print(toc_text[:500])
    print("-" * 80)
    
    # Extract TOC with LLM
    print("\n4. Extracting TOC with LLM...")
    toc_entries = await processor.extract_toc_with_llm(
        result['pages'],
        model_manager
    )
    
    print(f"\n   ✓ Extracted {len(toc_entries)} TOC entries")
    
    # Show first 10 entries
    print("\n5. First 10 TOC entries:")
    for i, entry in enumerate(toc_entries[:10], 1):
        print(f"   {i}. [{entry.level}] {entry.title} → page {entry.page_number}")
    
    # Check if we got the OOP entry
    print("\n6. Looking for OOP-related entries...")
    oop_entries = [e for e in toc_entries if 'ооп' in e.title.lower() or 'класс' in e.title.lower() or 'объект' in e.title.lower()]
    
    if oop_entries:
        print(f"   ✓ Found {len(oop_entries)} OOP-related entries:")
        for entry in oop_entries:
            print(f"      - {entry.title} → page {entry.page_number}")
    else:
        print("   ✗ No OOP entries found!")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    asyncio.run(test_toc_extraction())
