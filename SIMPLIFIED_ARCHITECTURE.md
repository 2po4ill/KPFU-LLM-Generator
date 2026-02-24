# Simplified Architecture - Implementation Plan

## Changes Summary

### 1. Remove Chunking
- ❌ Delete `create_chunks()` from `processor.py`
- ❌ Remove chunk-related code from `process_book()`
- ❌ Remove embedding service dependency (or simplify to metadata only)

### 2. Simplify Generation Pipeline (3 steps instead of 5)

**OLD (5 steps)**:
1. Book Relevance (semantic search on chunks)
2. Page Selection (TOC-based)
3. Content Generation
4. Semantic Validation (chunk-based)
5. FGOS Formatting

**NEW (3 steps)**:
1. Page Selection (TOC-based, with "0" for irrelevant books)
2. Content Generation (using selected pages)
3. FGOS Formatting (with simple validation)

### 3. Update TOC Page Selection Prompt

Add instruction for LLM to return "0" if book is irrelevant:

```python
prompt = f"""Вот оглавление книги:

{toc_text}

Тема лекции: "{theme}"

Какие страницы в этой книге относятся к этой теме?

ВАЖНО: Если в этой книге НЕТ разделов по этой теме, верни только цифру 0

Верни ТОЛЬКО номера страниц через запятую, например: 101, 102, 103
Или верни 0 если книга не подходит.

Номера страниц:"""
```

### 4. Simple Validation

Instead of complex semantic validation, use simple checks:
- Does content mention book title?
- Does content have code examples?
- Is content length reasonable (>1000 chars)?

```python
def _simple_validation(self, content: str, selected_pages: List[Dict]) -> float:
    score = 0.0
    
    # Check 1: Content length (0.3)
    if len(content) > 1000:
        score += 0.3
    
    # Check 2: Has code examples (0.3)
    if '```' in content or 'def ' in content or 'class ' in content:
        score += 0.3
    
    # Check 3: References pages (0.4)
    for page in selected_pages:
        if str(page['page_number']) in content:
            score += 0.1
            break
    
    return min(score, 1.0)
```

### 5. Store Selected Pages for Validation

Cache the pages used in generation:

```python
# In generate_lecture():
self.last_selected_pages = selected_pages  # Store for validation
```

## Implementation Steps

1. ✅ Update `_get_page_numbers_from_toc()` to handle "0" response
2. ✅ Remove `_step1_hybrid_book_relevance()` 
3. ✅ Rename `_step2_smart_page_selection()` to `_step1_smart_page_selection()`
4. ✅ Rename `_step3_content_generation()` to `_step2_content_generation()`
5. ✅ Remove `_step4_semantic_validation()`
6. ✅ Add `_simple_validation()` method
7. ✅ Rename `_step5_fgos_formatting()` to `_step3_fgos_formatting()`
8. ✅ Update `generate_lecture()` to use 3-step flow
9. ✅ Remove chunking from `processor.py`
10. ✅ Test with OOP lecture

## Files to Modify

1. `app/generation/generator.py` - Main changes
2. `app/literature/processor.py` - Remove chunking
3. `app/literature/embeddings.py` - Simplify or remove
4. Test scripts - Update to new flow

## Expected Benefits

- 🚀 Faster: No chunking, no complex validation (~30s saved)
- 🎯 Simpler: 3 steps instead of 5
- 🔧 Maintainable: Less code, clearer logic
- ✅ Reliable: Trust user's book choice, let TOC filter

## Next Action

Should I proceed with implementing these changes?
