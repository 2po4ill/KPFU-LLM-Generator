"""
Test PDF processing with the mock Python book
Run with: python test_pdf_processing.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Import directly from processor module to avoid chromadb import issues
from literature.processor import PDFProcessor

def test_pdf_extraction():
    """Test PDF text extraction"""
    
    pdf_path = Path("питон_мок_дата.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print("=" * 60)
    print("Testing PDF Processing")
    print("=" * 60)
    
    processor = PDFProcessor()
    
    # Test full processing
    print(f"\n📖 Processing: {pdf_path.name}")
    result = processor.process_book(pdf_path, "test_book_001")
    
    if result['success']:
        print(f"\n✅ Processing successful!")
        print(f"   Total pages: {result['total_pages']}")
        print(f"   Total characters: {result['total_chars']:,}")
        print(f"   Chunks created: {result['chunks_count']}")
        print(f"   TOC entries found: {len(result['toc_entries'])}")
        
        # Show TOC
        if result['toc_entries']:
            print(f"\n📑 Table of Contents:")
            for entry in result['toc_entries'][:10]:  # Show first 10
                indent = "  " * (entry.level - 1)
                print(f"   {indent}{entry.title} ... стр. {entry.page_number}")
            
            if len(result['toc_entries']) > 10:
                print(f"   ... and {len(result['toc_entries']) - 10} more entries")
        
        # Show keywords
        if result['keywords']:
            print(f"\n🔑 Top Keywords:")
            for word, freq in result['keywords'][:15]:
                print(f"   {word}: {freq}")
        
        # Show sample chunks
        print(f"\n📄 Sample Chunks:")
        for i, chunk in enumerate(result['chunks'][:3]):
            print(f"\n   Chunk {i+1} (Page {chunk.page_number}):")
            preview = chunk.content[:200].replace('\n', ' ')
            print(f"   {preview}...")
            print(f"   ({chunk.char_count} characters)")
        
        if result['chunks_count'] > 3:
            print(f"\n   ... and {result['chunks_count'] - 3} more chunks")
        
    else:
        print(f"\n❌ Processing failed: {result.get('error')}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_pdf_extraction()
