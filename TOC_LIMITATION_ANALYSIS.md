# Critical Issue: TOC-Based Selection Limitation

**Date**: February 11, 2026  
**Problem**: TOC doesn't contain all relevant pages for scattered topics

---

## The Problem

### What Happened
```
Theme: "Работа со строками: форматирование, методы строк, срезы"

LLM Response:
"Увы, но в предоставленном тексте нет информации о конкретных разделах книги"
(Unfortunately, there's no information about specific book sections in the provided text)

Pages Found: 8, 12
After Expansion: 8-16
Actual String Content: Page 39+ (scattered throughout book)
```

### Root Cause

**TOC-based selection assumes**:
- Topics are in dedicated sections
- TOC lists all relevant pages
- Content is continuous

**Reality**:
- String operations mentioned throughout the book
- TOC only shows main sections
- Content is scattered (page 8, 39, 50, etc.)

---

## Why This Happens

### Book Structure Types

#### Type 1: Dedicated Sections (Works Well)
```
TOC:
- Chapter 14: ООП ............... стр. 101
- Chapter 15: Модули ............ стр. 120

Content: Pages 101-119 all about OOP
Result: ✅ TOC-based selection works perfectly
```

#### Type 2: Scattered Content (Fails)
```
TOC:
- Chapter 3: Основы ............. стр. 8
- Chapter 5: Структуры данных ... стр. 39

Content: Strings mentioned in:
- Page 8 (introduction)
- Page 15 (examples)
- Page 39 (string methods)
- Page 52 (formatting)
- Page 67 (advanced)

Result: ❌ TOC-based selection misses most content
```

---

## Evidence from Test

### LLM's Response Analysis

```
"я могу предположить, что эта тема может быть затронута в разделе 12 
'Структуры данных' или разделе 8 'Методы строк'"
```

Translation: "I can assume this topic might be covered in section 12 
'Data Structures' or section 8 'String Methods'"

**Key word**: "предположить" (assume) - LLM is guessing, not finding clear TOC entries

### What This Means

1. TOC doesn't have a dedicated "Strings" section
2. String content is part of multiple chapters
3. LLM can't find clear page numbers in TOC
4. Returns vague guesses (8, 12) instead of actual pages (39+)

---

## The Fundamental Problem

### TOC-Based Approach Limitations

**Works When**:
- ✅ Topic has dedicated chapter/section
- ✅ TOC clearly lists page numbers
- ✅ Content is continuous (pages 101-119)

**Fails When**:
- ❌ Topic is scattered across chapters
- ❌ TOC doesn't list specific topics
- ❌ Content is distributed (pages 8, 39, 52, 67)

### String Operations Case

Strings are a **fundamental concept** used throughout the book:
- Chapter 3: String basics
- Chapter 5: String methods
- Chapter 8: String formatting
- Chapter 12: Strings in data structures
- Chapter 15: String manipulation

TOC only shows chapter titles, not "all pages about strings"

---

## Solutions Discussion

### Solution 1: Hybrid TOC + Semantic Search

**Approach**: Use TOC for dedicated sections, semantic search for scattered topics

**Algorithm**:
```python
# Step 1: Try TOC-based selection
toc_pages = get_pages_from_toc(theme)

if len(toc_pages) < 5:
    # Too few pages, topic might be scattered
    # Fall back to semantic search
    semantic_pages = semantic_search_all_pages(theme)
    return semantic_pages
else:
    # Good TOC match, use it
    return expand_ranges(toc_pages)
```

**Pros**:
- ✅ Handles both dedicated and scattered content
- ✅ Uses best method for each case
- ✅ Fallback ensures we find content

**Cons**:
- ⚠️ Need to implement semantic search
- ⚠️ More complex logic
- ⚠️ Slower (semantic search on all pages)

---

### Solution 2: Full-Book Semantic Search (Original Approach)

**Approach**: Abandon TOC, use semantic search on all pages

**Algorithm**:
```python
# Load all pages
all_pages = load_book_pages()

# Generate embeddings for all pages
page_embeddings = embed(all_pages)

# Search for theme
theme_embedding = embed(theme)
similarities = cosine_similarity(theme_embedding, page_embeddings)

# Get top N pages
top_pages = get_top_n(similarities, n=15)
```

**Pros**:
- ✅ Finds all relevant pages (scattered or not)
- ✅ Works for any topic
- ✅ No TOC dependency

**Cons**:
- ⚠️ Slower (process all pages)
- ⚠️ May select summary pages instead of content
- ⚠️ This is what we moved away from!

---

### Solution 3: LLM-Based Full-Book Scan

**Approach**: Give LLM ALL pages, ask which are relevant

**Algorithm**:
```python
# Load all pages (or sample every 5th page)
all_pages = load_book_pages()

# Ask LLM to identify relevant pages
prompt = f"""
Вот все страницы книги (по 1 абзацу с каждой):

{page_samples}

Тема: "{theme}"

Какие страницы содержат информацию об этой теме?
Верни номера страниц:
"""

relevant_pages = llm.generate(prompt)
```

**Pros**:
- ✅ LLM understands content semantically
- ✅ Finds scattered content
- ✅ More accurate than embeddings

**Cons**:
- ⚠️ Very slow (need to process all pages)
- ⚠️ Context window limits (can't fit 200 pages)
- ⚠️ Expensive (long prompt)

---

### Solution 4: Two-Stage Approach (Recommended)

**Approach**: TOC first, then targeted semantic search if needed

**Algorithm**:
```python
# Stage 1: Try TOC
toc_pages = get_pages_from_toc(theme)

if len(toc_pages) >= 10:
    # Good TOC match (like OOP)
    return expand_ranges(toc_pages)

# Stage 2: TOC failed, use semantic search
# But only search in chapters LLM mentioned
llm_mentioned_sections = extract_sections_from_llm_response()
# e.g., "section 8" and "section 12"

# Get page ranges for these sections from TOC
section_pages = get_section_page_ranges(llm_mentioned_sections)
# e.g., section 8 = pages 30-45, section 12 = pages 50-70

# Semantic search only in these ranges
relevant_pages = semantic_search_in_ranges(theme, section_pages)

return relevant_pages
```

**Pros**:
- ✅ Fast for dedicated sections (TOC only)
- ✅ Accurate for scattered content (semantic search)
- ✅ Limited search scope (only mentioned sections)
- ✅ Uses LLM's understanding of book structure

**Cons**:
- ⚠️ More complex implementation
- ⚠️ Requires semantic search capability
- ⚠️ Need to parse LLM's section mentions

---

## Immediate Action: Investigate TOC Content

Let's first understand what the TOC actually contains.

### Questions to Answer

1. **What does the TOC look like?**
   - Does it have page numbers?
   - Are sections clearly labeled?
   - Is "strings" mentioned anywhere?

2. **Where is string content actually located?**
   - Page 39 (you mentioned)
   - What other pages?
   - Is it in one chapter or scattered?

3. **What did LLM see in TOC?**
   - "section 8" and "section 12"
   - What are these sections about?
   - Do they actually contain string content?

### Debug Script Needed

```python
# 1. Print actual TOC text
print("TOC CONTENT:")
print(toc_text)

# 2. Search for "строк" (string) in TOC
if "строк" in toc_text.lower():
    print("Found 'строк' in TOC")
else:
    print("'строк' NOT in TOC")

# 3. Check what's on page 39
page_39 = get_page(39)
print("PAGE 39 CONTENT:")
print(page_39[:500])

# 4. Search all pages for string content
for page_num in range(1, 200):
    page = get_page(page_num)
    if "строк" in page.lower() and "метод" in page.lower():
        print(f"Page {page_num}: Contains string methods")
```

---

## Hypothesis

### Most Likely Scenario

This is a **beginner Python book** where strings are introduced early and used throughout:

- **Chapter 3** (pages 8-20): Basic strings
- **Chapter 5** (pages 30-45): String methods
- **Chapter 8** (pages 50-70): String formatting
- **Chapter 12** (pages 80-95): Strings in data structures

TOC shows:
```
3. Основы Python ........... 8
5. Типы данных ............. 30
8. Форматирование .......... 50
12. Структуры данных ....... 80
```

LLM sees "Типы данных" (Data Types) and "Форматирование" (Formatting) and guesses these might have string content, but can't be sure.

### Why TOC-Based Selection Failed

TOC doesn't say "Strings" explicitly, so LLM can't confidently select pages.

---

## Recommended Next Steps

### Step 1: Investigate (5 minutes)

Create debug script to:
1. Print actual TOC content
2. Find where "строк" appears in book
3. Check page 39 content
4. Understand book structure

### Step 2: Decide on Approach (Discussion)

Based on investigation:
- If strings ARE in dedicated section → Fix TOC prompt
- If strings are scattered → Implement hybrid approach
- If TOC is unclear → Fall back to semantic search

### Step 3: Implement Solution

Depending on decision:
- **Option A**: Improve TOC prompt to find scattered content
- **Option B**: Implement hybrid TOC + semantic search
- **Option C**: Use semantic search for this book

---

## Questions for You

1. **Do you know the book structure?**
   - Is there a dedicated "Strings" chapter?
   - Or is string content scattered?

2. **What's on page 39?**
   - Is it string methods?
   - Part of which chapter?

3. **What should we prioritize?**
   - Speed (TOC-based, may miss content)
   - Accuracy (semantic search, slower)
   - Hybrid (best of both, more complex)

---

## Temporary Workaround

For immediate testing, we could:

1. **Manually specify page ranges** for known topics
```python
KNOWN_TOPICS = {
    "строки": [8, 15, 39, 52, 67],
    "ООП": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112],
}
```

2. **Use broader search** in TOC prompt
```python
prompt = f"""
Тема: "{theme}"

Найди ВСЕ страницы, где может быть информация об этой теме.
Включи:
- Основные разделы
- Примеры
- Упражнения
- Любые упоминания

Верни ВСЕ релевантные страницы:
"""
```

3. **Implement semantic search fallback** (quick version)
```python
if len(toc_pages) < 5:
    # TOC failed, use semantic search
    return semantic_search_pages(theme)
```

---

## Conclusion

TOC-based selection has a fundamental limitation: it only works for topics with dedicated sections.

For scattered topics like "strings" (used throughout the book), we need:
- Semantic search on all pages, OR
- Hybrid approach (TOC + semantic search), OR
- Better TOC prompt that finds scattered content

**Immediate action**: Investigate book structure to understand where string content actually is.

---

**Status**: Critical limitation identified  
**Impact**: TOC-based selection fails for scattered topics  
**Next**: Investigate book structure and decide on solution
