"""
Test Russian-specific embedding model (rubert-tiny2)
"""

import asyncio
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def test_rubert():
    print("=" * 80)
    print("Testing Russian-Specific Embedding Model: cointegrated/rubert-tiny2")
    print("=" * 80)
    
    # Initialize
    print("\n1. Loading model...")
    model_manager = ModelManager()
    await model_manager.initialize()
    
    embedding_model = await model_manager.get_embedding_model()
    print(f"✓ Model loaded: {embedding_model}")
    
    # Test basic similarity
    print("\n2. Testing basic Russian similarity...")
    
    test_pairs = [
        ("ООП", "Объектно-ориентированное программирование"),
        ("Строки", "Работа со строками"),
        ("Циклы", "Цикл for"),
        ("Функции", "Определение функций"),
        ("Строки", "Логические и физические строки"),  # Should be lower
    ]
    
    for text1, text2 in test_pairs:
        emb1 = embedding_model.encode([text1])[0]
        emb2 = embedding_model.encode([text2])[0]
        
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2)
        )
        
        print(f"  '{text1}' <-> '{text2}': {similarity:.3f}")
    
    # Test with actual TOC
    print("\n3. Testing with actual TOC...")
    
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    pdf_path = Path('питон_мок_дата.pdf')
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    
    sections = generator._parse_toc_with_regex(toc_text)
    print(f"✓ Parsed {len(sections)} sections")
    
    # Test theme matching
    theme = "Работа со строками: форматирование, методы строк, срезы"
    print(f"\n4. Testing theme: '{theme}'")
    
    theme_embedding = embedding_model.encode([theme])[0]
    section_titles = [s['title'] for s in sections]
    title_embeddings = embedding_model.encode(section_titles)
    
    # Calculate similarities
    matches = []
    for i, section in enumerate(sections):
        title_emb = title_embeddings[i]
        
        similarity = np.dot(theme_embedding, title_emb) / (
            np.linalg.norm(theme_embedding) * np.linalg.norm(title_emb)
        )
        
        if similarity > 0.3:  # Lower threshold for testing
            matches.append((section, similarity))
    
    # Sort and show top matches
    matches.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n5. Top matches (threshold > 0.3):")
    for section, sim in matches[:10]:
        marker = "✓" if sim > 0.4 else "~"
        print(f"  {marker} {sim:.3f} - {section['number']:6s} {section['title']:50s} pages {section['page']}-{section['end_page']}")
    
    # Check expected sections
    print(f"\n6. Expected sections:")
    print(f"   7.4 Строки (pages 36-38)")
    print(f"   12.8 Ещё о строках (pages 89-90)")
    
    expected_found = []
    for section, sim in matches:
        if section['number'] in ['7.4', '12.8']:
            expected_found.append((section, sim))
            print(f"   ✓ Found: {section['number']} '{section['title']}' (similarity: {sim:.3f})")
    
    if len(expected_found) == 2:
        print(f"\n✓ SUCCESS: Both expected sections found!")
    else:
        print(f"\n⚠ WARNING: Only {len(expected_found)}/2 expected sections found")
    
    await model_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_rubert())
