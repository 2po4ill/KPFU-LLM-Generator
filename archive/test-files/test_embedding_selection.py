"""
Test embedding-based page selection with debug output
"""

import asyncio
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def test_embedding_selection():
    print("=" * 80)
    print("Testing Embedding-Based Page Selection")
    print("=" * 80)
    
    # Initialize
    model_manager = ModelManager()
    await model_manager.initialize()
    
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    # Extract PDF and get TOC
    pdf_path = Path('питон_мок_дата.pdf')
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    # Parse TOC with regex
    sections = generator._parse_toc_with_regex(toc_text)
    
    print(f"\n1. Parsed {len(sections)} sections from TOC")
    print(f"\nFirst 10 sections:")
    for i, section in enumerate(sections[:10]):
        print(f"  {section['number']:6s} {section['title']:50s} pages {section['page']}-{section['end_page']}")
    
    # Test theme
    theme = "Работа со строками: форматирование, методы строк, срезы"
    print(f"\n2. Testing theme: '{theme}'")
    
    # Get embedding model
    embedding_model = await model_manager.get_embedding_model()
    
    # Encode theme
    theme_embedding = embedding_model.encode([theme])[0]
    
    # Encode all section titles
    section_titles = [s['title'] for s in sections]
    title_embeddings = embedding_model.encode(section_titles)
    
    # Calculate similarities
    print(f"\n3. Similarity scores:")
    all_scores = []
    for i, section in enumerate(sections):
        title_emb = title_embeddings[i]
        
        similarity = np.dot(theme_embedding, title_emb) / (
            np.linalg.norm(theme_embedding) * np.linalg.norm(title_emb)
        )
        
        all_scores.append((section, similarity))
    
    # Sort by similarity
    all_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Show top 15
    print(f"\nTop 15 matches:")
    for section, sim in all_scores[:15]:
        marker = "✓" if sim > 0.4 else " "
        print(f"  {marker} {sim:.3f} - {section['number']:6s} {section['title']:50s} pages {section['page']}-{section['end_page']}")
    
    # Show expected sections
    print(f"\n4. Expected sections:")
    print(f"   7.4 Строки (pages 36-38)")
    print(f"   12.8 Ещё о строках (pages 89-90)")
    
    # Find these in our scores
    print(f"\n5. Checking expected sections:")
    for section, sim in all_scores:
        if 'Строк' in section['title'] or 'строк' in section['title']:
            marker = "✓" if sim > 0.4 else "✗"
            print(f"  {marker} {sim:.3f} - {section['number']:6s} {section['title']:50s} pages {section['page']}-{section['end_page']}")


if __name__ == "__main__":
    asyncio.run(test_embedding_selection())
