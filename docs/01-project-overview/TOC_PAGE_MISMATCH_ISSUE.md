# TOC Page Number Mismatch Issue

## Problem Discovery

The TOC-based page selection is selecting WRONG content because the page numbers in the TOC don't match the actual PDF page numbers.

## Evidence

### TOC Says:
- Entry 85: "self (страница 102)"
- Entry 86: "Классы (страница 102)"
- Entry 87: "Методыобъектов (страница 103)"

### Actual PDF Page 102 Contains:
- **0 mentions** of "класс" (class)
- **6 mentions** of "резервн" (backup)
- Content: "Решение задач" (Solving Problems) - Chapter 13 about backup scripts
- Last line: "94 Глава 13. Решение задач"

### What LLM Received:
```
[СТРАНИЦА 102]
...резервное копирование...backup_ver2.py...
Глава 13. Решение задач
```

### What LLM Generated:
Lecture about "решение проблем" (problem solving) instead of OOP!

## Root Cause

PDF page numbers != Book page numbers

- The TOC refers to the PRINTED book page numbers
- The PDF has additional pages (cover, preface, etc.)
- There's an offset between TOC page numbers and actual PDF pages

## Solution Options

### Option 1: Calculate Page Offset
- Find the offset between TOC pages and PDF pages
- Add offset to all TOC page numbers
- **Problem**: Offset might not be constant throughout the book

### Option 2: Search for Section Titles in Text
1. Extract section titles from TOC (e.g., "self", "Классы", "Методыобъектов")
2. Search for these titles in the actual PDF text
3. Get the PDF page numbers where titles appear
4. Use those pages for content
- **Advantage**: Accurate, works regardless of page numbering
- **Disadvantage**: Requires text search, might miss some sections

### Option 3: Use Semantic Search on TOC Titles
1. LLM selects relevant TOC entries (already working)
2. Take the TITLES from selected entries
3. Use semantic search to find chunks matching those titles
4. Get pages from matching chunks
- **Advantage**: Combines LLM understanding with accurate page finding
- **Disadvantage**: Still relies on semantic search (which we know has issues)

### Option 4: Hybrid Approach (RECOMMENDED)
1. LLM selects relevant TOC entries by title
2. Extract section titles from selected entries
3. Search for exact title matches in PDF text to find start pages
4. For each section, take N pages after the title (e.g., 5-10 pages)
5. Combine all sections' pages
- **Advantage**: Accurate, doesn't rely on TOC page numbers
- **Disadvantage**: Requires exact title matching

## Recommended Implementation

Use Option 4 (Hybrid Approach):

```python
async def _step2_smart_page_selection_v2(theme, relevant_books):
    for book in relevant_books:
        # Step 1: Get TOC
        toc_entries = get_book_toc(book_id)
        
        # Step 2: LLM selects relevant entries
        selected_toc = await _select_toc_entries_with_llm(theme, toc_entries)
        
        # Step 3: Extract section titles
        section_titles = [entry.title for entry in selected_toc]
        
        # Step 4: Find actual pages where these titles appear
        actual_pages = []
        for title in section_titles:
            # Search for title in PDF text
            pages_with_title = find_pages_with_text(book_id, title)
            if pages_with_title:
                start_page = pages_with_title[0]
                # Take 5-10 pages after title
                actual_pages.extend(range(start_page, start_page + 8))
        
        # Step 5: Load content from actual pages
        for page_num in actual_pages:
            load_page_content(page_num)
```

## Next Steps

1. Implement `find_pages_with_text()` function to search for section titles
2. Update `_step2_smart_page_selection()` to use title-based search instead of TOC page numbers
3. Test with OOP theme to verify correct pages are selected
4. Verify generated content actually uses OOP material

## Current Status

- ✅ TOC parsing works
- ✅ LLM TOC selection works (selected correct entries 85-92)
- ❌ Page number mapping is broken (TOC pages != PDF pages)
- ❌ Wrong content being sent to LLM (backup scripts instead of OOP)
- ❌ LLM generates wrong lecture (problem solving instead of OOP)
