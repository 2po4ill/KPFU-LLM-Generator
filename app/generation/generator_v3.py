"""
Content Generator v3 - Optimized with TOC Caching
Implements the targeted page extraction strategy for massive performance improvement

PERFORMANCE IMPROVEMENTS:
- Initialization: Extract first 30 pages only (~4s vs 144s)
- Runtime: Use cached TOC + extract only needed pages (~5s vs 147s)
- 97% faster for subsequent lectures after initialization

ARCHITECTURE:
1. Initialization (once per book): Extract TOC, cache data
2. Runtime (per lecture): Use cached TOC + targeted page extraction
3. Content Generation: Same high-quality generation as v2
"""
import asyncio
import sys
import time
import psutil
import GPUtil
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from core.config import settings
from core.toc_cache import get_optimized_pdf_processor, get_toc_cache
from generation.generator_v2 import ContentGenerator as BaseContentGenerator

@dataclass
class OptimizedGenerationResult:
    """Result from optimized content generation"""
    success: bool
    content: str
    citations: List[Dict[str, Any]]
    sources_used: List[Dict[str, Any]]
    generation_time_seconds: float
    confidence_score: float
    step_times: Dict[str, float]
    warnings: List[str]
    errors: List[str]
    # Optimization metrics
    initialization_time: Optional[float] = None
    cached_pages_used: int = 0
    extracted_pages_count: int = 0
    toc_cache_hit: bool = False

class OptimizedContentGenerator:
    """
    Optimized Content Generator with TOC caching
    Massive performance improvement through targeted page extraction
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.model_manager = None
        self.pdf_processor = None
        self.optimized_processor = None
        self.toc_cache = None
        
        # Performance tracking
        self.initialization_times = {}
        self.generation_stats = []
    
    async def initialize(self, model_manager=None, pdf_processor=None, **kwargs):
        """Initialize generator with dependencies"""
        self.model_manager = model_manager
        self.pdf_processor = pdf_processor
        
        # Initialize optimized processor
        self.optimized_processor = await get_optimized_pdf_processor(pdf_processor)
        self.toc_cache = get_toc_cache()
        
        logger.info("Optimized content generator v3 initialized (TOC caching enabled)")
    
    async def initialize_book(self, book_path: str, book_id: str) -> Dict[str, Any]:
        """
        Initialize book for optimized processing (done once per book)
        
        Args:
            book_path: Path to PDF file
            book_id: Unique book identifier
            
        Returns:
            Dictionary with initialization result
        """
        logger.info(f"Initializing book {book_id} for optimized processing...")
        
        result = await self.optimized_processor.initialize_book(Path(book_path), book_id)
        
        if result['success']:
            if result.get('cached', False):
                logger.info(f"Book {book_id} was already initialized")
            else:
                init_time = result.get('initialization_time', 0)
                self.initialization_times[book_id] = init_time
                logger.info(f"Book {book_id} initialized in {init_time:.1f}s")
                logger.info(f"  TOC pages: {result.get('toc_pages', [])}")
                logger.info(f"  Page offset: {result.get('page_offset', 0)}")
        
        return result
    
    async def generate_lecture_optimized(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        book_ids: List[str]
    ) -> OptimizedGenerationResult:
        """
        Generate lecture content using optimized TOC caching approach
        
        Args:
            theme: Lecture theme/topic
            rpd_data: RPD data (subject, degree, profession, etc.)
            book_ids: List of book IDs provided by user
            
        Returns:
            OptimizedGenerationResult with content and optimization metrics
        """
        start_time = time.time()
        step_times = {}
        warnings = []
        errors = []
        
        # Optimization metrics
        total_cached_pages = 0
        total_extracted_pages = 0
        toc_cache_hits = 0
        
        try:
            logger.info(f"Starting optimized content generation for theme: {theme}")
            logger.info(f"Using books: {book_ids}")
            
            # Step 1: Optimized Page Selection (target: 5s vs 147s)
            step1_start = time.time()
            selected_pages = await self._step1_optimized_page_selection(theme, book_ids)
            step_times['step1_optimized_page_selection'] = time.time() - step1_start
            
            if not selected_pages:
                errors.append("No relevant pages found in provided books")
                warnings.append("Try different books or check if theme matches book content")
                return OptimizedGenerationResult(
                    success=False,
                    content="",
                    citations=[],
                    sources_used=[],
                    generation_time_seconds=time.time() - start_time,
                    confidence_score=0.0,
                    step_times=step_times,
                    warnings=warnings,
                    errors=errors
                )
            
            # Extract optimization metrics
            for page_data in selected_pages:
                if page_data.get('cached', False):
                    total_cached_pages += 1
                else:
                    total_extracted_pages += 1
            
            toc_cache_hits = len([book_id for book_id in book_ids if self.toc_cache.is_book_cached(book_id)])
            
            logger.info(f"Step 1 completed in {step_times['step1_optimized_page_selection']:.2f}s")
            logger.info(f"  Pages: {len(selected_pages)} total ({total_cached_pages} cached, {total_extracted_pages} extracted)")
            logger.info(f"  TOC cache hits: {toc_cache_hits}/{len(book_ids)} books")
            
            # Step 2: Content Generation (same as v2)
            step2_start = time.time()
            generated_content = await self._step2_content_generation(theme, rpd_data, selected_pages)
            step_times['step2_content_generation'] = time.time() - step2_start
            logger.info(f"Step 2 completed in {step_times['step2_content_generation']:.2f}s")
            
            # Step 3: Validation & Formatting (same as v2)
            step3_start = time.time()
            
            # Validate against selected pages
            confidence = await self._validate_against_pages(generated_content, selected_pages)
            logger.info(f"Validation confidence: {confidence:.2%}")
            
            if confidence < 0.5:
                warnings.append(f"Low confidence score: {confidence:.2%} - content may contain hallucinations")
            
            # Format with FGOS standards
            formatted_content, citations = await self._fgos_formatting(generated_content, rpd_data, selected_pages)
            
            step_times['step3_validation_formatting'] = time.time() - step3_start
            logger.info(f"Step 3 completed in {step_times['step3_validation_formatting']:.2f}s")
            
            total_time = time.time() - start_time
            logger.info(f"Optimized content generation completed in {total_time:.2f}s")
            
            # Get unique books used
            books_used = {}
            for page in selected_pages:
                books_used[page['book_id']] = page['book_title']
            sources_used = [{'book_id': bid, 'title': title} for bid, title in books_used.items()]
            
            # Track generation stats
            generation_stat = {
                'theme': theme,
                'total_time': total_time,
                'cached_pages': total_cached_pages,
                'extracted_pages': total_extracted_pages,
                'toc_cache_hits': toc_cache_hits,
                'timestamp': time.time()
            }
            self.generation_stats.append(generation_stat)
            
            return OptimizedGenerationResult(
                success=True,
                content=formatted_content,
                citations=citations,
                sources_used=sources_used,
                generation_time_seconds=total_time,
                confidence_score=confidence,
                step_times=step_times,
                warnings=warnings,
                errors=errors,
                cached_pages_used=total_cached_pages,
                extracted_pages_count=total_extracted_pages,
                toc_cache_hit=(toc_cache_hits > 0)
            )
            
        except Exception as e:
            logger.error(f"Error in optimized content generation: {e}", exc_info=True)
            errors.append(str(e))
            
            return OptimizedGenerationResult(
                success=False,
                content="",
                citations=[],
                sources_used=[],
                generation_time_seconds=time.time() - start_time,
                confidence_score=0.0,
                step_times=step_times,
                warnings=warnings,
                errors=errors
            )
    
    async def _step1_optimized_page_selection(
        self,
        theme: str,
        book_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Optimized page selection using cached TOC and targeted extraction
        Target: 5 seconds vs 147 seconds (97% improvement)
        """
        if self.use_mock:
            return [
                {
                    'book_id': book_ids[0],
                    'book_title': 'Mock Book',
                    'page_number': i,
                    'content': f"Mock content for {theme}",
                    'relevance_score': 1.0,
                    'cached': True
                }
                for i in range(101, 106)
            ]
        
        selected_pages = []
        
        for book_id in book_ids:
            logger.info(f"Processing book: {book_id}")
            
            # Get cached TOC data (instant if cached)
            toc_data = self.optimized_processor.get_toc_data(book_id)
            
            if not toc_data:
                logger.warning(f"Book {book_id} not initialized. Call initialize_book() first.")
                continue
            
            # Log book info for debugging
            logger.info(f"Book {book_id} TOC preview: {toc_data['toc_text'][:200]}...")
            
            logger.info(f"Using cached TOC for {book_id} ({len(toc_data['toc_text'])} chars)")
            
            # Use LLM to get page numbers (same as v2, ~3s)
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_data['toc_text'])
            
            if not book_page_numbers or book_page_numbers == [0]:
                logger.info(f"Book {book_id} is not relevant for theme '{theme}' (LLM returned 0)")
                continue
            
            logger.info(f"LLM selected book page numbers: {book_page_numbers}")
            
            # Apply offset to convert book pages to PDF pages
            pdf_page_numbers = [book_page + toc_data['page_offset'] for book_page in book_page_numbers]
            logger.info(f"Converted to PDF page numbers: {pdf_page_numbers}")
            
            # Get pages using optimized processor (cached + targeted extraction)
            pages_result = await self.optimized_processor.get_pages_for_theme(
                book_id, theme, pdf_page_numbers
            )
            
            if pages_result['success']:
                book_title = f"Book {book_id}"  # TODO: Get from metadata
                
                for page_data in pages_result['pages']:
                    page_info = {
                        'book_id': book_id,
                        'book_title': book_title,
                        'page_number': page_data['page_number'],
                        'content': page_data['text'],
                        'relevance_score': 1.0,
                        'cached': page_data.get('cached', False)
                    }
                    selected_pages.append(page_info)
                
                logger.info(f"Retrieved {len(pages_result['pages'])} pages in {pages_result['processing_time']:.1f}s")
                logger.info(f"  Cached: {pages_result['cached_pages']}, Extracted: {pages_result['extracted_pages']}")
            else:
                logger.error(f"Failed to get pages for {book_id}: {pages_result.get('error', 'Unknown error')}")
        
        logger.info(f"Selected {len(selected_pages)} pages total from {len(book_ids)} books")
        if selected_pages:
            logger.info(f"Page numbers: {sorted(set([p['page_number'] for p in selected_pages]))}")
        
        return selected_pages
    
    async def _get_page_numbers_from_toc(self, theme: str, toc_text: str) -> List[int]:
        """
        Use LLM to get page numbers from TOC
        Parse TOC with regex first, then use LLM to select relevant sections
        """
        if not self.model_manager:
            return []
        
        try:
            # Import from generator_v2 for TOC parsing
            from generation.generator_v2 import ContentGenerator as V2Generator
            
            # Create temporary v2 instance for TOC parsing
            v2_temp = V2Generator(self.use_mock)
            await v2_temp.initialize(self.model_manager, self.pdf_processor)
            
            # Use v2's correct TOC parsing logic
            page_numbers = await v2_temp._get_page_numbers_from_toc(theme, toc_text)
            
            logger.info(f"Selected {len(page_numbers)} pages from TOC: {page_numbers[:10]}{'...' if len(page_numbers) > 10 else ''}")
            
            return page_numbers
            
        except Exception as e:
            logger.error(f"Error getting page numbers from TOC: {e}")
            return []
    
    # Reuse content generation methods from v2
    async def _step2_content_generation(self, theme: str, rpd_data: Dict[str, Any], selected_pages: List[Dict[str, Any]]) -> str:
        """Optimized core-first content generation with batched processing"""
        import asyncio
        
        if self.use_mock or not self.model_manager:
            return f"# Лекция: {theme}\n\n[Mock generated content]"
        
        logger.info("Starting optimized core-first content generation...")
        logger.info(f"Processing {len(selected_pages)} pages (no limit)")
        
        # Phase 1A: Extract core concepts from ALL pages in batches
        logger.info("Phase 1A: Batched concept extraction...")
        all_concepts = await self._extract_concepts_batched(theme, selected_pages)
        
        # Phase 1A.5: Deduplicate and merge similar concepts
        logger.info("Phase 1A.5: Deduplicating concepts...")
        unique_concepts = self._deduplicate_concepts(all_concepts)
        logger.info(f"✓ Deduplicated: {len(all_concepts)} → {len(unique_concepts)} unique concepts")
        
        # Phase 1B: Elaborate concepts in batches
        logger.info("Phase 1B: Batched concept elaboration...")
        core_concepts = await self._elaborate_concepts_batched(theme, unique_concepts)
        
        # Phase 2: Generate 2 focused sections (Introduction + Conclusion only)
        logger.info("Phase 2: Generating focused sections...")
        sections = await self._generate_focused_sections(theme, core_concepts)
        
        # Combine sections with core concepts (no separate practice section)
        final_content = f"""# {theme}

{sections['introduction']}

## Основные концепции

{core_concepts}

{sections['conclusion']}"""
        
        total_words = len(final_content.split())
        logger.info(f"Optimized generation complete: {len(final_content)} chars, ~{total_words} words")
        logger.info(f"  Breakdown: Core concepts ({len(core_concepts.split())} words) + Sections ({len(sections['introduction'].split()) + len(sections['conclusion'].split())} words)")
        return final_content
    
    async def _extract_concepts_batched(self, theme: str, selected_pages: List[Dict[str, Any]]) -> List[str]:
        """Phase 1A: Extract concepts from pages in batches of 5, 2 parallel at a time"""
        import time
        
        BATCH_SIZE = 5
        PARALLEL_BATCHES = 2
        
        # Create batches of pages
        page_batches = []
        for i in range(0, len(selected_pages), BATCH_SIZE):
            batch = selected_pages[i:i+BATCH_SIZE]
            page_batches.append(batch)
        
        logger.info(f"Created {len(page_batches)} batches of {BATCH_SIZE} pages")
        logger.info(f"Processing {PARALLEL_BATCHES} batches in parallel at a time")
        
        all_concepts = []
        
        # Process batches in groups of PARALLEL_BATCHES
        for batch_group_idx in range(0, len(page_batches), PARALLEL_BATCHES):
            batch_group = page_batches[batch_group_idx:batch_group_idx+PARALLEL_BATCHES]
            
            logger.info(f"Processing batch group {batch_group_idx//PARALLEL_BATCHES + 1}/{(len(page_batches) + PARALLEL_BATCHES - 1)//PARALLEL_BATCHES}")
            
            start_time = time.time()
            
            # Create parallel tasks for this group
            tasks = []
            for batch_idx, page_batch in enumerate(batch_group):
                global_batch_num = batch_group_idx + batch_idx + 1
                task = self._extract_concepts_from_batch(theme, page_batch, global_batch_num)
                tasks.append(task)
            
            # Execute batches in parallel
            batch_results = await asyncio.gather(*tasks)
            
            # Collect concepts
            for concepts in batch_results:
                all_concepts.extend(concepts)
            
            elapsed = time.time() - start_time
            logger.info(f"  Batch group completed in {elapsed:.1f}s, total concepts so far: {len(all_concepts)}")
        
        logger.info(f"✓ Extracted {len(all_concepts)} total concepts from {len(selected_pages)} pages")
        return all_concepts
    
    async def _extract_concepts_from_batch(self, theme: str, page_batch: List[Dict[str, Any]], batch_num: int) -> List[str]:
        """Extract concepts from a single batch of pages"""
        context = "\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in page_batch
        ])
        
        page_nums = [p['page_number'] for p in page_batch]
        logger.info(f"  Batch {batch_num}: Extracting from pages {page_nums}")
        
        prompt = f"""Проанализируй материал и определи ТОЧНО 5-8 ключевых концепций для темы "{theme}".

МАТЕРИАЛ:
{context}

ТРЕБОВАНИЯ:
- Верни ТОЛЬКО короткие названия концепций
- Через запятую, без нумерации
- БЕЗ объяснений и описаний
- Только названия концепций

Пример формата: "строковые литералы, индексация, срезы, методы строк"

Концепции:"""
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 150, "num_ctx": 8192}
            )
            
            concepts_text = response.get('response', '').strip()
            # Clean up any numbering or extra formatting
            concepts_text = concepts_text.replace('\n', ',')
            concepts = [c.strip() for c in concepts_text.split(',') if c.strip()]
            # Remove any numbering like "1.", "2." etc
            concepts = [c.split('.', 1)[-1].strip() if '.' in c and c[0].isdigit() else c for c in concepts]
            
            logger.info(f"  Batch {batch_num}: Extracted {len(concepts)} concepts")
            return concepts
            
        except Exception as e:
            logger.error(f"Error extracting concepts from batch {batch_num}: {e}")
            return []
    
    def _deduplicate_concepts(self, concepts: List[str]) -> List[str]:
        """
        Deduplicate and merge similar concepts
        
        Strategy:
        1. Normalize concepts (lowercase, strip)
        2. Remove exact duplicates
        3. Merge very similar concepts (fuzzy matching)
        """
        if not concepts:
            return []
        
        # Step 1: Normalize and remove exact duplicates
        normalized = {}
        for concept in concepts:
            # Normalize: lowercase, strip whitespace
            normalized_key = concept.lower().strip()
            if normalized_key and normalized_key not in normalized:
                normalized[normalized_key] = concept
        
        unique_concepts = list(normalized.values())
        
        # Step 2: Merge very similar concepts (simple substring matching)
        merged = []
        used = set()
        
        for i, concept1 in enumerate(unique_concepts):
            if i in used:
                continue
            
            # Check if this concept is a substring of or very similar to any already merged
            is_duplicate = False
            concept1_lower = concept1.lower()
            
            for merged_concept in merged:
                merged_lower = merged_concept.lower()
                
                # If one is substring of another, they're duplicates
                if concept1_lower in merged_lower or merged_lower in concept1_lower:
                    is_duplicate = True
                    break
                
                # If they share significant words, they might be duplicates
                words1 = set(concept1_lower.split())
                words2 = set(merged_lower.split())
                
                # If 80%+ words overlap, consider them duplicates
                if len(words1) > 0 and len(words2) > 0:
                    overlap = len(words1 & words2)
                    similarity = overlap / min(len(words1), len(words2))
                    if similarity >= 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                merged.append(concept1)
                used.add(i)
        
        logger.info(f"Deduplication details:")
        logger.info(f"  Original: {len(concepts)} concepts")
        logger.info(f"  After normalization: {len(unique_concepts)} concepts")
        logger.info(f"  After merging similar: {len(merged)} concepts")
        
        return merged
    
    async def _identify_core_concepts(self, theme: str, selected_pages: List[Dict[str, Any]]) -> List[str]:
        """Phase 1A: Identify core concepts for the theme"""
        context = "\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in selected_pages[:5]  # Use top 5 pages
        ])
        
        logger.info(f"Phase 1A: Identifying concepts from {len(selected_pages[:5])} pages")
        logger.info(f"Context size: {len(context)} chars")
        
        prompt = f"""Проанализируй материал учебника и определи ТОЧНО 8 ключевых концепций для темы "{theme}".

МАТЕРИАЛ:
{context}

Верни ТОЛЬКО список концепций через запятую, без объяснений:"""
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 200, "num_ctx": 8192}
            )
            
            concepts_text = response.get('response', '').strip()
            concepts = [c.strip() for c in concepts_text.split(',') if c.strip()]
            concepts = concepts[:8]  # Ensure exactly 8 concepts
            
            logger.info(f"✓ Identified {len(concepts)} concepts:")
            for i, concept in enumerate(concepts, 1):
                logger.info(f"  {i}. {concept}")
            
            return concepts
            
        except Exception as e:
            logger.error(f"Error identifying concepts: {e}")
            return ["основные понятия", "синтаксис", "примеры", "применение"]
    
    async def _elaborate_concepts_batched(self, theme: str, all_concepts: List[str]) -> str:
        """Phase 1B: Elaborate concepts in batches of 6, 2 parallel at a time"""
        import time
        
        BATCH_SIZE = 6
        PARALLEL_BATCHES = 2
        
        logger.info(f"Elaborating {len(all_concepts)} concepts")
        logger.info(f"Batch size: {BATCH_SIZE}, Parallel: {PARALLEL_BATCHES}")
        
        # Create balanced batches - if last batch would have <3 concepts, redistribute
        concept_batches = []
        remaining_concepts = all_concepts[:]
        
        while remaining_concepts:
            # If remaining concepts <= BATCH_SIZE + 2, split evenly
            if len(remaining_concepts) <= BATCH_SIZE + 2:
                # Split remaining into 2 balanced batches if possible
                if len(remaining_concepts) > BATCH_SIZE:
                    mid = len(remaining_concepts) // 2
                    concept_batches.append(remaining_concepts[:mid])
                    concept_batches.append(remaining_concepts[mid:])
                else:
                    concept_batches.append(remaining_concepts)
                break
            else:
                # Take normal batch
                concept_batches.append(remaining_concepts[:BATCH_SIZE])
                remaining_concepts = remaining_concepts[BATCH_SIZE:]
        
        logger.info(f"Created {len(concept_batches)} balanced concept batches:")
        for i, batch in enumerate(concept_batches, 1):
            logger.info(f"  Batch {i}: {len(batch)} concepts")
        
        all_elaborations = []
        
        # Process batches in groups of PARALLEL_BATCHES
        for batch_group_idx in range(0, len(concept_batches), PARALLEL_BATCHES):
            batch_group = concept_batches[batch_group_idx:batch_group_idx+PARALLEL_BATCHES]
            
            logger.info(f"Elaborating batch group {batch_group_idx//PARALLEL_BATCHES + 1}/{(len(concept_batches) + PARALLEL_BATCHES - 1)//PARALLEL_BATCHES}")
            
            start_time = time.time()
            
            # Create parallel tasks for this group
            tasks = []
            for batch_idx, concept_batch in enumerate(batch_group):
                global_batch_num = batch_group_idx + batch_idx + 1
                task = self._elaborate_concept_batch(theme, concept_batch, global_batch_num)
                tasks.append(task)
            
            # Execute batches in parallel
            batch_results = await asyncio.gather(*tasks)
            
            # Collect elaborations
            all_elaborations.extend(batch_results)
            
            elapsed = time.time() - start_time
            logger.info(f"  Batch group completed in {elapsed:.1f}s")
        
        # Combine all elaborations
        combined = f"""**Основные концепции: {theme}**

""" + "\n\n".join(all_elaborations)
        
        total_words = len(combined.split())
        logger.info(f"✓ Combined elaborations: {total_words} words total")
        
        return combined
    
    async def _elaborate_concept_batch(self, theme: str, concept_batch: List[str], batch_num: int) -> str:
        """Elaborate a single batch of concepts"""
        logger.info(f"  Batch {batch_num}: Elaborating {len(concept_batch)} concepts")
        
        # Create list of concepts without numbering
        concepts_list = "\n".join([f"- {concept}" for concept in concept_batch])
        
        prompt = f"""Подробно объясни следующие концепции темы "{theme}":

{concepts_list}

ТРЕБОВАНИЯ:
- Объясни ТОЛЬКО эти концепции из списка
- БЕЗ вступлений типа "Я готов помочь"
- БЕЗ заключений типа "В заключении"
- БЕЗ нумерации (1., 2., 3.)
- Используй заголовки: ### Название концепции
- Сразу начинай с первой концепции
- 400-500 слов на все концепции
- Структурированное изложение с примерами

ФОРМАТ:
### Название первой концепции
[Объяснение с примерами]

### Название второй концепции
[Объяснение с примерами]

Объяснение концепций:"""
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.2, "num_predict": 3000, "num_ctx": 8192}
            )
            
            result = response.get('response', '').strip()
            word_count = len(result.split())
            logger.info(f"  Batch {batch_num}: Generated {word_count} words")
            
            return result
            
        except Exception as e:
            logger.error(f"Error elaborating batch {batch_num}: {e}")
            return f"[Ошибка генерации концепций batch {batch_num}]"
    
    async def _generate_focused_sections(self, theme: str, core_concepts: str) -> Dict[str, str]:
        """Phase 2: Generate 2 focused sections (Introduction + Conclusion only)"""
        
        logger.info(f"Phase 2: Generating 2 sections in parallel (no separate practice)")
        logger.info(f"  Core concepts size: {len(core_concepts)} chars, {len(core_concepts.split())} words")
        logger.info(f"  Note: Practice examples already embedded in core concepts")
        
        async def generate_introduction() -> str:
            prompt = f"""Напиши введение к лекции "{theme}" на основе ключевых концепций.

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

Напиши введение:
- Важность темы
- Практическое применение
- Что изучим в лекции"""
            
            try:
                llm_model = await self.model_manager.get_llm_model()
                response = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.2, "num_predict": 2500, "num_ctx": 8192}
                )
                result = response.get('response', '')
                logger.info(f"✓ Introduction generated: {len(result.split())} words")
                return result
            except Exception as e:
                logger.error(f"Error generating introduction: {e}")
                return "[Ошибка генерации введения]"
        
        async def generate_conclusion() -> str:
            prompt = f"""Напиши заключение к лекции "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

Напиши заключение:
- Резюме ключевых моментов из ЭТОЙ лекции
- Практическая ценность изученного материала
- Мотивация к дальнейшему изучению темы

ВАЖНО:
- НЕ упоминай конкретные будущие темы (функции, классы, базы данных и т.д.)
- Фокусируйся ТОЛЬКО на изученном материале
- Подчеркни практическое применение концепций из лекции"""
            
            try:
                llm_model = await self.model_manager.get_llm_model()
                response = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.2, "num_predict": 2000, "num_ctx": 8192}
                )
                result = response.get('response', '')
                logger.info(f"✓ Conclusion generated: {len(result.split())} words")
                return result
            except Exception as e:
                logger.error(f"Error generating conclusion: {e}")
                return "[Ошибка генерации заключения]"
        
        # Generate only 2 sections in parallel (no practice section)
        tasks = [
            generate_introduction(),
            generate_conclusion()
        ]
        
        sections = await asyncio.gather(*tasks)
        
        logger.info(f"✓ All sections generated")
        
        return {
            'introduction': sections[0],
            'conclusion': sections[1]
        }
    
    async def _validate_against_pages(self, generated_content: str, selected_pages: List[Dict[str, Any]]) -> float:
        """Validation (same as v2)"""
        v2_generator = BaseContentGenerator(self.use_mock)
        await v2_generator.initialize(self.model_manager, self.pdf_processor)
        
        return await v2_generator._validate_against_pages(generated_content, selected_pages)
    
    async def _fgos_formatting(self, content: str, rpd_data: Dict[str, Any], selected_pages: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """FGOS formatting (same as v2)"""
        v2_generator = BaseContentGenerator(self.use_mock)
        await v2_generator.initialize(self.model_manager, self.pdf_processor)
        
        return await v2_generator._fgos_formatting(content, rpd_data, selected_pages)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        cache_stats = self.toc_cache.get_cache_stats()
        
        if self.generation_stats:
            avg_time = sum(stat['total_time'] for stat in self.generation_stats) / len(self.generation_stats)
            avg_cached_pages = sum(stat['cached_pages'] for stat in self.generation_stats) / len(self.generation_stats)
            avg_extracted_pages = sum(stat['extracted_pages'] for stat in self.generation_stats) / len(self.generation_stats)
        else:
            avg_time = avg_cached_pages = avg_extracted_pages = 0
        
        return {
            'cache_stats': cache_stats,
            'initialization_times': self.initialization_times,
            'generation_count': len(self.generation_stats),
            'average_generation_time': avg_time,
            'average_cached_pages': avg_cached_pages,
            'average_extracted_pages': avg_extracted_pages,
            'recent_generations': self.generation_stats[-5:] if self.generation_stats else []
        }

# Global optimized generator instance
_optimized_generator = None

async def get_optimized_content_generator(
    model_manager=None,
    pdf_processor=None,
    use_mock: bool = False
) -> OptimizedContentGenerator:
    """Get global optimized content generator instance"""
    global _optimized_generator
    
    if _optimized_generator is None:
        _optimized_generator = OptimizedContentGenerator(use_mock=use_mock)
        await _optimized_generator.initialize(model_manager, pdf_processor)
    
    return _optimized_generator