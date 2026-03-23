"""
Extract TOC and parse it with regex, save to file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


def extract_and_parse_toc():
    print("Extracting and parsing TOC...")
    
    # Extract PDF
    pdf_processor = PDFProcessor()
    pdf_path = Path('питон_мок_дата.pdf')
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    # Get TOC pages
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    # Parse with regex
    generator = ContentGenerator(use_mock=True)
    sections = generator._parse_toc_with_regex(toc_text)
    
    print(f"Parsed {len(sections)} sections")
    
    # Format as structured list with ranges
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("PARSED TOC WITH PAGE RANGES")
    output_lines.append("=" * 80)
    output_lines.append("")
    
    for section in sections:
        # Format: "7.4 Строки (pages 36-38)"
        line = f"{section['number']:8s} {section['title']:60s} (pages {section['page']}-{section['end_page']})"
        output_lines.append(line)
    
    output_lines.append("")
    output_lines.append("=" * 80)
    output_lines.append(f"Total: {len(sections)} sections")
    output_lines.append("=" * 80)
    
    # Save to file
    output_file = Path('toc_parsed_with_ranges.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Saved to: {output_file}")
    
    # Also print first 20 sections
    print("\nFirst 20 sections:")
    for section in sections[:20]:
        print(f"  {section['number']:8s} {section['title']:50s} (pages {section['page']}-{section['end_page']})")


if __name__ == "__main__":
    extract_and_parse_toc()
