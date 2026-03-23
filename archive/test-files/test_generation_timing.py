"""
Detailed timing breakdown for content generation
Profile each step to identify bottlenecks
"""

import asyncio
import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.model_manager import ModelManager
from app.literature.processor import PDFProcessor
from app.generation.generator_v2 import ContentGenerator


async def profile_content_generation():
    """Profile content generation with detailed timing"""
    
    print("=" * 80)
    print("DETAILED TIMING BREAKDOWN")
    print("=" * 80)
    
    # Initialize components
    model_manager = ModelManager()
    pdf_processor = PDFProcessor()
    generator = ContentGenerator(use_mock=False)
    await generator.initialize(model_manager, pdf_processor)
    
    theme = "Работа со строками: форматирование, методы строк, срезы"
    book_ids = ['python_book_1']
    pdf_path = Path('питон_мок_дата.pdf')
    
    # ========== STEP 1: PAGE SELECTION ==========
    print("\n" + "=" * 80)
    print("STEP 1: PAGE SELECTION")
    print("=" * 80)
    
    step1_start = time.time()
    
    # 1.1: Extract PDF
    t1 = time.time()
    pages_data = pdf_processor.extract_text_from_pdf(pdf_path)
    t1_extract = time.time() - t1
    print(f"\n1.1 PDF Extraction: {t1_extract:.2f}s")
    print(f"    - Pages extracted: {pages_data['total_pages']}")
    
    # 1.2: Find TOC
    t2 = time.time()
    toc_page_numbers = pdf_processor.find_toc_pages(pages_data['pages'])
    t2_toc = time.time() - t2
    print(f"\n1.2 TOC Detection: {t2_toc:.2f}s")
    print(f"    - TOC pages: {toc_page_numbers}")
    
    # 1.3: Get TOC text
    t3 = time.time()
    toc_text = '\n\n'.join([
        p['text'] for p in pages_data['pages'] 
        if p['page_number'] in toc_page_numbers
    ])
    t3_text = time.time() - t3
    print(f"\n1.3 TOC Text Extraction: {t3_text:.2f}s")
    print(f"    - TOC length: {len(toc_text)} chars")
    
    # 1.4: Parse TOC with regex
    t4 = time.time()
    sections = generator._parse_toc_with_regex(toc_text)
    t4_parse = time.time() - t4
    print(f"\n1.4 TOC Regex Parsing: {t4_parse:.2f}s")
    print(f"    - Sections parsed: {len(sections)}")
    
    # 1.5: Format TOC for LLM
    t5 = time.time()
    formatted_sections = []
    for section in sections:
        formatted_sections.append(
            f"{section['number']} {section['title']} (pages {section['page']}-{section['end_page']})"
        )
    full_toc = '\n'.join(formatted_sections)
    t5_format = time.time() - t5
    print(f"\n1.5 TOC Formatting: {t5_format:.2f}s")
    print(f"    - Formatted TOC length: {len(full_toc)} chars")
    
    # 1.6: LLM call for page selection
    t6 = time.time()
    llm_model = await model_manager.get_llm_model()
    
    prompt = f"""Тема: "{theme}"

Выбери разделы, которые учат этой теме.

Оглавление:
{full_toc}

Ответ (номера разделов):"""
    
    print(f"\n1.6 LLM Page Selection (Gemma 3 27B)...")
    print(f"    - Prompt length: {len(prompt)} chars")
    
    response = await llm_model.generate(
        model="gemma3:27b",
        prompt=prompt,
        options={
            "temperature": 0.1,
            "num_predict": 100
        }
    )
    t6_llm = time.time() - t6
    print(f"    - LLM call time: {t6_llm:.2f}s")
    print(f"    - Response: {response.get('response', '').strip()}")
    
    # 1.7: Parse response and get pages
    t7 = time.time()
    page_numbers = await generator._get_page_numbers_from_toc(theme, toc_text)
    t7_parse = time.time() - t7
    print(f"\n1.7 Total Page Selection: {t7_parse:.2f}s")
    print(f"    - Selected pages: {page_numbers}")
    
    step1_total = time.time() - step1_start
    print(f"\n{'='*80}")
    print(f"STEP 1 TOTAL: {step1_total:.2f}s")
    print(f"{'='*80}")
    
    # ========== STEP 2: CONTENT GENERATION ==========
    print("\n" + "=" * 80)
    print("STEP 2: CONTENT GENERATION")
    print("=" * 80)
    
    step2_start = time.time()
    
    # 2.1: Prepare selected pages
    t8 = time.time()
    selected_pages = []
    for page_num in page_numbers:
        page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
        if page_data:
            selected_pages.append({
                'book_id': 'python_book_1',
                'book_title': 'A Byte of Python',
                'page_number': page_num,
                'content': page_data['text'],
                'relevance_score': 1.0
            })
    t8_prep = time.time() - t8
    print(f"\n2.1 Page Preparation: {t8_prep:.2f}s")
    print(f"    - Pages prepared: {len(selected_pages)}")
    
    # 2.2: Build context
    t9 = time.time()
    pages_to_use = selected_pages[:15]
    context = "\n\n---PAGE BREAK---\n\n".join([
        f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
        for p in pages_to_use
    ])
    t9_context = time.time() - t9
    print(f"\n2.2 Context Building: {t9_context:.2f}s")
    print(f"    - Context length: {len(context)} chars")
    print(f"    - Pages in context: {len(pages_to_use)}")
    
    # 2.3: LLM content generation
    t10 = time.time()
    print(f"\n2.3 LLM Content Generation (Gemma 3 27B)...")
    print(f"    - Starting generation...")
    
    rpd_data = {
        'subject_title': 'Основы программирования на Python',
        'profession': 'Программная инженерия',
        'academic_degree': 'bachelor',
        'department': 'Кафедра информационных систем'
    }
    
    generated_content = await generator._step2_content_generation(theme, rpd_data, selected_pages)
    t10_llm = time.time() - t10
    print(f"    - LLM generation time: {t10_llm:.2f}s")
    print(f"    - Generated length: {len(generated_content)} chars")
    print(f"    - Word count: ~{len(generated_content.split())} words")
    
    step2_total = time.time() - step2_start
    print(f"\n{'='*80}")
    print(f"STEP 2 TOTAL: {step2_total:.2f}s")
    print(f"{'='*80}")
    
    # ========== STEP 3: VALIDATION ==========
    print("\n" + "=" * 80)
    print("STEP 3: VALIDATION & FORMATTING")
    print("=" * 80)
    
    step3_start = time.time()
    
    # 3.1: Extract claims
    t11 = time.time()
    print(f"\n3.1 Extracting Claims (Gemma 3 27B)...")
    claims = await generator._extract_claims(generated_content)
    t11_extract = time.time() - t11
    print(f"    - Claim extraction time: {t11_extract:.2f}s")
    print(f"    - Claims extracted: {len(claims)}")
    if claims:
        print(f"    - First claim: {claims[0][:80]}...")
    
    # 3.2: Load embedding model
    t12 = time.time()
    print(f"\n3.2 Loading Embedding Model...")
    embedding_model = await model_manager.get_embedding_model()
    t12_load = time.time() - t12
    print(f"    - Model load time: {t12_load:.2f}s")
    
    # 3.3: Generate page embeddings
    t13 = time.time()
    print(f"\n3.3 Generating Page Embeddings...")
    page_texts = [p['content'] for p in selected_pages]
    page_embeddings = embedding_model.encode(page_texts)
    t13_embed = time.time() - t13
    print(f"    - Page embedding time: {t13_embed:.2f}s")
    print(f"    - Pages embedded: {len(page_embeddings)}")
    
    # 3.4: Validate claims
    t14 = time.time()
    print(f"\n3.4 Validating Claims...")
    confidence = await generator._validate_against_pages(generated_content, selected_pages)
    t14_validate = time.time() - t14
    print(f"    - Validation time: {t14_validate:.2f}s")
    print(f"    - Confidence score: {confidence:.2%}")
    
    # 3.5: FGOS formatting
    t15 = time.time()
    formatted_content, citations = await generator._fgos_formatting(generated_content, rpd_data, selected_pages)
    t15_format = time.time() - t15
    print(f"\n3.5 FGOS Formatting: {t15_format:.2f}s")
    print(f"    - Citations: {len(citations)}")
    
    step3_total = time.time() - step3_start
    print(f"\n{'='*80}")
    print(f"STEP 3 TOTAL: {step3_total:.2f}s")
    print(f"{'='*80}")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 80)
    print("TIMING SUMMARY")
    print("=" * 80)
    
    total_time = step1_total + step2_total + step3_total
    
    print(f"\nStep 1 (Page Selection): {step1_total:.2f}s ({step1_total/total_time*100:.1f}%)")
    print(f"  - PDF extraction: {t1_extract:.2f}s")
    print(f"  - TOC detection: {t2_toc:.2f}s")
    print(f"  - TOC parsing: {t4_parse:.2f}s")
    print(f"  - LLM page selection: {t6_llm:.2f}s")
    
    print(f"\nStep 2 (Content Generation): {step2_total:.2f}s ({step2_total/total_time*100:.1f}%)")
    print(f"  - Page preparation: {t8_prep:.2f}s")
    print(f"  - Context building: {t9_context:.2f}s")
    print(f"  - LLM generation: {t10_llm:.2f}s")
    
    print(f"\nStep 3 (Validation): {step3_total:.2f}s ({step3_total/total_time*100:.1f}%)")
    print(f"  - Claim extraction (LLM): {t11_extract:.2f}s")
    print(f"  - Embedding model load: {t12_load:.2f}s")
    print(f"  - Page embeddings: {t13_embed:.2f}s")
    print(f"  - Claim validation: {t14_validate:.2f}s")
    print(f"  - FGOS formatting: {t15_format:.2f}s")
    
    print(f"\nTOTAL TIME: {total_time:.2f}s")
    
    print("\n" + "=" * 80)
    print("BOTTLENECK ANALYSIS")
    print("=" * 80)
    
    bottlenecks = [
        ("LLM Content Generation", t10_llm),
        ("Step 3 Validation Total", step3_total),
        ("Step 1 Page Selection Total", step1_total),
        ("Claim Extraction (LLM)", t11_extract),
        ("LLM Page Selection", t6_llm),
    ]
    
    bottlenecks.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 5 Slowest Operations:")
    for i, (name, duration) in enumerate(bottlenecks[:5], 1):
        print(f"{i}. {name}: {duration:.2f}s ({duration/total_time*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(profile_content_generation())
