"""
Quick test of enhanced parsing capabilities
"""
from app.literature.processor import PDFProcessor
import sys

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

def quick_test():
    print("QUICK PARSING TEST")
    print("="*50)
    
    books = [
        ('питон_мок_дата.pdf', 'A Byte of Python'),
        ('Изучаем_Питон.pdf', 'Изучаем Python'),
        ('ООП_на_питоне.pdf', 'ООП на Python')
    ]
    
    pdf_processor = PDFProcessor()
    
    for book_path, book_name in books:
        print(f"\n{book_name}:")
        print("-" * 30)
        
        try:
            # Extract
            data = pdf_processor.extract_text_from_pdf(book_path)
            if not data['success']:
                print(f"❌ Extraction failed")
                continue
            
            # Offset
            offset = pdf_processor.detect_page_offset(data['pages'])
            print(f"Offset: {offset}")
            
            # TOC pages
            toc_pages = pdf_processor.find_toc_pages(data['pages'])
            print(f"TOC pages: {toc_pages}")
            
            if toc_pages:
                # Parse TOC
                toc_text = '\n\n'.join([
                    p['text'] for p in data['pages'] 
                    if p['page_number'] in toc_pages
                ])
                
                entries = pdf_processor.parse_table_of_contents(toc_text)
                print(f"TOC entries: {len(entries)}")
                
                if entries:
                    print("Sample entries:")
                    for entry in entries[:3]:
                        print(f"  {entry.title[:40]:40s} → {entry.page_number}")
                    print("✅ Parsing works!")
                else:
                    print("⚠️ No entries parsed")
            else:
                print("❌ No TOC found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_test()