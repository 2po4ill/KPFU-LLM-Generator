# Final Implementation Plan: Chunked TOC + DeepSeek + Post-processing

## Architecture

```
PDF → Extract TOC → Clean Text → Split into Chunks → DeepSeek Query (per chunk) → Parse Ranges → Add +1 Buffer → Final Pages
```

## Components

### 1. TOC Text Cleaning
```python
def clean_toc_text(toc_text: str) -> str:
    """Add spaces to stuck-together words"""
    import re
    # lowercase + uppercase → add space
    cleaned = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', toc_text)
    # letter + number → add space
    cleaned = re.sub(r'([а-яёА-ЯЁa-zA-Z])(\d)', r'\1 \2', cleaned)
    return cleaned
```

### 2. TOC Chunking
```python
def chunk_toc_by_chapters(toc_text: str, chapters_per_chunk: int = 5) -> List[str]:
    """
    Split TOC into chunks by chapter boundaries
    Each chunk contains ~5 chapters for manageable context
    """
    lines = toc_text.split('\n')
    chunks = []
    current_chunk = []
    chapter_count = 0
    
    for line in lines:
        # Detect main chapter (e.g., "7 Основы")
        if re.match(r'^\d+\s+[А-ЯЁ]', line):
            chapter_count += 1
            if chapter_count > chapters_per_chunk and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                chapter_count = 1
        
        current_chunk.append(line)
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks
```

### 3. DeepSeek Query (per chunk)
```python
async def query_chunk_with_deepseek(theme: str, chunk: str) -> str:
    """Query single TOC chunk with DeepSeek"""
    prompt = f"""Найди в предоставленном оглавлении разделы, названия которых соответствуют теме "{theme}".

Правило определения страниц для раздела:
Номер страницы, указанный после названия раздела в оглавлении, является номером его начала. Раздел занимает все страницы от начальной страницы включительно и до страницы, СООТВЕТСТВУЮЩЕЙ началу следующего раздела того же или высшего уровня.

В ответе укажи номера ВСЕХ страниц, которые занимают эти разделы. Если раздел занимает несколько страниц подряд, укажи этот диапазон через дефис (например, 36-39).

ИГНОРИРУЙ СТАНДАРТНУЮ ЛОГИКУ ОГЛАВЛЕНИЙ. Если в оглавлении для раздела указан только один номер, но по правилу выше ему принадлежит несколько страниц, все равно укажи диапазон.

Раздели информацию по разным разделам запятой.

Формат ответа: строка с числами и дефисами. Например: 36-39, 89-91

Оглавление:
{chunk}

ТОЛЬКО диапазоны через запятую:"""
    
    response = await llm_model.generate(
        model="deepseek-v3.1:671b-cloud",
        prompt=prompt,
        options={"temperature": 0.1, "num_predict": 100}
    )
    
    return response.get('response', '').strip()
```

### 4. Range Parsing
```python
def parse_page_ranges(ranges_text: str) -> List[tuple]:
    """
    Parse "36-38, 89-90" into [(36, 38), (89, 90)]
    """
    import re
    
    if not ranges_text or ranges_text == "0":
        return []
    
    ranges = []
    parts = ranges_text.split(',')
    
    for part in parts:
        part = part.strip()
        
        # Range: "36-38"
        if '-' in part:
            match = re.match(r'(\d+)-(\d+)', part)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                ranges.append((start, end))
        else:
            # Single page: "36"
            match = re.match(r'(\d+)', part)
            if match:
                page = int(match.group(1))
                ranges.append((page, page))
    
    return ranges
```

### 5. Post-processing: Add +1 Buffer
```python
def add_buffer_to_ranges(ranges: List[tuple], buffer_pages: int = 1) -> List[int]:
    """
    Add buffer pages after each range to ensure complete coverage
    
    Example:
        Input: [(36, 38), (89, 90)]
        Output: [36, 37, 38, 39, 89, 90, 91]
    
    Rationale: Sections often continue onto the next page after TOC-listed end
    """
    pages = set()
    
    for start, end in ranges:
        # Add all pages in range
        pages.update(range(start, end + 1))
        # Add buffer pages after range
        pages.update(range(end + 1, end + 1 + buffer_pages))
    
    return sorted(pages)
```

### 6. Complete Pipeline
```python
async def select_pages_from_toc(
    theme: str,
    toc_text: str,
    model_manager
) -> List[int]:
    """
    Complete pipeline: Clean → Chunk → Query → Parse → Buffer
    """
    # Step 1: Clean TOC text
    cleaned_toc = clean_toc_text(toc_text)
    
    # Step 2: Split into chunks
    chunks = chunk_toc_by_chapters(cleaned_toc, chapters_per_chunk=5)
    logger.info(f"Split TOC into {len(chunks)} chunks")
    
    # Step 3: Query each chunk with DeepSeek
    all_ranges = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Querying chunk {i+1}/{len(chunks)}")
        response = await query_chunk_with_deepseek(theme, chunk)
        logger.info(f"Chunk {i+1} response: {response}")
        
        ranges = parse_page_ranges(response)
        all_ranges.extend(ranges)
    
    # Step 4: Add +1 buffer to ensure complete coverage
    final_pages = add_buffer_to_ranges(all_ranges, buffer_pages=1)
    
    logger.info(f"Selected {len(final_pages)} pages: {final_pages}")
    
    return final_pages
```

## Example Flow

**Input:**
- Theme: "Работа со строками: форматирование, методы строк, срезы"
- TOC: Full book TOC (19 chapters)

**Processing:**
1. Clean TOC: Add spaces to stuck words
2. Chunk: Split into 4 chunks (5 chapters each)
3. Query Chunk 1 (Ch 1-5): Response = "0"
4. Query Chunk 2 (Ch 6-10): Response = "36-38"
5. Query Chunk 3 (Ch 11-15): Response = "89-90"
6. Query Chunk 4 (Ch 16-19): Response = "0"
7. Parse: [(36, 38), (89, 90)]
8. Add +1 buffer: [36, 37, 38, 39, 89, 90, 91]

**Output:** Pages [36, 37, 38, 39, 89, 90, 91] ✅

## Configuration

```python
# In app/core/config.py or generator_v2.py

TOC_CONFIG = {
    "model": "deepseek-v3.1:671b-cloud",
    "chapters_per_chunk": 5,
    "buffer_pages": 1,  # Add 1 page after each range
    "temperature": 0.1,
    "max_tokens": 100
}
```

## Academic Justification

> "To ensure comprehensive coverage of relevant content, we employ a two-stage approach: (1) DeepSeek V3 identifies relevant sections from the table of contents using semantic matching and hierarchical structure analysis, returning page ranges for each section; (2) A post-processing step adds a one-page buffer after each identified range to account for content that may extend beyond the TOC-listed boundaries. This conservative approach ensures no relevant material is omitted while maintaining precision in section selection."

## Next Steps

1. Implement all functions in `generator_v2.py`
2. Test with multiple themes
3. Validate page selection accuracy
4. Measure performance (time per chunk)
