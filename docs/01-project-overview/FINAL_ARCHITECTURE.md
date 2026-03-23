# Final Simplified Architecture

## Core Principles
1. ✅ Trust user's book selection - no book filtering
2. ✅ Use TOC for page selection - LLM returns "0" if irrelevant
3. ✅ Remove chunking completely - not needed
4. ✅ Validate against actual pages used - proper anti-hallucination

## New 3-Step Pipeline

### Step 1: Smart Page Selection (TOC-based)
**Input**: Theme + List of book_ids
**Process**:
```python
for each book_id:
    1. Load book PDF
    2. Find TOC pages (3-7)
    3. Extract raw TOC text
    4. Ask LLM: "Which pages cover {theme}? Return 0 if none."
    5. If LLM returns "0" → skip this book
    6. If LLM returns page numbers → load those full pages
```
**Output**: List of selected pages with full content

**Prompt Update**:
```python
prompt = f"""Вот оглавление книги:

{toc_text}

Тема лекции: "{theme}"

Какие страницы в этой книге относятся к этой теме?

ВАЖНО: 
- Если в книге НЕТ разделов по этой теме, верни ТОЛЬКО цифру: 0
- Если есть подходящие разделы, верни номера страниц через запятую

Примеры:
- Если тема не подходит: 0
- Если тема подходит: 101, 102, 103, 104

Номера страниц:"""
```

---

### Step 2: Content Generation
**Input**: Theme + RPD data + Selected pages
**Process**:
```python
1. Prepare context from selected pages (top 5-10 pages)
2. Create prompt with theme + page content
3. LLM generates lecture
4. Return generated content
```
**Output**: Generated lecture content

**No changes needed** - already working

---

### Step 3: Semantic Validation (Against Used Pages)
**Input**: Generated content + Selected pages
**Process**:
```python
1. Extract factual claims from generated content using LLM
2. For each claim:
    - Generate embedding for claim
    - Generate embeddings for selected pages
    - Calculate cosine similarity
    - If similarity > threshold → claim is supported
3. Calculate confidence = supported_claims / total_claims
4. Return confidence score
```
**Output**: Confidence score (0-1)

**Key Change**: Validate against `selected_pages` content, NOT chunks!

```python
async def _validate_against_pages(
    self,
    generated_content: str,
    selected_pages: List[Dict[str, Any]]
) -> float:
    """
    Validate generated content against the actual pages used
    
    This is the anti-hallucination check
    """
    # Extract claims
    claims = await self._extract_claims(generated_content)
    
    if not claims:
        return 0.75  # Default if no claims extracted
    
    # Get embedding model
    embedding_model = await self.model_manager.get_embedding_model()
    
    # Generate embeddings for all selected pages
    page_texts = [p['content'] for p in selected_pages]
    page_embeddings = embedding_model.encode(page_texts)
    
    # Validate each claim
    supported = 0
    for claim in claims:
        claim_embedding = embedding_model.encode([claim])[0]
        
        # Calculate similarity with each page
        max_similarity = 0
        for page_emb in page_embeddings:
            similarity = cosine_similarity(claim_embedding, page_emb)
            max_similarity = max(max_similarity, similarity)
        
        # Claim is supported if similarity > 0.4
        if max_similarity > 0.4:
            supported += 1
    
    confidence = supported / len(claims)
    return confidence
```

---

### Step 4: FGOS Formatting
**Input**: Generated content + RPD data + Selected pages
**Process**:
```python
1. Add FGOS header with RPD data
2. Add citations from selected pages
3. Add date
4. Return formatted content
```
**Output**: Final formatted lecture

**No changes needed** - already working

---

## Changes to processor.py

### Remove Chunking

**Before**:
```python
def process_book(pdf_path, book_id):
    # Extract text
    pages = extract_text_from_pdf(pdf_path)
    
    # Create chunks ❌ REMOVE THIS
    chunks = create_chunks(pages, book_id)
    
    # Parse TOC
    toc = parse_toc(pages)
    
    return {
        'chunks': chunks,  # ❌ REMOVE
        'toc': toc,
        'pages': pages
    }
```

**After**:
```python
def process_book(pdf_path, book_id):
    # Extract text
    pages = extract_text_from_pdf(pdf_path)
    
    # Find TOC pages
    toc_pages = find_toc_pages(pages)
    
    return {
        'book_id': book_id,
        'total_pages': len(pages),
        'toc_page_numbers': toc_pages,
        'pages': pages,  # Keep full pages for later use
        'metadata': extract_metadata(pdf_path)
    }
```

**Methods to Remove**:
- ❌ `create_chunks()`
- ❌ `extract_toc_with_llm()` (not used anymore)
- ❌ `parse_table_of_contents()` (not used anymore)
- ❌ `get_book_toc()` (not used anymore)

**Methods to Keep**:
- ✅ `extract_text_from_pdf()`
- ✅ `find_toc_pages()`
- ✅ `extract_keywords_from_text()`

---

## Changes to embeddings.py

### Option A: Remove Completely
If we don't need book-level search, remove the entire file.

### Option B: Simplify for Validation Only
Keep only for validation purposes:

```python
class ValidationService:
    """Simple service for validation only - no vector store"""
    
    def __init__(self):
        self.embedding_model = None
    
    async def initialize(self, model_manager):
        self.embedding_model = await model_manager.get_embedding_model()
    
    def validate_claims_against_pages(
        self,
        claims: List[str],
        pages: List[str]
    ) -> float:
        """Validate claims against page content"""
        # Generate embeddings
        claim_embeddings = self.embedding_model.encode(claims)
        page_embeddings = self.embedding_model.encode(pages)
        
        # Calculate similarities
        supported = 0
        for claim_emb in claim_embeddings:
            max_sim = max([
                cosine_similarity(claim_emb, page_emb)
                for page_emb in page_embeddings
            ])
            if max_sim > 0.4:
                supported += 1
        
        return supported / len(claims) if claims else 0.5
```

**Recommendation**: Option B - keep simplified version for validation

---

## Implementation Order

### Phase 1: Update Generator (Priority 1)
1. ✅ Update `_get_page_numbers_from_toc()` - add "0" handling
2. ✅ Remove `_step1_hybrid_book_relevance()`
3. ✅ Update `_step2_smart_page_selection()` to work with book_ids directly
4. ✅ Keep `_step3_content_generation()` as-is
5. ✅ Rewrite `_step4_semantic_validation()` to validate against selected_pages
6. ✅ Keep `_step5_fgos_formatting()` as-is
7. ✅ Update `generate_lecture()` main flow

### Phase 2: Update Processor (Priority 2)
1. ✅ Remove `create_chunks()` method
2. ✅ Remove unused TOC parsing methods
3. ✅ Simplify `process_book()` return value
4. ✅ Update tests

### Phase 3: Simplify Embeddings (Priority 3)
1. ✅ Remove FAISS vector store code
2. ✅ Keep only validation functionality
3. ✅ Update initialization

### Phase 4: Test End-to-End (Priority 4)
1. ✅ Test OOP lecture generation
2. ✅ Verify validation works correctly
3. ✅ Check confidence scores are reasonable
4. ✅ Verify no hallucination

---

## Expected Results

### Performance
- **Before**: ~200s total (6s book selection + 60s page selection + 120s generation + 14s validation)
- **After**: ~180s total (60s page selection + 120s generation + 0s formatting)
- **Savings**: ~20s (removed book selection overhead)

### Accuracy
- **Before**: 0% confidence (validating against wrong data)
- **After**: 60-80% confidence (validating against correct pages)

### Simplicity
- **Before**: 5 steps, chunking, FAISS, complex validation
- **After**: 3 steps, no chunking, direct validation

---

## Next Steps

1. Implement Phase 1 (Generator updates)
2. Test with single OOP lecture
3. If working, proceed with Phase 2-3
4. Final end-to-end testing

Ready to start implementation?
