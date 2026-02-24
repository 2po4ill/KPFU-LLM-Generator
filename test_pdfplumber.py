"""
Test pdfplumber for better TOC extraction
"""

import pdfplumber

def main():
    pdf_path = 'питон_мок_дата.pdf'
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Extract TOC pages (3-7)
        toc_text = ""
        for page_num in range(2, 7):  # 0-indexed, so 2-6 = pages 3-7
            page = pdf.pages[page_num]
            text = page.extract_text()
            toc_text += text + "\n\n"
        
        # Save to file
        with open('toc_pdfplumber.txt', 'w', encoding='utf-8') as f:
            f.write(toc_text)
        
        print(f"TOC saved to toc_pdfplumber.txt ({len(toc_text)} chars)")
        
        # Show first 1000 chars
        print("\nFirst 1000 chars:")
        print(toc_text[:1000])

if __name__ == '__main__':
    main()
