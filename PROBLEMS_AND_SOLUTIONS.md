# Problems and Solutions Discussion

**Date**: February 11, 2026  
**Context**: Analysis of string operations test results

---

## Test Results Comparison

### OOP Test
- Pages: 101-112 (12 pages, continuous range)
- Content: Good quality, detailed examples
- Time: 51.5s
- Confidence: 50%

### String Test
- Pages: 2, 3, 8, 12, 13, 15, 16 (7 pages, scattered)
- Content: Too short, generic examples
- Time: 61.28s
- Confidence: 50%

---

## Problem 1: Content Too Short

### Observation
String lecture is significantly shorter than OOP lecture despite similar generation time.

### Root Cause
Only 7 pages selected vs 12 pages for OOP. Less source material = shorter content.

### Why This Happens
LLM only returns specific page numbers from TOC, missing pages in between sections.

**Example**:
- TOC shows: "Строки ... стр. 12"
- Next section: "Списки ... стр. 15"
- LLM returns: 12, 15
- Missing: 13, 14 (which contain string content)

---

## Problem 2: Missing Pages Between TOC Entries

### The Core Issue

**Current Behavior**:
```
TOC Entry 1: "Строки" → Page 12
TOC Entry 2: "Списки" → Page 15
LLM Returns: [12, 15]
Actual Content: Pages 12, 13, 14 all about strings
```

**What We Get**: Only pages 12 and 15  
**What We Need**: Pages 12, 13, 14 (all string content)

### Why This Is Critical

1. **Incomplete Content**: Missing 50%+ of relevant material
2. **Fragmented Examples**: Code examples split across pages
3. **Poor Quality**: Can't generate detailed lectures with partial content

---

## Solutions Discussion

### Solution 1: Range Expansion (Simple)

**Approach**: When LLM returns page numbers, expand to include pages between TOC entries.

**Algorithm**:
```python
# LLM returns: [12, 15, 20]
# Expand to ranges:
# - 12 to 14 (before next entry at 15)
# - 15 to 19 (before next entry at 20)
# - 20 to 22 (assume 2-3 pages per section)

def expand_page_ranges(page_numbers, max_gap=5):
    expanded = []
    for i, page in enumerate(page_numbers):
        expanded.append(page)
        
        # Add pages until next TOC entry
        if i < len(page_numbers) - 1:
            next_page = page_numbers[i + 1]
            # Add all pages between (but not including next TOC page)
            for p in range(page + 1, next_page):
                expanded.append(p)
        else:
            # Last entry: add 2-3 more pages
            for p in range(page + 1, page + 3):
                expanded.append(p)
    
    return expanded

# Example:
# Input: [12, 15, 20]
# Output: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```

**Pros**:
- ✅ Simple to implement
- ✅ Captures all content between sections
- ✅ Works with any book format

**Cons**:
- ⚠️ May include irrelevant pages if sections are far apart
- ⚠️ Last section has arbitrary cutoff (2-3 pages)

**Mitigation**:
- Add `max_gap` parameter (e.g., max 5 pages between entries)
- If gap > max_gap, don't expand (different topic)

---

### Solution 2: Smart Range with LLM Validation (Medium)

**Approach**: Expand ranges, then ask LLM to validate which pages are relevant.

**Algorithm**:
```python
# Step 1: Expand ranges (as above)
expanded = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]

# Step 2: Load page content
pages_content = load_pages(expanded)

# Step 3: Ask LLM to filter
prompt = f"""
Тема: "Работа со строками"

Вот содержимое страниц. Какие страницы относятся к этой теме?

{pages_content}

Верни только номера релевантных страниц: 
"""

# LLM returns: [12, 13, 14, 15, 16]
# (Filtered out 17-22 as they're about lists)
```

**Pros**:
- ✅ More accurate than blind expansion
- ✅ Filters out irrelevant pages
- ✅ Adapts to actual content

**Cons**:
- ⚠️ Requires loading all pages first (slower)
- ⚠️ Extra LLM call (adds 5-10s)
- ⚠️ More complex logic

---

### Solution 3: Two-Stage TOC Analysis (Complex)

**Approach**: First get TOC entries, then ask LLM for page ranges.

**Algorithm**:
```python
# Stage 1: Get TOC entries
prompt1 = f"""
Вот оглавление книги:
{toc_text}

Тема: "Работа со строками"

Какие РАЗДЕЛЫ относятся к этой теме? Верни название раздела и страницу:
"""

# LLM returns:
# "Строки - стр. 12"
# "Форматирование строк - стр. 15"

# Stage 2: Get page ranges
prompt2 = f"""
Вот оглавление:
{toc_text}

Раздел "Строки" начинается на странице 12.
Следующий раздел начинается на странице 15.

Сколько страниц занимает раздел "Строки"?
Верни диапазон: начало-конец
"""

# LLM returns: "12-14"
```

**Pros**:
- ✅ Most accurate
- ✅ Understands section boundaries
- ✅ Natural language reasoning

**Cons**:
- ⚠️ Two LLM calls (slower)
- ⚠️ More complex prompts
- ⚠️ May fail if TOC doesn't show section lengths

---

### Solution 4: Hybrid Approach (Recommended)

**Approach**: Combine simple expansion with smart limits.

**Algorithm**:
```python
def smart_expand_pages(toc_pages, max_pages_per_section=5, max_gap=10):
    """
    Expand TOC page numbers to include content pages
    
    Args:
        toc_pages: List of page numbers from TOC
        max_pages_per_section: Max pages to add after each TOC entry
        max_gap: Max gap between TOC entries to expand
    """
    expanded = []
    
    for i, page in enumerate(toc_pages):
        expanded.append(page)
        
        if i < len(toc_pages) - 1:
            next_page = toc_pages[i + 1]
            gap = next_page - page
            
            if gap <= max_gap:
                # Small gap: include all pages between
                for p in range(page + 1, next_page):
                    expanded.append(p)
            else:
                # Large gap: only add a few pages
                for p in range(page + 1, min(page + max_pages_per_section, next_page)):
                    expanded.append(p)
        else:
            # Last entry: add a few more pages
            for p in range(page + 1, page + max_pages_per_section):
                expanded.append(p)
    
    return sorted(set(expanded))

# Example 1: Close entries (strings)
# Input: [12, 15]
# Gap: 3 pages (< max_gap)
# Output: [12, 13, 14, 15]

# Example 2: Far entries (different topics)
# Input: [12, 50]
# Gap: 38 pages (> max_gap)
# Output: [12, 13, 14, 15, 16] (only 5 pages after 12)
```

**Pros**:
- ✅ Simple to implement
- ✅ Handles both close and far sections
- ✅ No extra LLM calls
- ✅ Configurable parameters

**Cons**:
- ⚠️ May still include some irrelevant pages
- ⚠️ Requires tuning parameters

**Recommended Parameters**:
- `max_pages_per_section`: 5 (typical section is 3-7 pages)
- `max_gap`: 10 (if sections are >10 pages apart, they're different topics)

---

## Problem 3: Content Quality

### Observation
String lecture has generic examples that don't match the book style.

**Example from generated content**:
```python
# Пример со страницы 8
name = "John"
print("Hello, {}!".format(name))
```

This looks generic, not from the actual book.

### Root Cause
Only 7 scattered pages provided to LLM. Not enough context to extract real examples.

### Solution
Fix Problem 2 first (missing pages), then content quality should improve automatically.

---

## Implementation Plan

### Phase 1: Implement Hybrid Expansion (30 minutes)

1. Add `smart_expand_pages()` function to `generator_v2.py`
2. Call it after LLM returns page numbers
3. Test with both OOP and strings themes

**Expected Results**:
- OOP: 101-112 → 101-112 (no change, already continuous)
- Strings: 12, 15 → 12, 13, 14, 15, 16, 17, 18 (expanded)

### Phase 2: Test and Tune (1 hour)

1. Run tests with different themes
2. Check if expanded pages are relevant
3. Tune `max_pages_per_section` and `max_gap` parameters

### Phase 3: Content Quality Verification (30 minutes)

1. Verify generated content is longer
2. Check if examples are from the book
3. Compare confidence scores

---

## Expected Improvements

### Before (Current)
- String pages: 7 pages (scattered)
- Content length: ~500 words
- Quality: Generic examples
- Confidence: 50%

### After (With Expansion)
- String pages: 12-15 pages (continuous)
- Content length: ~1500 words
- Quality: Real book examples
- Confidence: 60-70%

---

## Alternative: Change Prompt Strategy

### Current Prompt
```
Какие страницы в этой книге относятся к этой теме?
Номера страниц:
```

LLM returns: Individual page numbers from TOC

### Alternative Prompt
```
Какие страницы в этой книге относятся к этой теме?
Верни диапазоны страниц (например: 12-18, 25-30):
```

LLM might return: "12-18" (range instead of individual pages)

**Pros**:
- ✅ LLM understands sections span multiple pages
- ✅ More natural for book structure
- ✅ No post-processing needed

**Cons**:
- ⚠️ LLM might not understand range format
- ⚠️ Need to parse ranges (12-18 → [12,13,14,15,16,17,18])
- ⚠️ Less tested approach

**Worth trying**: Could be simpler than expansion logic

---

## Recommendation

### Immediate Action: Hybrid Expansion

Implement Solution 4 (Hybrid Approach) because:
1. Simple to implement (30 minutes)
2. No extra LLM calls (no performance hit)
3. Configurable (can tune parameters)
4. Handles edge cases (large gaps)

### Code Changes Needed

**File**: `app/generation/generator_v2.py`

**Function**: `_get_page_numbers_from_toc()`

**Change**:
```python
# After getting page numbers from LLM
page_numbers = [int(n) for n in numbers if 0 <= int(n) <= 200]

# ADD THIS: Expand to include pages between TOC entries
page_numbers = self._expand_page_ranges(
    page_numbers,
    max_pages_per_section=5,
    max_gap=10
)

return page_numbers
```

**New Function**:
```python
def _expand_page_ranges(
    self,
    toc_pages: List[int],
    max_pages_per_section: int = 5,
    max_gap: int = 10
) -> List[int]:
    """Expand TOC page numbers to include content pages"""
    # Implementation as shown in Solution 4
```

---

## Testing Plan

### Test 1: Strings (Current Problem)
- Before: [2, 3, 8, 12, 13, 15, 16]
- After: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
- Expected: Better content, longer lecture

### Test 2: OOP (Already Good)
- Before: [101-112]
- After: [101-112] (no change, already continuous)
- Expected: No regression

### Test 3: Edge Case (Far Apart Sections)
- Input: [10, 50, 90]
- After: [10, 11, 12, 13, 14, 50, 51, 52, 53, 54, 90, 91, 92, 93, 94]
- Expected: Only relevant pages, no 15-49 or 55-89

---

## Questions to Discuss

1. **Max pages per section**: 5 pages reasonable? Or should be 3? 7?
2. **Max gap**: 10 pages good threshold? Or 5? 15?
3. **Alternative prompt**: Should we try asking for ranges instead?
4. **Validation**: Should we add LLM validation after expansion?

---

## Risk Assessment

### Low Risk
- Hybrid expansion is simple and safe
- Can always revert if it doesn't work
- No breaking changes to existing code

### Medium Risk
- May include some irrelevant pages (but limited by max_gap)
- May increase generation time slightly (more pages to process)

### Mitigation
- Start with conservative parameters (max_pages_per_section=3)
- Test thoroughly before production
- Add logging to see which pages are expanded

---

## Next Steps

1. **Discuss and decide** on solution approach
2. **Implement** chosen solution
3. **Test** with multiple themes
4. **Tune** parameters based on results
5. **Document** final configuration

---

**Status**: Problem identified, solution proposed  
**Recommendation**: Implement Hybrid Expansion (Solution 4)  
**Estimated Time**: 30 minutes implementation + 1 hour testing  
**Expected Impact**: 2-3x longer content, better quality
