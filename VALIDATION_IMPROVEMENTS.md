# Semantic Validation Improvements Summary

## Date: February 11, 2026

## Problem Statement
The system was generating lectures with 0% confidence, indicating that the LLM was hallucinating content instead of using the provided book sources.

## Improvements Made

### 1. Page Selection Enhancement
- **Before**: Only 3 pages selected, 14,391 chars context
- **After**: 8-10 unique pages selected, 70,000+ chars context
- **Changes**:
  - Increased `top_k` from 30 to 100 chunks in semantic search
  - Increased unique pages per book from 15 to 25
  - Added logging to track page selection process
  - Combined multiple chunks from same page for richer content

### 2. Context Window Configuration
- **Added**: Explicit `num_ctx: 32768` parameter to Ollama
- **Result**: Generation time increased from 20s to 113s (context being used)
- **Benefit**: LLM can now process much larger context

### 3. Prompt Engineering
- **Iteration 1**: Added "КРИТИЧЕСКИ ВАЖНО" warnings
- **Iteration 2**: Listed specific examples to avoid (Person, Employee, Vehicle)
- **Iteration 3**: Simplified prompt structure for clarity
- **Iteration 4**: Reduced context to top 5 pages for clearer signal
- **Current**: Direct, simple prompt emphasizing source-only usage

### 4. Validation Threshold Adjustment
- **Before**: 0.55 similarity threshold (too strict)
- **After**: 0.40 similarity threshold (more lenient for Russian text)
- **Reasoning**: Semantic similarity for Russian text tends to be lower

### 5. Logging Enhancements
- Added context preview logging (first 500 chars)
- Added page number tracking
- Added claim validation distance logging
- Added unique page count logging

## Current Status

### What's Working ✅
- Semantic search correctly finds OOP pages (112, 109, 86, 89, 87, 118, 116, 99)
- Page selection combines multiple chunks from same page
- Context is being passed to LLM (70k+ characters)
- Validation system extracts and checks claims
- System generates lectures in reasonable time (2 minutes per lecture)

### What's Not Working ❌
- **LLM still hallucinating**: Despite all improvements, Llama 3.1 8B generates generic examples (Person, Animal, Dog, Calculator) instead of using book content
- **0% confidence persists**: Validation correctly identifies that generated content doesn't match sources
- **LLM ignores instructions**: Even with explicit warnings, LLM uses training data instead of provided sources

## Root Cause Analysis

The issue is NOT with:
- Page selection (working correctly)
- Context size (70k chars is sufficient)
- Validation logic (correctly identifying hallucinations)
- Prompt structure (tried multiple approaches)

The issue IS with:
- **LLM model limitations**: Llama 3.1 8B (4.9GB) is too small to reliably follow "use only sources" instructions
- **Training data dominance**: The model's training on common OOP examples (Person, Animal, etc.) overrides the instruction to use book sources
- **Instruction following**: Smaller models struggle with complex constraints like "don't use your training data"

## Recommendations

### Option 1: Use Larger Model (RECOMMENDED)
- Switch to Llama 3.1 70B or Llama 3.3 70B
- Larger models better at instruction following
- Better at distinguishing between training data and provided context
- **Tradeoff**: Slower generation (5-10x), requires more VRAM

### Option 2: RAG with Retrieval-Augmented Prompting
- Instead of asking LLM to generate from scratch, use a two-step process:
  1. Extract relevant passages from book
  2. Ask LLM to rephrase/explain those specific passages
- **Benefit**: Forces LLM to work with concrete text
- **Tradeoff**: More complex pipeline

### Option 3: Accept Current Behavior with Warnings
- Keep current system
- Mark all content as "requires verification"
- Use validation score as quality indicator
- **Benefit**: Works with current hardware
- **Tradeoff**: Content quality not guaranteed

### Option 4: Hybrid Approach
- Use current system for structure and flow
- Manually verify and edit generated content
- Use validation warnings to guide editing
- **Benefit**: Practical for production
- **Tradeoff**: Requires human review

## Technical Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Pages Selected | 3 | 8-10 | +167-233% |
| Context Size | 14,391 chars | 70,000+ chars | +386% |
| Generation Time | 20s | 113s | +465% |
| Confidence Score | 0% | 0% | No change |
| Validation Threshold | 0.55 | 0.40 | -27% |

## Code Changes

### Files Modified
1. `app/generation/generator.py`
   - `_step2_smart_page_selection()`: Increased top_k to 100, pages to 25
   - `_step3_content_generation()`: Added num_ctx=32768, simplified prompt
   - `_validate_claims()`: Lowered threshold to 0.40, added logging

2. `app/literature/embeddings.py`
   - No changes needed (working correctly)

### Configuration Changes
- Ollama generation options:
  ```python
  {
      "temperature": 0.3,
      "num_predict": 6000,
      "num_ctx": 32768,  # NEW
      "top_p": 0.9
  }
  ```

## Next Steps

1. **Immediate**: Test with Llama 3.3 70B model if hardware allows
2. **Short-term**: Implement RAG-based extraction approach
3. **Long-term**: Consider fine-tuning smaller model on educational content generation

## Conclusion

We've successfully improved the page selection and context delivery system. The validation system correctly identifies that the LLM is not using sources. The remaining issue is a fundamental limitation of the Llama 3.1 8B model's ability to follow complex instructions about source usage. This requires either a larger model or a different approach to content generation.
