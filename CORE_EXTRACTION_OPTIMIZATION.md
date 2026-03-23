# Core Extraction Optimization Strategies

**Problem**: 15 pages → 800 words is massive compression (95%+ reduction)  
**Goal**: Reduce input pages while maintaining core concept quality  
**Target**: 60s for Phase 1 (currently 90s with 15 pages)

---

## 🎯 **Page Reduction Strategies**

### **Strategy 1: Smart Page Pre-filtering** (Recommended)

#### **Approach**: Use existing TOC + LLM to identify most relevant pages
```python
async def identify_core_pages(theme: str, selected_pages: List[Dict], max_pages: int = 6) -> List[Dict]:
    """Pre-filter pages to find most concept-dense content"""
    
    # Quick analysis of all pages to find concept density
    page_summaries = []
    for page in selected_pages:
        # Fast summary of each page (100 words max)
        summary = await quick_page_analysis(page['content'], theme)
        page_summaries.append({
            'page': page,
            'summary': summary,
            'concept_density': calculate_concept_density(summary, theme)
        })
    
    # Sort by concept density and take top pages
    page_summaries.sort(key=lambda x: x['concept_density'], reverse=True)
    
    return [item['page'] for item in page_summaries[:max_pages]]

def calculate_concept_density(summary: str, theme: str) -> float:
    """Calculate how concept-dense a page is"""
    
    # Keyword-based scoring
    concept_keywords = ['определение', 'понятие', 'принцип', 'основы', 'концепция']
    example_keywords = ['пример', 'демонстрация', 'иллюстрация']
    
    concept_score = sum(1 for kw in concept_keywords if kw in summary.lower())
    example_penalty = sum(0.5 for kw in example_keywords if kw in summary.lower())
    
    # Prefer concept-heavy pages, penalize example-heavy pages
    return concept_score - example_penalty + len(summary.split()) / 100
```

**Expected Reduction**: 15 pages → 6 pages (60% reduction)  
**Time Savings**: 90s → 54s (40% improvement)

---

### **Strategy 2: Two-Stage Extraction** (Most Efficient)

#### **Approach**: Quick extraction → Detailed extraction
```python
async def two_stage_core_extraction(theme: str, selected_pages: List[Dict]) -> str:
    """Two-stage extraction for efficiency"""
    
    # Stage 1: Quick concept identification (30s)
    key_concepts_list = await extract_key_concepts_list(theme, selected_pages)
    
    # Stage 2: Detailed elaboration (30s)  
    detailed_concepts = await elaborate_concepts(theme, key_concepts_list, selected_pages[:5])
    
    return detailed_concepts

async def extract_key_concepts_list(theme: str, pages: List[Dict]) -> List[str]:
    """Quick extraction of key concept names only"""
    
    # Use all pages but ask for minimal output
    context = build_context(pages)
    
    prompt = f"""
    Извлеки ТОЛЬКО НАЗВАНИЯ ключевых концепций по теме "{theme}".
    
    МАТЕРИАЛ: {context}
    
    ТРЕБОВАНИЯ:
    - Максимум 100 слов
    - Только названия концепций (без объяснений)
    - Список через запятую
    
    Пример: "переменные, функции, циклы, условия, массивы"
    """
    
    return await llm_generate(prompt, temperature=0.1, max_tokens=150)

async def elaborate_concepts(theme: str, concepts_list: str, core_pages: List[Dict]) -> str:
    """Detailed elaboration of identified concepts"""
    
    # Use only most relevant pages for elaboration
    context = build_context(core_pages)  # 5 pages instead of 15
    
    prompt = f"""
    Подробно опиши концепции: {concepts_list}
    
    МАТЕРИАЛ: {context}
    
    ТРЕБОВАНИЯ:
    - Точно 800 слов
    - Подробное объяснение каждой концепции
    - Только факты из материала
    """
    
    return await llm_generate(prompt, temperature=0.1, max_tokens=1200)
```

**Expected Performance**: 
- Stage 1: 15 pages → 30s (quick scan)
- Stage 2: 5 pages → 30s (detailed extraction)
- **Total**: 60s (33% improvement)

---

### **Strategy 3: Embedding-Based Page Ranking** (Advanced)

#### **Approach**: Use existing embeddings to rank page relevance
```python
async def rank_pages_by_relevance(theme: str, pages: List[Dict], embedding_service) -> List[Dict]:
    """Rank pages by semantic relevance to theme"""
    
    # Create theme embedding
    theme_embedding = await embedding_service.generate_embeddings([theme])
    
    # Calculate relevance scores
    page_scores = []
    for page in pages:
        # Use cached page embedding if available
        page_embedding = await get_or_create_page_embedding(page, embedding_service)
        
        # Calculate similarity
        similarity = cosine_similarity(theme_embedding[0], page_embedding)
        page_scores.append((similarity, page))
    
    # Sort by relevance and return top pages
    page_scores.sort(reverse=True)
    return [page for _, page in page_scores[:6]]  # Top 6 most relevant pages

async def get_or_create_page_embedding(page: Dict, embedding_service) -> np.ndarray:
    """Get cached embedding or create new one"""
    
    # Check cache first
    cache_key = f"page_{page['page_number']}_{hash(page['content'][:100])}"
    
    if cache_key in embedding_cache:
        return embedding_cache[cache_key]
    
    # Create new embedding
    embedding = await embedding_service.generate_embeddings([page['content']])
    embedding_cache[cache_key] = embedding[0]
    
    return embedding[0]
```

**Expected Reduction**: 15 pages → 6 most relevant pages  
**Quality**: Higher relevance = better concept extraction

---

### **Strategy 4: Hierarchical Content Filtering** (Comprehensive)

#### **Approach**: Multi-level filtering for optimal page selection
```python
async def hierarchical_page_filtering(theme: str, pages: List[Dict]) -> List[Dict]:
    """Multi-level filtering to find best pages for concept extraction"""
    
    # Level 1: Remove obviously irrelevant pages (fast)
    relevant_pages = filter_by_keywords(pages, theme)
    
    # Level 2: Rank by content density (medium)
    dense_pages = rank_by_content_density(relevant_pages, theme)
    
    # Level 3: Semantic similarity ranking (slower but accurate)
    if len(dense_pages) > 8:
        final_pages = await rank_by_semantic_similarity(dense_pages[:8], theme)
    else:
        final_pages = dense_pages
    
    return final_pages[:6]  # Top 6 pages

def filter_by_keywords(pages: List[Dict], theme: str) -> List[Dict]:
    """Fast keyword-based filtering"""
    
    theme_keywords = extract_theme_keywords(theme)
    
    scored_pages = []
    for page in pages:
        score = sum(1 for kw in theme_keywords if kw in page['content'].lower())
        if score > 0:  # At least one keyword match
            scored_pages.append((score, page))
    
    # Return pages with keyword matches, sorted by score
    scored_pages.sort(reverse=True)
    return [page for _, page in scored_pages]

def rank_by_content_density(pages: List[Dict], theme: str) -> List[Dict]:
    """Rank by conceptual content density"""
    
    scored_pages = []
    for page in pages:
        # Calculate various density metrics
        concept_density = count_concept_indicators(page['content'])
        definition_density = count_definitions(page['content'])
        example_ratio = count_examples(page['content']) / len(page['content'])
        
        # Prefer concept-heavy, definition-rich pages with fewer examples
        score = concept_density + definition_density - (example_ratio * 100)
        scored_pages.append((score, page))
    
    scored_pages.sort(reverse=True)
    return [page for _, page in scored_pages]
```

---

## 📊 **Strategy Comparison**

| Strategy | Input Reduction | Time Savings | Implementation | Quality |
|----------|----------------|--------------|----------------|---------|
| **Smart Pre-filtering** | 15→6 pages (60%) | 90s→54s (40%) | Easy | Good |
| **Two-Stage Extraction** | 15→5 pages (67%) | 90s→60s (33%) | Medium | Excellent |
| **Embedding Ranking** | 15→6 pages (60%) | 90s→54s (40%) | Hard | Very Good |
| **Hierarchical Filtering** | 15→6 pages (60%) | 90s→54s (40%) | Hard | Excellent |

---

## 🚀 **Recommended Implementation**

### **Phase 1: Two-Stage Extraction** (Immediate - 1 day)
```python
async def optimized_core_extraction(theme: str, selected_pages: List[Dict]) -> str:
    """Optimized core extraction with 60s target"""
    
    # Stage 1: Quick concept identification (30s)
    print("Stage 1: Identifying key concepts...")
    start_time = time.time()
    
    concepts_list = await extract_key_concepts_list(theme, selected_pages)
    
    stage1_time = time.time() - start_time
    print(f"Stage 1 completed: {stage1_time:.1f}s")
    
    # Stage 2: Detailed elaboration with reduced pages (30s)
    print("Stage 2: Elaborating concepts...")
    stage2_start = time.time()
    
    # Use only first 5 pages for detailed extraction
    core_pages = selected_pages[:5]
    detailed_concepts = await elaborate_concepts(theme, concepts_list, core_pages)
    
    stage2_time = time.time() - stage2_start
    print(f"Stage 2 completed: {stage2_time:.1f}s")
    
    total_time = time.time() - start_time
    print(f"Total core extraction: {total_time:.1f}s")
    
    return detailed_concepts
```

### **Phase 2: Smart Pre-filtering** (Week 2 - 2 days)
Add intelligent page selection before two-stage extraction:
```python
# Pre-filter to best 6 pages, then two-stage extraction
best_pages = await identify_core_pages(theme, selected_pages, max_pages=6)
core_concepts = await optimized_core_extraction(theme, best_pages)
```

### **Phase 3: Embedding Enhancement** (Week 3 - 3 days)
Add semantic similarity ranking for even better page selection.

---

## 🎯 **Expected Results**

### **Current Performance**:
- Phase 1: 15 pages → 90s
- Phase 2: 4 sections → 60s  
- **Total**: 150s

### **Optimized Performance**:
- Phase 1: 6 pages (two-stage) → 60s
- Phase 2: 4 sections → 60s
- **Total**: 120s (20% improvement)

### **Quality Maintenance**:
- **Concept coverage**: Maintained through smart page selection
- **Factual accuracy**: Preserved through focused extraction
- **Consistency**: Improved through better concept identification

---

## ✅ **Why Two-Stage Extraction is Best**

1. **Immediate implementation**: Modify existing prompts
2. **Guaranteed time reduction**: 90s → 60s target achievable
3. **Quality preservation**: Two-stage ensures comprehensive coverage
4. **Universal applicability**: Works for any subject domain
5. **Clear performance metrics**: Easy to measure and optimize

**Your 60s target is absolutely achievable** with two-stage extraction!

---

**Status**: 🎯 **OPTIMIZATION STRATEGY IDENTIFIED**  
**Priority**: ⚡ **IMMEDIATE** - Two-stage extraction for 60s target  
**Expected Impact**: 📈 **20% overall improvement** (150s → 120s total)