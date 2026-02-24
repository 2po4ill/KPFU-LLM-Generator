"""
Validate lecture accuracy by comparing generated content with actual book pages
"""

import sys
from pathlib import Path
import re

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.literature.processor import PDFProcessor


def extract_page_references(lecture_content: str) -> list:
    """Extract all page numbers referenced in the lecture"""
    # Pattern: "страницы [number]" or "страниц[аыеи] [number]"
    pattern = r'страниц[аыеи]?\s+\[?(\d+)\]?'
    matches = re.findall(pattern, lecture_content, re.IGNORECASE)
    return [int(m) for m in matches]


def extract_code_examples(lecture_content: str) -> list:
    """Extract all code examples with their page references"""
    examples = []
    
    # Pattern: # Пример со страницы [number] followed by code block
    pattern = r'#\s*Пример\s+со\s+страниц[аыеи]\s+\[?(\d+)\]?\s*\n```python\n(.*?)\n```'
    matches = re.findall(pattern, lecture_content, re.DOTALL | re.IGNORECASE)
    
    for page_num, code in matches:
        examples.append({
            'page': int(page_num),
            'code': code.strip()
        })
    
    return examples


def check_code_in_page(code: str, page_content: str) -> dict:
    """Check if code example exists in page content"""
    # Normalize whitespace for comparison
    code_normalized = ' '.join(code.split())
    page_normalized = ' '.join(page_content.split())
    
    # Check for exact match
    if code_normalized in page_normalized:
        return {'found': True, 'match_type': 'exact'}
    
    # Check for partial match (at least 50% of code)
    code_words = code_normalized.split()
    matches = sum(1 for word in code_words if word in page_normalized)
    match_ratio = matches / len(code_words) if code_words else 0
    
    if match_ratio > 0.5:
        return {'found': True, 'match_type': 'partial', 'ratio': match_ratio}
    
    return {'found': False, 'match_type': 'none', 'ratio': match_ratio}


def extract_claims(lecture_content: str) -> list:
    """Extract factual claims from lecture"""
    claims = []
    
    # Split into sentences
    sentences = re.split(r'[.!?]\s+', lecture_content)
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Skip short sentences, questions, headers
        if len(sentence) < 30:
            continue
        if sentence.endswith('?'):
            continue
        if sentence.startswith('#') or sentence.startswith('**'):
            continue
        
        # Look for technical claims (contains Python keywords or technical terms)
        technical_keywords = [
            'метод', 'функци', 'строк', 'переменн', 'оператор', 'класс',
            'объект', 'тип', 'значени', 'параметр', 'аргумент', 'возвращает',
            'преобразует', 'используется', 'позволяет', 'Python'
        ]
        
        if any(keyword in sentence.lower() for keyword in technical_keywords):
            claims.append(sentence)
    
    return claims[:20]  # Limit to 20 claims


def check_claim_in_pages(claim: str, pages_content: list) -> dict:
    """Check if claim is supported by page content"""
    claim_normalized = ' '.join(claim.lower().split())
    
    for page in pages_content:
        page_normalized = ' '.join(page['content'].lower().split())
        
        # Check for keyword overlap
        claim_words = set(claim_normalized.split())
        page_words = set(page_normalized.split())
        
        # Remove common words
        common_words = {'и', 'в', 'на', 'с', 'для', 'как', 'это', 'что', 'по', 'из', 'к', 'о'}
        claim_words -= common_words
        page_words -= common_words
        
        if not claim_words:
            continue
        
        overlap = claim_words & page_words
        overlap_ratio = len(overlap) / len(claim_words)
        
        if overlap_ratio > 0.4:
            return {
                'supported': True,
                'page': page['page_number'],
                'overlap_ratio': overlap_ratio
            }
    
    return {'supported': False, 'overlap_ratio': 0}


def main():
    print("=" * 80)
    print("LECTURE ACCURACY VALIDATION")
    print("=" * 80)
    
    # Load lecture
    lecture_path = Path('test_gemma_lecture.md')
    if not lecture_path.exists():
        print("ERROR: test_gemma_lecture.md not found")
        return
    
    lecture_content = lecture_path.read_text(encoding='utf-8')
    print(f"\n✓ Loaded lecture: {len(lecture_content)} chars, ~{len(lecture_content.split())} words")
    
    # Load PDF
    pdf_path = Path('питон_мок_дата.pdf')
    if not pdf_path.exists():
        print("ERROR: PDF not found")
        return
    
    pdf_processor = PDFProcessor()
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    
    if not pages_data['success']:
        print("ERROR: Failed to extract PDF")
        return
    
    print(f"✓ Loaded PDF: {pages_data['total_pages']} pages")
    
    # Expected pages (from page selection)
    expected_pages = [36, 37, 38, 39, 41, 42, 89, 90, 134, 135]
    print(f"\n✓ Expected pages (from selection): {expected_pages}")
    
    # Extract page references from lecture
    referenced_pages = extract_page_references(lecture_content)
    unique_refs = sorted(set(referenced_pages))
    print(f"✓ Pages referenced in lecture: {unique_refs}")
    print(f"  Total references: {len(referenced_pages)}")
    
    # Check which references are valid
    valid_refs = [p for p in unique_refs if p in expected_pages]
    invalid_refs = [p for p in unique_refs if p not in expected_pages]
    
    print(f"\n{'='*80}")
    print("PAGE REFERENCE VALIDATION")
    print(f"{'='*80}")
    print(f"✓ Valid references (in selected pages): {valid_refs}")
    print(f"✗ Invalid references (NOT in selected pages): {invalid_refs}")
    print(f"\nAccuracy: {len(valid_refs)}/{len(unique_refs)} = {len(valid_refs)/len(unique_refs)*100:.1f}%")
    
    # Extract and validate code examples
    print(f"\n{'='*80}")
    print("CODE EXAMPLE VALIDATION")
    print(f"{'='*80}")
    
    code_examples = extract_code_examples(lecture_content)
    print(f"\nFound {len(code_examples)} code examples in lecture")
    
    valid_code = 0
    invalid_code = 0
    
    for i, example in enumerate(code_examples[:10], 1):  # Check first 10
        page_num = example['page']
        code = example['code']
        
        print(f"\nExample {i}: Page {page_num}")
        print(f"Code preview: {code[:60]}...")
        
        # Check if page is in expected pages
        if page_num not in expected_pages:
            print(f"  ✗ Page {page_num} NOT in selected pages!")
            invalid_code += 1
            continue
        
        # Get page content
        page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
        
        if not page_data:
            print(f"  ✗ Could not load page {page_num}")
            invalid_code += 1
            continue
        
        # Check if code exists in page
        result = check_code_in_page(code, page_data['text'])
        
        if result['found']:
            print(f"  ✓ Code found in page ({result['match_type']} match)")
            if 'ratio' in result:
                print(f"    Match ratio: {result['ratio']:.1%}")
            valid_code += 1
        else:
            print(f"  ✗ Code NOT found in page (ratio: {result['ratio']:.1%})")
            invalid_code += 1
    
    print(f"\nCode Accuracy: {valid_code}/{valid_code + invalid_code} = {valid_code/(valid_code + invalid_code)*100:.1f}%")
    
    # Extract and validate claims
    print(f"\n{'='*80}")
    print("CONTENT CLAIMS VALIDATION")
    print(f"{'='*80}")
    
    claims = extract_claims(lecture_content)
    print(f"\nExtracted {len(claims)} technical claims from lecture")
    
    # Get content from expected pages
    expected_pages_content = [
        {'page_number': p['page_number'], 'content': p['text']}
        for p in pages_data['pages']
        if p['page_number'] in expected_pages
    ]
    
    supported_claims = 0
    unsupported_claims = 0
    
    print(f"\nValidating claims against {len(expected_pages_content)} selected pages...")
    
    for i, claim in enumerate(claims[:10], 1):  # Check first 10
        print(f"\nClaim {i}: {claim[:80]}...")
        
        result = check_claim_in_pages(claim, expected_pages_content)
        
        if result['supported']:
            print(f"  ✓ Supported by page {result['page']} (overlap: {result['overlap_ratio']:.1%})")
            supported_claims += 1
        else:
            print(f"  ✗ NOT supported by selected pages")
            unsupported_claims += 1
    
    print(f"\nClaims Accuracy: {supported_claims}/{supported_claims + unsupported_claims} = {supported_claims/(supported_claims + unsupported_claims)*100:.1f}%")
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL ACCURACY SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n1. Page References:")
    print(f"   - Valid: {len(valid_refs)}/{len(unique_refs)} ({len(valid_refs)/len(unique_refs)*100:.1f}%)")
    print(f"   - Invalid pages: {invalid_refs}")
    
    print(f"\n2. Code Examples:")
    print(f"   - Valid: {valid_code}/{valid_code + invalid_code} ({valid_code/(valid_code + invalid_code)*100:.1f}%)")
    
    print(f"\n3. Content Claims:")
    print(f"   - Supported: {supported_claims}/{supported_claims + unsupported_claims} ({supported_claims/(supported_claims + unsupported_claims)*100:.1f}%)")
    
    # Overall accuracy
    total_checks = len(unique_refs) + (valid_code + invalid_code) + (supported_claims + unsupported_claims)
    total_valid = len(valid_refs) + valid_code + supported_claims
    overall_accuracy = total_valid / total_checks * 100 if total_checks > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"OVERALL ACCURACY: {overall_accuracy:.1f}%")
    print(f"{'='*80}")
    
    if overall_accuracy >= 70:
        print("\n✓ GOOD: Lecture content is mostly accurate")
    elif overall_accuracy >= 50:
        print("\n⚠ FAIR: Lecture has some accuracy issues")
    else:
        print("\n✗ POOR: Lecture has significant accuracy problems")


if __name__ == "__main__":
    main()
