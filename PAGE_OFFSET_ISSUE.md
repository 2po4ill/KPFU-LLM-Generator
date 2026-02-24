# Critical Issue: Page Number Offset

## Problem Discovery

The validation revealed that the generated lecture content was 0% accurate to the provided pages. The root cause is a **page numbering offset** between:
1. **TOC page numbers** (book's internal numbering, колонтитул/footer)
2. **PDF file page numbers** (actual PDF pages)

## The Offset

**Offset = 8 pages**

| TOC Reference | Book Page (колонтитул) | Actual PDF Page | Content |
|---------------|------------------------|-----------------|---------|
| 7.4 Строки ... 36 | 36 | 44 | Strings section |
| 6.3 Выбор редактора ... 28 | 28 | 36 | Editor selection |
| 6.4 Программные файлы ... 29 | 29 | 37 | Program files |

## What Went Wrong

### Page Selection Said:
- Theme: "Работа со строками" (Strings)
- Selected pages: [36, 37, 38, 39, 41, 42] (PDF pages)

### What We Actually Got:
- PDF page 36 = Book page 28 = "6.3 Выбор редактора" (Choosing editor)
- PDF page 37 = Book page 29 = "6.4 Программные файлы" (Program files)
- PDF page 38 = Book page 30 = First programs
- PDF page 39 = Book page 31 = Hello World

**None of these are about strings!**

### What We Should Have Selected:
- PDF pages [44, 45, 46, 47, 49, 50] = Book pages [36, 37, 38, 39, 41, 42]
- This would contain the actual strings content

## Verification

Checked PDF page 44 (book page 36):
```
"7.2 Литеральные константы"
"7.4 Строки"
```

✓ This is the correct content about strings!

## Impact

1. **Page Selection**: TOC parsing returns book page numbers, but we use them as PDF page numbers
2. **Content Generation**: LLM receives wrong pages, ignores them, hallucinates content
3. **Validation**: Validates hallucinated content against wrong pages, gives false confidence

## Solution

### Option 1: Add Offset to Page Numbers
After TOC parsing, add 8 to all page numbers:
```python
pdf_page_numbers = [book_page + 8 for book_page in toc_page_numbers]
```

### Option 2: Extract Footer Page Numbers
Parse the footer (колонтитул) from each PDF page to find the book page number:
```python
def get_book_page_number(pdf_page_text):
    # Extract number from footer
    match = re.search(r'(\d+)\s*(?:Глава|Chapter|$)', last_line)
    return int(match.group(1)) if match else None
```

### Option 3: Build Page Mapping
Create a mapping during PDF extraction:
```python
page_mapping = {
    book_page: pdf_page
    for pdf_page, book_page in extracted_pages
}
```

## Recommended Fix

**Use Option 1 (Add Offset) with validation:**

1. Detect offset automatically:
   - Parse TOC to get first section and its book page
   - Find that section in PDF pages
   - Calculate offset = PDF page - book page

2. Apply offset to all TOC page numbers:
   ```python
   pdf_pages = [book_page + offset for book_page in toc_pages]
   ```

3. Validate offset is consistent across multiple sections

## Implementation

```python
def detect_page_offset(toc_text, pdf_pages):
    """Detect offset between book pages and PDF pages"""
    # Parse first clear section from TOC
    # e.g., "6.3 Выбор редактора ... 28"
    match = re.search(r'(\d+\.\d+)\s+(.+?)\s+(\d+)', toc_text)
    if not match:
        return 0
    
    section_num = match.group(1)
    section_title = match.group(2)
    book_page = int(match.group(3))
    
    # Find this section in PDF pages
    for pdf_page in pdf_pages:
        if section_num in pdf_page['text'] and section_title[:20] in pdf_page['text']:
            offset = pdf_page['page_number'] - book_page
            return offset
    
    return 0

# Usage
offset = detect_page_offset(toc_text, pages_data['pages'])
pdf_page_numbers = [book_page + offset for book_page in toc_page_numbers]
```

## Testing

After fix, verify:
1. TOC says "7.4 Строки ... 36"
2. We select PDF page 44 (36 + 8)
3. PDF page 44 contains "7.4 Строки" content
4. Generated lecture uses actual string content from book

## Priority

**CRITICAL** - This completely breaks the system's core functionality of using book content.

Without this fix:
- ❌ Wrong pages selected
- ❌ LLM ignores provided content
- ❌ Generates hallucinated content
- ❌ Validation gives false confidence

With this fix:
- ✅ Correct pages selected
- ✅ LLM receives relevant content
- ✅ Can generate accurate lectures
- ✅ Validation works properly
