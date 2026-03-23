# Generator V3 - Quick Reference

**Version**: 3.0 Final  
**Status**: ✅ Production Ready  
**Date**: February 26, 2026

---

## 🚀 Quick Start

```python
from app.generation.generator_v3 import get_optimized_content_generator

# Initialize
generator = await get_optimized_content_generator()
await generator.initialize(model_manager, pdf_processor)

# Initialize book (once per book)
await generator.initialize_book("book.pdf", "book_id")

# Generate lecture
result = await generator.generate_lecture_optimized(
    theme="Работа со строками",
    book_ids=["book_id"],
    rpd_data={}
)

print(f"Words: {len(result.content.split())}")
print(f"Time: {result.generation_time_seconds}s")
```

---

## 📊 Performance at a Glance

| Metric | Value |
|--------|-------|
| **Generation Time** | ~200s (3.3 min) |
| **Word Count** | ~2,900 words |
| **Pages Processed** | 47 pages |
| **Unique Concepts** | 32 (from 73 raw) |
| **GPU Usage** | 50-60% sustained |
| **Quality** | Professional |

---

## 🏗️ Architecture Flow

```
1. Extract Concepts (41s)
   └── 47 pages → 73 concepts

2. Deduplicate (instant)
   └── 73 → 32 unique concepts

3. Elaborate Concepts (112s)
   └── 32 concepts → 2,463 words

4. Generate Sections (45s)
   └── Intro + Conclusion → 478 words

Total: 198s, 2,941 words
```

---

## ✅ Key Features

- ✅ **Deduplication**: 56% reduction in redundant concepts
- ✅ **No Page Limits**: Processes all relevant pages
- ✅ **Clean Formatting**: ### headers, no numbering conflicts
- ✅ **Embedded Examples**: Theory + practice together
- ✅ **No Hallucinations**: Conclusion doesn't invent future topics
- ✅ **Balanced Batches**: 6+6+6+6+4+4 distribution

---

## 🔧 Key Files

| File | Purpose |
|------|---------|
| `app/generation/generator_v3.py` | Main generator implementation |
| `app/core/toc_cache.py` | TOC caching for fast page selection |
| `app/generation/generator_v2.py` | TOC parsing (used by v3) |
| `test_single_lecture_fixed.py` | Test script |

---

## 🎯 What Changed from V2

1. ✅ Added concept deduplication (73 → 32)
2. ✅ Removed 30-page limit (now 47 pages)
3. ✅ Fixed numbering (use ### headers)
4. ✅ Balanced batches (6+6+6+6+4+4)
5. ✅ Removed separate practice section
6. ✅ Fixed conclusion hallucinations

---

## 📝 Configuration

```python
# Batch sizes
BATCH_SIZE_PAGES = 5          # Pages per extraction batch
BATCH_SIZE_CONCEPTS = 6       # Concepts per elaboration batch
PARALLEL_BATCHES = 2          # Parallel processing

# Word targets
WORDS_PER_CONCEPT_BATCH = "400-500"
TOTAL_TARGET_WORDS = 2000

# LLM settings
MODEL = "llama3.1:8b"
TEMPERATURE = 0.2             # Low for factual content
NUM_CTX = 8192
```

---

## 🐛 Troubleshooting

**GPU Out of Memory**:
```python
# Reduce parallel batches
PARALLEL_BATCHES = 1
```

**Generation Too Slow**:
```python
# Increase batch sizes
BATCH_SIZE_PAGES = 7
BATCH_SIZE_CONCEPTS = 8
```

**Too Many Concepts**:
```python
# Adjust extraction prompt
CONCEPTS_PER_BATCH = "3-5"  # Instead of "5-8"
```

---

## 📈 Metrics to Monitor

```python
# Check deduplication effectiveness
original_concepts = len(all_concepts)
unique_concepts = len(deduplicated_concepts)
reduction_rate = (1 - unique_concepts/original_concepts) * 100

# Check generation efficiency
words_per_second = total_words / generation_time
gpu_utilization = peak_gpu_usage

# Check quality
validation_confidence = result.confidence_score
word_count = len(result.content.split())
```

---

## 🎓 Output Structure

```markdown
# Lecture Title

## Введение
[Context, importance, learning objectives]

## Основные концепции

### Concept 1
[Theory + Examples + Explanation]

### Concept 2
[Theory + Examples + Explanation]

...

## Заключение
[Summary, practical value, motivation]
```

---

## ✨ Best Practices

1. **Initialize book once**: Cache TOC data for reuse
2. **Monitor GPU**: Keep usage below 70% for stability
3. **Validate output**: Check word count and confidence
4. **Review deduplication**: Ensure concepts are truly unique
5. **Test with different themes**: Verify consistency

---

## 🚀 Production Deployment

```bash
# Start services
docker-compose up -d

# Run generator
python app/main.py

# Monitor logs
tail -f logs/generator.log

# Check metrics
curl http://localhost:8000/api/metrics
```

---

## 📞 Quick Help

**Issue**: Duplicate concepts in output  
**Fix**: Deduplication is working, check threshold (0.8)

**Issue**: Numbering conflicts  
**Fix**: Already fixed with ### headers

**Issue**: Hallucinated future topics  
**Fix**: Already fixed in conclusion prompt

**Issue**: Too slow  
**Fix**: Increase batch sizes or reduce parallel batches

---

**For detailed documentation, see**: `GENERATOR_V3_FINAL_ARCHITECTURE.md`
