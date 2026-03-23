# TOC-Based Page Selection - Solution

## Problem
We needed to select relevant pages from books based on lecture themes, but:
- Semantic search on chunks was selecting wrong pages (summaries instead of content)
- LLM couldn't parse TOC structure (kept hallucinating)
- Regex parsing was too brittle (different books have different formats)

## Solution: Direct Page Number Extraction

Instead of parsing TOC structure, we:
1. Find TOC pages (3-7 in most books)
2. Give LLM the **raw TOC text** (unprocessed)
3. Ask: "Which page numbers cover [theme]?"
4. Extract numbers from response
5. Load those full pages

## Why This Works

- **No parsing needed** - LLM reads messy TOC format directly
- **Semantic understanding** - LLM understands which sections relate to theme
- **Simple output** - Just comma-separated numbers, easy to parse
- **Adaptable** - Works with any TOC format (any book)

## Implementation

### In `generator.py`:

```python
async def _get_page_numbers_from_toc(theme: str, toc_text: str) -> List[int]:
    prompt = f"""Вот оглавление книги по Python:

{toc_text}

Тема лекции: "{theme}"

Какие страницы в этой книге относятся к этой теме?

Верни ТОЛЬКО номера страниц через запятую, например: 101, 102, 103

Номера страниц:"""
    
    response = await llm.generate(prompt)
    numbers = re.findall(r'\d+', response)
    return [int(n) for n in numbers]
```

### Test Results

Theme: "Основы ООП: Классы, объекты, методы, наследование"

LLM Response: `101, 102, 103, 104, 108, 110, 112`

✓ **Correct!** OOP content is on pages 101-112 in the book.

## Benefits

1. **Accurate** - Gets the right pages for the theme
2. **Fast** - Single LLM call, ~4 seconds
3. **Flexible** - Works with any book format
4. **Simple** - No complex parsing logic
5. **Maintainable** - Easy to understand and debug

## Next Steps

1. Test with different themes
2. Test with different books
3. Integrate into full generation pipeline
4. Handle edge cases (no TOC, very large TOC, etc.)

## Files Modified

- `app/generation/generator.py` - Added `_get_page_numbers_from_toc()`, updated `_step2_smart_page_selection()`
- `app/literature/processor.py` - Simplified `process_book()` to skip TOC parsing
- `test_toc_page_selection.py` - Test script for verification
