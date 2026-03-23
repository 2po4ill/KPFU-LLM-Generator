# Llama 3.1 8B vs Gemma 3 27B - Performance Comparison

## Test Results Summary

### Configuration
- **Page Selection**: Gemma 3 27B (both tests)
- **Content Generation**: Llama 3.1 8B vs Gemma 3 27B
- **Validation**: Llama 3.1 8B vs Gemma 3 27B
- **Theme**: "Работа со строками: форматирование, методы строк, срезы"

## Performance Comparison

| Metric | Gemma 3 27B | Llama 3.1 8B | Improvement |
|--------|-------------|--------------|-------------|
| **Total Time** | 594.96s (9.9 min) | 108.23s (1.8 min) | **5.5x faster** |
| Step 1 (Page Selection) | 46.82s | 42.56s | 1.1x faster |
| Step 2 (Content Gen) | 488.68s | 53.31s | **9.2x faster** |
| Step 3 (Validation) | 59.27s | 12.36s | **4.8x faster** |
| Content Length | 1099 words | 509 words | 2.2x shorter |
| Generation Speed | 2.1 words/s | 9.5 words/s | 4.5x faster |

## Detailed Breakdown

### Step 1: Page Selection (Both use Gemma 3 27B)
- Gemma: 46.82s
- Llama: 42.56s
- Similar performance (both use same model)

### Step 2: Content Generation
**Gemma 3 27B:**
- Time: 488.68s (8.1 minutes)
- Output: 1099 words
- Speed: 2.1 words/second
- Quality: Good structure, but generic content

**Llama 3.1 8B:**
- Time: 53.31s (0.9 minutes)
- Output: 509 words
- Speed: 9.5 words/second
- Quality: Good structure, practical examples

**Winner: Llama 3.1 8B** (9.2x faster)

### Step 3: Validation
**Gemma 3 27B:**
- Claim extraction: 55.25s
- Validation: 43.17s
- Total: 59.27s

**Llama 3.1 8B:**
- Claim extraction: 8.07s
- Validation: 4.90s
- Total: 12.36s

**Winner: Llama 3.1 8B** (4.8x faster)

## Content Quality Comparison

### Gemma 3 27B Output (1099 words)
✅ Better structure with numbered sections
✅ More detailed introduction (300+ words)
✅ More code examples (10 examples)
❌ Still too short (target: 2000-2500 words)
❌ Some examples from wrong pages (89-91 about lists/tuples)
❌ Generic explanations

### Llama 3.1 8B Output (509 words)
✅ Clear structure with sections
✅ Practical examples with explanations
✅ Covers main topics (types, methods, formatting, slicing)
✅ All examples have page references
❌ Too short (target: 2000-2500 words)
❌ Hit token limit (8000 tokens)
❌ Some examples from wrong pages (89-90)

## Issues with Both Models

### 1. Content Too Short
- Gemma: 1099 words (44% of target)
- Llama: 509 words (20% of target)
- Target: 2000-2500 words
- **Root Cause**: Both hit `num_predict` token limit

### 2. Wrong Page References
- Both models reference pages 89-90
- These pages are about lists/tuples, not strings!
- **Root Cause**: Page selection picked wrong pages (section 12.8 "Ещё о строках")

### 3. Generic Content
- Both produce high-level explanations
- Not enough specific technical details from book
- Missing actual string methods from the book pages

## Recommendations

### For Performance: Use Llama 3.1 8B ✅
- 5.5x faster overall
- 9.2x faster content generation
- 4.8x faster validation
- Acceptable quality

### For Content Length: Increase Token Limit
```python
"num_predict": 15000,  # Allow ~2500 words in Russian
```

### For Content Quality: Two-Stage Generation
1. Generate outline first
2. Generate each section separately
3. Combine into final lecture

### For Page Selection: Improve Filtering
- Verify page content matches theme
- Remove pages about lists/tuples when theme is strings
- Add content-based filtering after TOC selection

## Final Configuration

```python
# Page Selection: Gemma 3 27B (better accuracy)
model="gemma3:27b"
num_predict=100

# Content Generation: Llama 3.1 8B (faster)
model="llama3.1:8b"
num_predict=15000  # Increased for longer content

# Validation: Llama 3.1 8B (faster)
model="llama3.1:8b"
num_predict=1000
```

## Expected Performance with Llama 3.1 8B

| Step | Time | Notes |
|------|------|-------|
| Page Selection | ~45s | Gemma 3 27B |
| Content Generation | ~120s | Llama 3.1 8B with 15000 tokens |
| Validation | ~15s | Llama 3.1 8B |
| **Total** | **~180s (3 min)** | **Target achieved** ✅ |

## Conclusion

**Use Llama 3.1 8B for content generation and validation:**
- 5.5x faster than Gemma 3 27B
- Acceptable quality
- Can generate full course (12 lectures) in ~36 minutes vs 2 hours

**Keep Gemma 3 27B only for page selection:**
- Better accuracy for TOC analysis
- Only 45s per lecture (acceptable)

**Next steps:**
1. ✅ Switch to Llama 3.1 8B (done)
2. ⏳ Increase token limit to 15000
3. ⏳ Test with increased limit
4. ⏳ Implement page content filtering
5. ⏳ Consider two-stage generation if needed
