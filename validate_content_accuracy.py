"""
Improved validation: Check if content is accurate regardless of page number labels
Focus on: Is the content FROM the book pages we provided?
"""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from app.literature.processor import PDFProcessor


def extract_code_blocks(text: str) -> list:
    """Extract all code blocks from text"""
    pattern = r'```python\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [m.strip() for m in matches]


def normalize_code(code: str) -> str:
    """Normalize code for comparison"""
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Remove extra whitespace
    code = ' '.join(code.split())
    # Remove quotes differences
    code = code.replace('"', "'")
    return code.lower()


def find_code_in_pages(code: str, pages: list) -> dict:
    """Find if code exists in any of the pages"""
    code_norm = normalize_code(code)
    code_words = set(code_norm.split())
    
    # Remove very common words
    common = {'=', '(', ')', '[', ']', '{', '}', ',', '.', ':', 'print'}
    code_words -= common
    
    if not code_words:
        return {'found': False, 'reason': 'no_significant_words'}
    
    best_match = {'found': False, 'page': None, 'ratio': 0}
    
    for page in pages:
        page_norm = normalize_code(page['content'])
        page_words = set(page_norm.split())
        
        # Check word overlap
        overlap = code_words & page_words
        ratio = len(overlap) / len(code_words)
        
        if ratio > best_match['ratio']:
            best_match = {
                'found': ratio > 0.5,
                'page': page['page_number'],
                'ratio': ratio,
                'overlap_words': len(overlap),
                'total_words': len(code_words)
            }
    
    return best_match


def extract_technical_statements(text: str) -> list:
    """Extract technical statements about Python"""
    statements = []
    
    # Split into sentences
    sentences = re.split(r'[.!]\s+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Skip short, questions, headers, examples
        if len(sentence) < 40:
            continue
        if '?' in sentence:
            continue
        if sentence.startswith('#') or sentence.startswith('**') or sentence.startswith('```'):
            continue
        if 'пример' in sentence.lower() and 'страниц' in sentence.lower():
            continue
        
        # Look for technical content
        technical_indicators = [
            'метод', 'функци', 'строк', 'переменн', 'оператор',
            'возвращает', 'преобразует', 'используется', 'позволяет',
            'python', 'код', 'программ', 'данных', 'значени'
        ]
        
        if any(ind in sentence.lower() for ind in technical_indicators):
            # Skip meta-statements about the lecture itself
            meta_phrases = [
                'в этом разделе', 'мы рассмотрим', 'мы изучи', 'в этой лекции',
                'например, на странице', 'этот пример демонстрирует'
            ]
            
            if not any(phrase in sentence.lower() for phrase in meta_phrases):
                statements.append(sentence)
    
    return statements


def check_statement_in_pages(statement: str, pages: list) -> dict:
    """Check if statement content appears in pages"""
    # Extract key technical terms
    statement_lower = statement.lower()
    
    # Extract Python-specific terms
    python_terms = re.findall(r'`([^`]+)`', statement)
    python_terms += re.findall(r'\b(str|int|float|list|dict|tuple|len|upper|lower|strip|split|join|replace|format|print)\b', statement_lower)
    
    # Extract Russian technical terms
    russian_terms = []
    for word in statement_lower.split():
        if len(word) > 5 and any(c in word for c in 'аеиоуыэюя'):
            # Skip common words
            if word not in ['можно', 'также', 'например', 'только', 'всегда', 'никогда', 'должен', 'может']:
                russian_terms.append(word)
    
    all_terms = set(python_terms + russian_terms[:10])  # Limit Russian terms
    
    if not all_terms:
        return {'supported': False, 'reason': 'no_terms'}
    
    best_match = {'supported': False, 'page': None, 'ratio': 0}
    
    for page in pages:
        page_lower = page['content'].lower()
        
        # Count how many terms appear in page
        found_terms = sum(1 for term in all_terms if term in page_lower)
        ratio = found_terms / len(all_terms)
        
        if ratio > best_match['ratio']:
            best_match = {
                'supported': ratio > 0.3,  # At least 30% of terms
                'page': page['page_number'],
                'ratio': ratio,
                'found_terms': found_terms,
                'total_terms': len(all_terms)
            }
    
    return best_match


def main():
    print("=" * 80)
    print("CONTENT ACCURACY VALIDATION (Improved)")
    print("Checking if content is FROM the provided pages, regardless of labels")
    print("=" * 80)
    
    # Load lecture
    lecture_path = Path('test_gemma_lecture.md')
    lecture_content = lecture_path.read_text(encoding='utf-8')
    print(f"\n✓ Loaded lecture: ~{len(lecture_content.split())} words")
    
    # Load PDF and get selected pages
    pdf_processor = PDFProcessor()
    pages_data = pdf_processor.extract_text_from_pdf('питон_мок_дата.pdf')
    
    selected_pages = [36, 37, 38, 39, 41, 42, 89, 90, 134, 135]
    pages_content = [
        {'page_number': p['page_number'], 'content': p['text']}
        for p in pages_data['pages']
        if p['page_number'] in selected_pages
    ]
    
    print(f"✓ Loaded {len(pages_content)} selected pages: {selected_pages}")
    
    # Test 1: Code Examples
    print(f"\n{'='*80}")
    print("TEST 1: CODE EXAMPLES")
    print("Question: Are code examples FROM the selected pages?")
    print(f"{'='*80}")
    
    code_blocks = extract_code_blocks(lecture_content)
    print(f"\nFound {len(code_blocks)} code blocks in lecture")
    
    code_results = []
    for i, code in enumerate(code_blocks[:15], 1):  # Check first 15
        print(f"\nCode {i}:")
        print(f"  {code[:60]}...")
        
        result = find_code_in_pages(code, pages_content)
        code_results.append(result)
        
        if result['found']:
            print(f"  ✓ FOUND in page {result['page']}")
            print(f"    Match: {result['ratio']:.1%} ({result['overlap_words']}/{result['total_words']} words)")
        else:
            print(f"  ✗ NOT FOUND in selected pages")
            if result.get('page'):
                print(f"    Best match: page {result['page']} ({result['ratio']:.1%})")
    
    code_found = sum(1 for r in code_results if r['found'])
    code_accuracy = code_found / len(code_results) * 100 if code_results else 0
    
    print(f"\n{'='*40}")
    print(f"Code Accuracy: {code_found}/{len(code_results)} = {code_accuracy:.1f}%")
    print(f"{'='*40}")
    
    # Test 2: Technical Statements
    print(f"\n{'='*80}")
    print("TEST 2: TECHNICAL STATEMENTS")
    print("Question: Are technical facts FROM the selected pages?")
    print(f"{'='*80}")
    
    statements = extract_technical_statements(lecture_content)
    print(f"\nExtracted {len(statements)} technical statements")
    
    statement_results = []
    for i, statement in enumerate(statements[:20], 1):  # Check first 20
        print(f"\nStatement {i}:")
        print(f"  {statement[:80]}...")
        
        result = check_statement_in_pages(statement, pages_content)
        statement_results.append(result)
        
        if result['supported']:
            print(f"  ✓ SUPPORTED by page {result['page']}")
            print(f"    Terms match: {result['ratio']:.1%} ({result['found_terms']}/{result['total_terms']})")
        else:
            print(f"  ✗ NOT SUPPORTED by selected pages")
            if result.get('page'):
                print(f"    Best match: page {result['page']} ({result['ratio']:.1%})")
    
    statements_supported = sum(1 for r in statement_results if r['supported'])
    statements_accuracy = statements_supported / len(statement_results) * 100 if statement_results else 0
    
    print(f"\n{'='*40}")
    print(f"Statements Accuracy: {statements_supported}/{len(statement_results)} = {statements_accuracy:.1f}%")
    print(f"{'='*40}")
    
    # Test 3: Overall Content Check
    print(f"\n{'='*80}")
    print("TEST 3: OVERALL CONTENT SIMILARITY")
    print("Question: How much lecture content overlaps with selected pages?")
    print(f"{'='*80}")
    
    # Extract significant words from lecture (excluding code blocks and meta-text)
    lecture_text = lecture_content
    # Remove code blocks
    lecture_text = re.sub(r'```.*?```', '', lecture_text, flags=re.DOTALL)
    # Remove headers
    lecture_text = re.sub(r'^#+.*$', '', lecture_text, flags=re.MULTILINE)
    # Remove page references
    lecture_text = re.sub(r'страниц[аыеи]?\s+\[?\d+\]?', '', lecture_text, flags=re.IGNORECASE)
    
    lecture_words = set(lecture_text.lower().split())
    
    # Remove common words
    common_words = {
        'и', 'в', 'на', 'с', 'для', 'как', 'это', 'что', 'по', 'из', 'к', 'о', 'а', 'но',
        'мы', 'вы', 'он', 'она', 'они', 'этот', 'эта', 'эти', 'тот', 'та', 'те',
        'который', 'которая', 'которые', 'быть', 'есть', 'был', 'была', 'были',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'
    }
    lecture_words -= common_words
    lecture_words = {w for w in lecture_words if len(w) > 3}  # Keep words > 3 chars
    
    # Get words from selected pages
    pages_text = ' '.join([p['content'] for p in pages_content])
    pages_words = set(pages_text.lower().split())
    pages_words -= common_words
    pages_words = {w for w in pages_words if len(w) > 3}
    
    # Calculate overlap
    overlap = lecture_words & pages_words
    overlap_ratio = len(overlap) / len(lecture_words) * 100 if lecture_words else 0
    
    print(f"\nLecture unique words: {len(lecture_words)}")
    print(f"Pages unique words: {len(pages_words)}")
    print(f"Overlap: {len(overlap)} words")
    print(f"Overlap ratio: {overlap_ratio:.1f}%")
    
    # Final Summary
    print(f"\n{'='*80}")
    print("FINAL ACCURACY ASSESSMENT")
    print(f"{'='*80}")
    
    print(f"\n1. Code Examples: {code_accuracy:.1f}% accurate")
    print(f"   ({code_found}/{len(code_results)} code blocks found in selected pages)")
    
    print(f"\n2. Technical Statements: {statements_accuracy:.1f}% accurate")
    print(f"   ({statements_supported}/{len(statement_results)} statements supported by selected pages)")
    
    print(f"\n3. Overall Content Overlap: {overlap_ratio:.1f}%")
    print(f"   ({len(overlap)}/{len(lecture_words)} significant words from selected pages)")
    
    # Calculate weighted average
    overall_accuracy = (code_accuracy * 0.3 + statements_accuracy * 0.4 + overlap_ratio * 0.3)
    
    print(f"\n{'='*80}")
    print(f"OVERALL CONTENT ACCURACY: {overall_accuracy:.1f}%")
    print(f"{'='*80}")
    
    if overall_accuracy >= 70:
        print("\n✓ GOOD: Content is mostly from the provided pages")
    elif overall_accuracy >= 50:
        print("\n⚠ FAIR: Content has moderate accuracy")
    else:
        print("\n✗ POOR: Content may be hallucinated or from wrong sources")
    
    print(f"\nNote: Page number labels may be wrong, but this measures if the")
    print(f"CONTENT itself comes from the pages we provided to the LLM.")


if __name__ == "__main__":
    main()
