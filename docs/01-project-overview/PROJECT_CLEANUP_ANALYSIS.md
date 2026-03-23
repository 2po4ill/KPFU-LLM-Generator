# Project Cleanup Analysis

## Core Insight
**Book selection should be by TITLE only, not by chunking entire book content.**

## Current Architecture Issues

### ❌ PROBLEM 1: Unnecessary Chunking
**Location**: `app/literature/processor.py` - `create_chunks()`

**Current**: Split entire book into 1000-char chunks for semantic search
**Why Wrong**: We only need book title to decide relevance
**Impact**: Wastes time, memory, and processing

**Decision**: ⚠️ REMOVE chunking entirely OR only use for caching/future features

---

### ❌ PROBLEM 2: Embedding Service Complexity
**Location**: `app/literature/embeddings.py`

**Current**: FAISS vector store with 10,000+ chunk embeddings
**Why Wrong**: We don't need chunk-level search anymore
**Impact**: Unnecessary complexity, slow initialization

**Decision**: ⚠️ SIMPLIFY - Only store book metadata (title, author, TOC pages)

---

### ❌ PROBLEM 3: Step 1 Book Selection
**Location**: `app/generation/generator.py` - `_step1_hybrid_book_relevance()`

**Current**: 
```python
# Searches through chunks to find relevant books
similar_chunks = self.embedding_service.search_similar_chunks(
    query=theme,
    book_id=book_id,
    top_k=5
)
```

**Should Be**:
```python
# Simple semantic similarity on book title
book_title = "A Byte of Python"
theme = "ООП"
similarity = embedding_model.similarity(book_title, theme)
```

**Decision**: ⚠️ REPLACE with title-based matching

---

### ✅ CORRECT: Step 2 Page Selection
**Location**: `app/generation/generator.py` - `_get_page_numbers_from_toc()`

**Current**: Give LLM raw TOC → get page numbers → load full pages
**Status**: ✅ WORKING CORRECTLY (tested, returns pages 101-112 for OOP)

---

### ❌ PROBLEM 4: Validation Using Chunks
**Location**: `app/generation/generator.py` - `_validate_claims()`

**Current**: Validates claims against chunk embeddings
**Why Wrong**: Should validate against actual page content used in generation
**Impact**: Inaccurate validation

**Decision**: ⚠️ REMOVE or validate against selected pages only

---

## Proposed Clean Architecture

### New Flow

```
INPUT: Theme + List of Books

STEP 1: Book Selection (Simple)
├─ For each book:
│  ├─ Get book title
│  ├─ Calculate semantic similarity(title, theme)
│  └─ Rank books by similarity
└─ Select top 3 books

STEP 2: Page Selection (TOC-based) ✅ ALREADY WORKING
├─ For each selected book:
│  ├─ Find TOC pages (3-7)
│  ├─ Give LLM raw TOC text + theme
│  ├─ LLM returns page numbers
│  └─ Load full pages
└─ Return selected pages

STEP 3: Content Generation ✅ ALREADY WORKING
├─ Give LLM: theme + selected pages
├─ LLM generates lecture
└─ Return content

STEP 4: Validation (Simplified)
├─ Check if content references selected pages
├─ Simple keyword matching
└─ Return confidence score

STEP 5: FGOS Formatting ✅ ALREADY WORKING
└─ Format with citations
```

---

## Files to Modify

### 1. `app/literature/processor.py`
**Changes**:
- ⚠️ REMOVE `create_chunks()` method
- ⚠️ REMOVE `chunk_size`, `chunk_overlap` attributes
- ✅ KEEP `extract_text_from_pdf()`
- ✅ KEEP `find_toc_pages()`
- ⚠️ REMOVE `extract_toc_with_llm()` (not used anymore)
- ⚠️ REMOVE `parse_table_of_contents()` (not used anymore)
- ⚠️ SIMPLIFY `process_book()` to only extract metadata

**New `process_book()` should return**:
```python
{
    'book_id': str,
    'title': str,
    'author': str,
    'total_pages': int,
    'toc_page_numbers': [3, 4, 5, 6, 7],
    'pages': [full page data]  # Keep for later use
}
```

---

### 2. `app/literature/embeddings.py`
**Changes**:
- ⚠️ DECISION NEEDED: Remove entirely OR simplify to book-level only
- If keeping: Only store book titles, not chunks
- If removing: Move book metadata to simple dict/database

**Option A - Simplify**:
```python
class BookMetadataService:
    def add_book(self, book_id, title, author):
        # Store in dict or database
        
    def find_relevant_books(self, theme):
        # Simple semantic similarity on titles
```

**Option B - Remove**:
- Store book metadata in PostgreSQL
- Use simple keyword matching for book selection

---

### 3. `app/generation/generator.py`
**Changes**:
- ⚠️ REWRITE `_step1_hybrid_book_relevance()` - use title matching only
- ✅ KEEP `_step2_smart_page_selection()` - working correctly
- ✅ KEEP `_get_page_numbers_from_toc()` - working correctly
- ✅ KEEP `_step3_content_generation()` - working correctly
- ⚠️ SIMPLIFY `_step4_semantic_validation()` - remove chunk-based validation
- ✅ KEEP `_step5_fgos_formatting()` - working correctly

---

### 4. `app/api/literature_routes.py`
**Changes**:
- ⚠️ UPDATE `/upload` endpoint to not generate chunks
- ⚠️ SIMPLIFY book processing

---

## Database Schema Changes

### Current `literature_cache` table:
```sql
CREATE TABLE literature_cache (
    book_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    authors TEXT,
    total_pages INTEGER,
    total_chars INTEGER,
    chunks_count INTEGER,  -- ⚠️ REMOVE
    faiss_index_path VARCHAR(500),  -- ⚠️ REMOVE
    keywords TEXT,
    metadata JSONB,
    processed_at TIMESTAMP,
    last_accessed TIMESTAMP
);
```

### Proposed `literature_cache` table:
```sql
CREATE TABLE literature_cache (
    book_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    authors TEXT,
    total_pages INTEGER,
    toc_page_numbers INTEGER[],  -- NEW: Store TOC pages
    file_path VARCHAR(500),  -- NEW: Path to PDF
    keywords TEXT,
    metadata JSONB,
    processed_at TIMESTAMP,
    last_accessed TIMESTAMP
);
```

---

## Controversial Decisions to Discuss

### 🤔 DECISION 1: Keep or Remove Embedding Service?
**Option A**: Remove entirely, use simple keyword matching
- Pros: Simpler, faster, no ML dependencies
- Cons: Less accurate book selection

**Option B**: Keep but simplify to book-level only
- Pros: Better book selection accuracy
- Cons: Still need embedding model

**Recommendation**: Keep simplified version for book title matching

---

### 🤔 DECISION 2: Validation Strategy
**Current**: Semantic validation with claim extraction (not working well)

**Option A**: Remove validation entirely
- Pros: Simpler, faster
- Cons: No quality check

**Option B**: Simple keyword validation
- Check if content mentions book title
- Check if content has code examples
- Pros: Fast, simple
- Cons: Less thorough

**Option C**: Keep semantic validation but use selected pages only
- Pros: More accurate
- Cons: Still complex

**Recommendation**: Option B - simple keyword validation

---

### 🤔 DECISION 3: Caching Strategy
**Current**: Cache chunks in FAISS

**Option A**: Cache full pages in memory
- Pros: Fast access
- Cons: High memory usage

**Option B**: Cache nothing, read from PDF each time
- Pros: Low memory
- Cons: Slower

**Option C**: Cache TOC and metadata only
- Pros: Balance of speed and memory
- Cons: Still need to read pages

**Recommendation**: Option C - cache TOC and metadata

---

## Implementation Priority

### Phase 1: Critical Cleanup (Do First)
1. ✅ Fix Step 2 (TOC-based page selection) - DONE
2. ⚠️ Simplify Step 1 (title-based book selection)
3. ⚠️ Remove chunking from processor
4. ⚠️ Test end-to-end with OOP lecture

### Phase 2: Optimization (Do After Testing)
1. ⚠️ Simplify or remove embedding service
2. ⚠️ Update database schema
3. ⚠️ Simplify validation
4. ⚠️ Update API endpoints

### Phase 3: Polish (Do Last)
1. Remove unused code
2. Update documentation
3. Add proper error handling
4. Performance optimization

---

## Files to Delete (After Cleanup)

- `test_toc_extraction.py` - Not needed anymore
- `test_toc_regex.py` - Not needed anymore
- `test_toc_raw_text.py` - Not needed anymore
- `toc_extraction_response.txt` - Debug file
- `toc_selection_prompt.txt` - Old approach
- Possibly `app/literature/embeddings.py` - If we remove it

---

## Summary

**Core Changes**:
1. ❌ Remove book chunking
2. ✅ Keep TOC-based page selection (working!)
3. ⚠️ Simplify book selection to title-only
4. ⚠️ Simplify or remove validation
5. ⚠️ Update database schema

**Result**: Simpler, faster, more maintainable system that does exactly what's needed.
