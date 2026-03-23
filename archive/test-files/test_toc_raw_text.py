"""
Show raw TOC text to understand format
"""

from pathlib import Path
from app.literature.processor import PDFProcessor

def show_toc_text():
    """Show raw TOC text"""
    
    # Initialize
    pdf_path = Path('питон_мок_дата.pdf')
    processor = PDFProcessor()
    
    # Extract text
    result = processor.extract_text_from_pdf(pdf_path)
    
    # Find TOC pages
    toc_pages = processor.find_toc_pages(result['pages'])
    
    # Get TOC text
    toc_text = '\n\n'.join([
        p['text'] for p in result['pages'] 
        if p['page_number'] in toc_pages
    ])
    
    # Show first 2000 chars
    print("=" * 80)
    print("RAW TOC TEXT (first 2000 chars):")
    print("=" * 80)
    print(toc_text[:2000])
    print("=" * 80)
    
    # Show lines 100-150
    lines = toc_text.split('\n')
    print("\nLINES 100-150:")
    print("=" * 80)
    for i, line in enumerate(lines[100:150], 100):
        print(f"{i:3d}: {line}")
    print("=" * 80)

if __name__ == '__main__':
    show_toc_text()
