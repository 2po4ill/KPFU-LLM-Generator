"""
Test enhanced offset detection and TOC parsing with new books
"""
from app.literature.processor import PDFProcessor
import sys

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def test_enhanced_book_parsing(book_path, book_name):
    """Test enhanced parsing for a specific book"""
    print(f"\n{'='*80}")
    print(f"TESTING ENHANCED PARSING: {book_name}")
    print(f"File: {book_path}")
    print(f"{'='*80}")
    
    try:
        pdf_processor = PDFProcessor()
        
        # Test PDF extraction
        print("1. PDF Extraction...")
        data = pdf_processor.extract_text_from_pdf(book_path)
        
        if not data['success']:
            print(f"❌ Failed: {data.get('error')}")
            return False
        
        print(f"✓ Success: {data['total_pages']} pages, {data['total_chars']:,} chars")
        
        # Test enhanced offset detection
        print("\n2. Enhanced Offset Detection...")
        offset = pdf_processor.detect_page_offset(data['pages'])
        print(f"✓ Detected offset: {offset}")
        
        # Test TOC detection
        print("\n3. TOC Detection...")
        toc_pages = pdf_processor.find_toc_pages(data['pages'])
        print(f"✓ TOC pages: {toc_pages}")
        
        if not toc_pages:
            print("⚠️ No TOC pages found")
            return False
        
        # Test enhanced TOC parsing
        print("\n4. Enhanced TOC Parsing...")
        toc_text = '\n\n'.join([
            p['text'] for p in data['pages'] 
            if p['page_number'] in toc_pages
        ])
        
        print(f"TOC text length: {len(toc_text)} chars")
        
        # Parse TOC
        toc_entries = pdf_processor.parse_table_of_contents(toc_text)
        print(f"✓ Parsed {len(toc_entries)} TOC entries")
        
        if toc_entries:
            print(f"\nSample TOC entries:")
            for i, entry in enumerate(toc_entries[:10]):
                print(f"  {i+1:2d}. [{entry.level}] {entry.title[:50]:50s} → page {entry.page_number}")
            
            if len(toc_entries) > 10:
                print(f"  ... and {len(toc_entries) - 10} more entries")
        else:
            print("⚠️ No TOC entries parsed - showing raw TOC sample:")
            lines = toc_text.split('\n')
            for i, line in enumerate(lines[:20]):
                if line.strip():
                    print(f"  {i+1:2d}: {line.strip()}")
        
        # Test with offset applied
        if toc_entries and offset != 0:
            print(f"\n5. Testing Offset Application...")
            sample_entry = toc_entries[len(toc_entries)//2]  # Middle entry
            book_page = sample_entry.page_number
            pdf_page = book_page + offset
            
            print(f"Sample: '{sample_entry.title[:30]}...'")
            print(f"  TOC says: page {book_page}")
            print(f"  With offset {offset}: PDF page {pdf_page}")
            
            if pdf_page <= data['total_pages']:
                page_data = next((p for p in data['pages'] if p['page_number'] == pdf_page), None)
                if page_data:
                    content_preview = page_data['text'][:200].replace('\n', ' ')
                    print(f"  PDF page {pdf_page} content: {content_preview}...")
                else:
                    print(f"  PDF page {pdf_page} not found")
            else:
                print(f"  PDF page {pdf_page} exceeds book length ({data['total_pages']})")
        
        print(f"\n✅ Book '{book_name}' parsing SUCCESSFUL")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    books = [
        ('питон_мок_дата.pdf', 'A Byte of Python (baseline)'),
        ('Изучаем_Питон.pdf', 'Изучаем Python (new)'),
        ('ООП_на_питоне.pdf', 'ООП на Python (new)')
    ]
    
    print("TESTING ENHANCED PARSING WITH ALL BOOKS")
    print("="*80)
    
    results = {}
    
    for book_path, book_name in books:
        success = test_enhanced_book_parsing(book_path, book_name)
        results[book_name] = success
    
    # Summary
    print(f"\n{'='*80}")
    print("PARSING RESULTS SUMMARY")
    print("="*80)
    
    successful = 0
    for book_name, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{book_name:30s} {status}")
        if success:
            successful += 1
    
    print(f"\nSuccessful: {successful}/{len(books)}")
    
    if successful >= 2:
        print(f"\n🎉 Ready for multi-book lecture generation!")
        print(f"Next step: Run multi-book comparison tests")
    else:
        print(f"\n⚠️ Need to fix parsing issues before multi-book testing")

if __name__ == "__main__":
    main()