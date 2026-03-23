# Context Distribution Strategies for Parallel Processing

**Goal**: Distribute relevant pages to each section instead of sending all pages to all sections  
**Current Problem**: 5 sections × 15 pages = 75 total page processings  
**Target**: 5 sections × 3-5 relevant pages = 15-25 total page processings (67-80% reduction)

---

## 🎯 **Strategy 1: Rule-Based Disoktribution** (Simplest - 2 hours)

### **Concept**: Distribute pages based on section position and type

```python
def distribute_pages_by_rules(pages: List[Dict], outline: List[Dict]) -> Dict[int, List[Dict]]:
    """Distribute pages using simple rules"""
    
    total_pages = len(pages)
    total_sections = len(outline)
    
    section_contexts = {}
    
    for i, section_info in enumerate(outline):
        section_title = section_info['title'].lower()
        
        # Rule 1: Introduction gets first pages
        if 'введение' in section_title or i == 0:
            section_contexts[i] = pages[:4]  # First 4 pages
            
        # Rule 2: Examples/Code gets middle pages  
        elif 'пример' in section_title or 'код' in section_title:
            start = total_pages // 3
            end = start + 5
            section_contexts[i] = pages[start:end]
            
        # Rule 3: Conclusion gets last pages + first page
        elif 'заключение' in section_title or i == total_sections - 1:
            section_contexts[i] = [pages[0]] + pages[-3:]  # First + last 3
            
        # Rule 4: Core concepts get distributed middle pages
        else:
            # Distribute remaining pages across core sections
            pages_per_section = max(3, total_pages // total_sections)
            start = i * pages_per_section
            end = start + pages_per_section
            section_contexts[i] = pages[start:end]
    
    return section_contexts

# Usage:
section_contexts = distribute_pages_by_rules(selected_pages, outline)
for i, section_info in enumerate(outline):
    relevant_pages = section_contexts[i]
    context = build_context_from_pages(relevant_pages)  # 3-5 pages instead of 15
    section = await generate_section(section_info, context)
```

**Pros**: Simple, fast, no dependencies  
**Cons**: Not adaptive to content, may miss relevant pages  
**Expected Improvement**: 30-40% (good baseline)

---

## 🎯 **Strategy 2: Keyword-Based Distribution** (Moderate - 4 hours)

### **Concept**: Match section keywords with page content

```python
async def distribute_pages_by_keywords(
    pages: List[Dict], 
    outline: List[Dict]
) -> Dict[int, List[Dict]]:
    """Distribute pages based on keyword matching"""
    
    section_contexts = {}
    
    for i, section_info in enumerate(outline):
        # Extract keywords from section
        section_keywords = extract_section_keywords(section_info)
        
        # Score each page for relevance
        page_scores = []
        for page in pages:
            score = calculate_keyword_relevance(section_keywords, page['content'])
            page_scores.append((score, page))
        
        # Sort by relevance and take top 4-5 pages
        page_scores.sort(reverse=True)
        section_contexts[i] = [page for _, page in page_scores[:4]]
        
        # Always include first page for context
        if pages[0] not in section_contexts[i]:
            section_contexts[i] = [pages[0]] + section_contexts[i][:3]
    
    return section_contexts

def extract_section_keywords(section_info: Dict) -> List[str]:
    """Extract keywords from section title and key points"""
    keywords = []
    
    # From title
    title_words = section_info['title'].lower().split()
    keywords.extend(title_words)
    
    # From key points
    for point in section_info.get('points', []):
        point_words = point.lower().split()
        keywords.extend(point_words)
    
    # Add section-specific keywords
    title_lower = section_info['title'].lower()
    if 'пример' in title_lower:
        keywords.extend(['код', 'программа', 'функция', 'метод'])
    elif 'концепц' in title_lower:
        keywords.extend(['определение', 'понятие', 'принцип'])
    elif 'практик' in title_lower:
        keywords.extend(['совет', 'ошибка', 'рекомендация'])
    
    return list(set(keywords))  # Remove duplicates

def calculate_keyword_relevance(keywords: List[str], page_content: str) -> float:
    """Calculate relevance score based on keyword frequency"""
    content_lower = page_content.lower()
    
    score = 0
    for keyword in keywords:
        # Count occurrences
        count = content_lower.count(keyword)
        # Weight by keyword importance (longer keywords = more important)
        weight = len(keyword) / 10
        score += count * weight
    
    # Normalize by page length
    return score / len(page_content) * 1000
```

**Pros**: Content-aware, better relevance than rules  
**Cons**: May miss semantic relationships  
**Expected Improvement**: 40-50% (good quality)

---

## 🎯 **Strategy 3: Embedding-Based Distribution** (Advanced - 6 hours)

### **Concept**: Use semantic similarity with existing embedding model

```python
async def distribute_pages_by_embeddings(
    pages: List[Dict], 
    outline: List[Dict],
    embedding_model
) -> Dict[int, List[Dict]]:
    """Distribute pages using semantic similarity"""
    
    # Pre-compute page embeddings (cache these!)
    page_embeddings = {}
    for i, page in enumerate(pages):
        if i not in page_embeddings:  # Cache check
            page_embeddings[i] = await embedding_model.embed_text(page['content'])
    
    section_contexts = {}
    
    for i, section_info in enumerate(outline):
        # Create section query from title + key points
        section_query = f"{section_info['title']} {' '.join(section_info.get('points', []))}"
        section_embedding = await embedding_model.embed_text(section_query)
        
        # Calculate similarity scores
        page_similarities = []
        for j, page in enumerate(pages):
            similarity = cosine_similarity(section_embedding, page_embeddings[j])
            page_similarities.append((similarity, page))
        
        # Sort by similarity and take top pages
        page_similarities.sort(reverse=True)
        
        # Take top 3-4 most relevant pages
        relevant_pages = [page for _, page in page_similarities[:3]]
        
        # Always include first page for general context
        if pages[0] not in relevant_pages:
            relevant_pages = [pages[0]] + relevant_pages[:2]
        
        section_contexts[i] = relevant_pages
    
    return section_contexts

def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    import numpy as np
    
    a = np.array(embedding1)
    b = np.array(embedding2)
    
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

**Pros**: Semantic understanding, highest quality  
**Cons**: Requires embedding computation, slower  
**Expected Improvement**: 50-60% (best quality)

---

## 🎯 **Strategy 4: Hybrid Approach** (Recommended - 4 hours)

### **Concept**: Combine multiple strategies for robustness

```python
async def distribute_pages_hybrid(
    pages: List[Dict], 
    outline: List[Dict],
    embedding_model=None
) -> Dict[int, List[Dict]]:
    """Hybrid approach combining rules, keywords, and embeddings"""
    
    section_contexts = {}
    
    for i, section_info in enumerate(outline):
        candidate_pages = set()
        
        # Strategy 1: Rule-based baseline (always include)
        rule_pages = get_rule_based_pages(pages, section_info, i, len(outline))
        candidate_pages.update(rule_pages)
        
        # Strategy 2: Keyword matching (add top matches)
        keyword_pages = get_keyword_pages(pages, section_info, top_n=2)
        candidate_pages.update(keyword_pages)
        
        # Strategy 3: Embedding similarity (if available)
        if embedding_model:
            try:
                embedding_pages = await get_embedding_pages(
                    pages, section_info, embedding_model, top_n=2
                )
                candidate_pages.update(embedding_pages)
            except Exception as e:
                logger.warning(f"Embedding fallback failed: {e}")
        
        # Convert to list and limit to 4-5 pages
        final_pages = list(candidate_pages)[:5]
        
        # Ensure we have minimum pages
        if len(final_pages) < 3:
            # Fallback to rule-based distribution
            final_pages = get_rule_based_pages(pages, section_info, i, len(outline))
        
        section_contexts[i] = final_pages
    
    return section_contexts

def get_rule_based_pages(pages: List[Dict], section_info: Dict, section_idx: int, total_sections: int) -> List[Dict]:
    """Get pages using simple rules"""
    title_lower = section_info['title'].lower()
    
    if section_idx == 0:  # Introduction
        return pages[:3]
    elif section_idx == total_sections - 1:  # Conclusion
        return [pages[0]] + pages[-2:]
    elif 'пример' in title_lower or 'код' in title_lower:
        # Code examples - middle pages
        start = len(pages) // 3
        return pages[start:start+3]
    else:
        # Core content - distributed
        pages_per_section = max(2, len(pages) // total_sections)
        start = section_idx * pages_per_section
        return pages[start:start+3]

def get_keyword_pages(pages: List[Dict], section_info: Dict, top_n: int = 2) -> List[Dict]:
    """Get pages using keyword matching"""
    keywords = extract_section_keywords(section_info)
    
    page_scores = []
    for page in pages:
        score = calculate_keyword_relevance(keywords, page['content'])
        page_scores.append((score, page))
    
    page_scores.sort(reverse=True)
    return [page for _, page in page_scores[:top_n]]
```

**Pros**: Robust, fallback mechanisms, good balance  
**Cons**: More complex implementation  
**Expected Improvement**: 45-55% (reliable quality)

---

## 🚀 **Implementation Plan**

### **Phase 1: Quick Win (2 hours)**
```python
# Implement rule-based distribution
def create_context_aware_parallel_test():
    """Test with rule-based context distribution"""
    
    # Modify existing test to use distributed contexts
    section_contexts = distribute_pages_by_rules(selected_pages, outline)
    
    # Generate sections in parallel with relevant contexts
    tasks = []
    for i, section_info in enumerate(outline):
        relevant_context = build_context_from_pages(section_contexts[i])
        task = generate_section(section_info, relevant_context)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### **Phase 2: Enhanced Quality (4 hours)**
```python
# Add keyword-based refinement
def enhance_with_keywords():
    """Add keyword matching to improve relevance"""
    
    # Combine rule-based + keyword-based
    section_contexts = distribute_pages_hybrid(selected_pages, outline)
    
    # Test parallel generation with improved contexts
    # Expected: 40-50% improvement
```

### **Phase 3: Production Ready (6 hours)**
```python
# Full hybrid implementation with caching
def production_context_distribution():
    """Production-ready context distribution"""
    
    # Cache page embeddings for reuse
    # Implement fallback mechanisms
    # Add performance monitoring
    # Expected: 50-60% improvement
```

---

## 📊 **Expected Results Comparison**

| Strategy | Context Size | Implementation Time | Expected Improvement | Quality |
|----------|-------------|-------------------|-------------------|---------|
| **Current (All Pages)** | 15 pages/section | - | Baseline (215s) | High |
| **Rule-Based** | 3-4 pages/section | 2 hours | 30-40% (130-150s) | Good |
| **Keyword-Based** | 3-4 pages/section | 4 hours | 40-50% (110-130s) | Better |
| **Embedding-Based** | 3-4 pages/section | 6 hours | 50-60% (90-110s) | Best |
| **Hybrid** | 4-5 pages/section | 4 hours | 45-55% (100-120s) | Excellent |

### **Multi-Book Projection**:
- **Current**: 52 minutes for 9 lectures
- **Rule-based**: 31-36 minutes (40% improvement)
- **Hybrid**: 23-28 minutes (55% improvement)

---

## ✅ **Recommendation: Start with Rule-Based**

### **Why Rule-Based First**:
1. **Quick implementation** (2 hours)
2. **Immediate 30-40% improvement**
3. **No dependencies** on embeddings
4. **Easy to understand and debug**
5. **Foundation for hybrid approach**

### **Implementation Steps**:
1. **Modify `_step2_content_generation`** to use distributed contexts
2. **Test with rule-based distribution** 
3. **Measure performance improvement**
4. **Enhance with keywords if needed**

Would you like me to implement the rule-based context distribution first? It's the fastest path to unlocking parallel processing benefits on your hardware.

---

**Next Action**: 🎯 **Implement rule-based context distribution test**  
**Expected Time**: ⏱️ **2 hours**  
**Expected Improvement**: 📈 **30-40% faster generation**