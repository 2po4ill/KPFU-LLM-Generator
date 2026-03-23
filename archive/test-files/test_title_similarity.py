"""
Test semantic similarity between theme and book title
"""

import asyncio
from app.core.model_manager import ModelManager

async def test_similarity():
    """Test if semantic similarity works for book selection"""
    
    print("=" * 80)
    print("TESTING SEMANTIC SIMILARITY FOR BOOK SELECTION")
    print("=" * 80)
    
    # Initialize
    model_manager = ModelManager()
    embedding_model = await model_manager.get_embedding_model()
    
    # Test cases
    test_cases = [
        {
            'theme': 'ООП',
            'titles': [
                'Путеводитель по питону',
                'A Byte of Python',
                'Объектно-ориентированное программирование на Python',
                'Введение в программирование',
                'Python для начинающих'
            ]
        },
        {
            'theme': 'Основы ООП: Классы, объекты, методы',
            'titles': [
                'Путеводитель по питону',
                'A Byte of Python',
                'Объектно-ориентированное программирование на Python',
            ]
        },
        {
            'theme': 'Функции в Python',
            'titles': [
                'Путеводитель по питону',
                'Функциональное программирование',
                'Python: полное руководство'
            ]
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: Theme = '{test['theme']}'")
        print(f"{'='*80}")
        
        # Get theme embedding
        theme_embedding = embedding_model.encode([test['theme']])[0]
        
        # Calculate similarity for each title
        results = []
        for title in test['titles']:
            title_embedding = embedding_model.encode([title])[0]
            
            # Cosine similarity
            import numpy as np
            similarity = np.dot(theme_embedding, title_embedding) / (
                np.linalg.norm(theme_embedding) * np.linalg.norm(title_embedding)
            )
            
            results.append((title, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Print results
        print(f"\nResults (sorted by similarity):")
        for title, sim in results:
            bar = '█' * int(sim * 50)
            print(f"  {sim:.3f} {bar} {title}")
        
        # Check if generic title ranks high
        generic_titles = ['Путеводитель по питону', 'A Byte of Python', 'Python для начинающих']
        top_title = results[0][0]
        
        if top_title in generic_titles:
            print(f"\n  ⚠️  WARNING: Generic title '{top_title}' ranked highest!")
            print(f"      This means semantic similarity on title alone may not work well.")
        else:
            print(f"\n  ✓ Specific title ranked highest: '{top_title}'")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nIf generic titles (like 'Путеводитель по питону') rank high for specific")
    print("themes (like 'ООП'), then title-based semantic search won't work well.")
    print("\nAlternatives:")
    print("  1. Use TOC content for book selection (not just title)")
    print("  2. Use keywords extracted from book")
    print("  3. Use LLM to match theme to book description")
    print("  4. Just use ALL books (if we only have a few)")

if __name__ == '__main__':
    asyncio.run(test_similarity())
