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
import os
import re
import sys
import time
import psutil
import numpy as np
try:
    import GPUtil  # Optional GPU util lib (may be incompatible on newer Python)
except Exception:
    GPUtil = None
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

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


@dataclass
class ConceptCard:
    """Reusable concept artifact for downstream package generation."""
    concept: str
    normalized_concept: str
    elaboration_text: str
    source_pages: List[int]
    claims: List[Dict[str, Any]]


@dataclass
class OptimizedPackageResult:
    """Result from package generation (lecture + lab + self-check)."""
    success: bool
    lecture_content: str
    lab_content: str
    selfcheck_content: str
    moodle_questions_xml: str
    concept_cards: List[ConceptCard]
    citations: List[Dict[str, Any]]
    sources_used: List[Dict[str, Any]]
    generation_time_seconds: float
    confidence_score: float
    step_times: Dict[str, float]
    warnings: List[str]
    errors: List[str]
    review_report_content: str = ""
    cached_pages_used: int = 0
    extracted_pages_count: int = 0
    toc_cache_hit: bool = False
    presentation_slides_json: str = ""
    presentation_pptx: Optional[bytes] = None

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
        self.concept_cache: Dict[str, List[ConceptCard]] = {}
        self._last_selected_pages: List[Dict[str, Any]] = []
        self._last_presentation_assets_dir: Optional[Path] = None
        self._last_facet_sections_map: Dict[str, str] = {}
        self._last_facet_hallucination_metrics: Dict[str, Dict[str, Any]] = {}
        self._progress_callback = None
        self._last_presentation_preview: Dict[str, Any] = {}
        self._book_catalog: Dict[str, Dict[str, str]] = {}

    def set_book_catalog(self, catalog: Optional[Dict[str, Dict[str, str]]]) -> None:
        """Map book_id -> {title, url} for provenance labels."""
        self._book_catalog = dict(catalog or {})

    def _book_title_for_id(self, book_id: str) -> str:
        meta = self._book_catalog.get(book_id) or {}
        return (meta.get("title") or "").strip() or book_id

    def _format_book_for_provenance(self, book_id: str, fallback_title: str = "") -> str:
        meta = self._book_catalog.get(book_id) or {}
        title = (meta.get("title") or fallback_title or book_id or "").strip()
        url = (meta.get("url") or "").strip()
        if title and url:
            return f"{title} | {url}"
        return title or fallback_title or book_id or ""

    def set_progress_callback(self, callback) -> None:
        self._progress_callback = callback

    def _emit_progress(
        self,
        step_id: str,
        message: str,
        detail: str = "",
        *,
        status: str = "active",
        pct: Optional[float] = None,
    ) -> None:
        cb = getattr(self, "_progress_callback", None)
        if not cb:
            return
        from core.progress import progress_event

        try:
            cb(progress_event(step_id, message, detail=detail, status=status, pct=pct))
        except Exception:
            pass

    def _checkpoint(self, idx: int, total: int, title: str, extra: str = "") -> None:
        suffix = f" | {extra}" if extra else ""
        logger.info(f"[CHECKPOINT {idx}/{total}] {title}{suffix}")
        pct = (float(idx) / float(total) * 100.0) if total else None
        self._emit_progress(f"checkpoint_{idx}", title, extra, pct=pct)

    def _response_to_text(self, response: Any) -> str:
        if isinstance(response, dict):
            return str(response.get("response") or response.get("text") or "")
        if hasattr(response, "model_dump"):
            try:
                payload = response.model_dump()
                return str(payload.get("response") or payload.get("text") or "")
            except Exception:
                return ""
        if hasattr(response, "__dict__"):
            payload = dict(response.__dict__)
            return str(payload.get("response") or payload.get("text") or "")
        return ""

    def _parse_json_object_from_text(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass
        # Fallback: extract first JSON object-like block.
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                parsed = json.loads(m.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    async def _llm_generate_with_timeout(
        self,
        llm_model: Any,
        *,
        log_label: str,
        **kwargs: Any,
    ) -> Any:
        timeout = float(
            getattr(settings, "facet_section_llm_timeout_seconds", 0.0) or 0.0
        )
        if timeout <= 0:
            timeout = float(getattr(settings, "request_timeout_seconds", 300) or 300)
        logger.info("LLM start (%ss max): %s", int(timeout), log_label)
        started = time.time()
        try:
            return await asyncio.wait_for(llm_model.generate(**kwargs), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.error(
                "LLM timeout after %ss: %s",
                int(timeout),
                log_label,
            )
            raise TimeoutError(f"LLM timeout ({log_label}) after {int(timeout)}s") from e
        finally:
            logger.info("LLM done in %.1fs: %s", time.time() - started, log_label)

    async def _generate_json_object(
        self,
        prompt: str,
        options: Dict[str, Any],
        log_label: str = "json_object",
    ) -> Dict[str, Any]:
        """
        Generate structured output using client-level JSON mode when available.
        """
        llm_model = await self.model_manager.get_llm_model()
        response = None
        try:
            response = await self._llm_generate_with_timeout(
                llm_model,
                log_label=log_label,
                model=settings.llm_model,
                prompt=prompt,
                options=options,
                format="json",
            )
        except TypeError:
            # Some clients may not support the format argument.
            response = await self._llm_generate_with_timeout(
                llm_model,
                log_label=f"{log_label}:no_json_format",
                model=settings.llm_model,
                prompt=prompt,
                options=options,
            )
        text = self._response_to_text(response).strip()
        return self._parse_json_object_from_text(text)

    async def _start_llm_metrics_collection(self):
        """
        Monkey-patch llm_model.generate to collect token/time metrics.
        Returns a restore callback.
        """
        self._llm_metrics = {
            "total": {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "wall_seconds": 0.0,
            },
            "phases": {},
        }
        self._llm_metrics_phase = "unscoped"
        self._llm_metrics_restore = None
        self._llm_metrics_instrumented = False

        if not self.model_manager:
            return lambda: None

        try:
            await self.model_manager.get_llm_model()
        except Exception:
            return lambda: None

        llm_model = getattr(self.model_manager, "llm_model", None)
        if llm_model is None:
            return lambda: None
        if getattr(llm_model, "_kpfu_metrics_wrapped", False):
            return lambda: None

        original_generate = llm_model.generate
        generator_self = self

        async def wrapped_generate(*args, **kwargs):
            started = time.time()
            phase = getattr(generator_self, "_llm_metrics_phase", "unscoped")
            response = None
            try:
                response = await original_generate(*args, **kwargs)
                return response
            finally:
                elapsed = time.time() - started
                prompt_text = kwargs.get("prompt", "") or ""
                response_payload = {}
                if isinstance(response, dict):
                    response_payload = response
                elif hasattr(response, "model_dump"):
                    try:
                        response_payload = response.model_dump()
                    except Exception:
                        response_payload = {}
                elif hasattr(response, "__dict__"):
                    response_payload = dict(response.__dict__)
                response_text = ""
                if response_payload:
                    response_text = (
                        response_payload.get("response")
                        or response_payload.get("text")
                        or ""
                    )

                # Prefer provider counters; fallback to rough estimates.
                prompt_tokens = 0
                completion_tokens = 0
                if response_payload:
                    prompt_tokens = int(
                        response_payload.get("prompt_eval_count")
                        or response_payload.get("prompt_tokens")
                        or response_payload.get("input_tokens")
                        or 0
                    )
                    completion_tokens = int(
                        response_payload.get("eval_count")
                        or response_payload.get("completion_tokens")
                        or response_payload.get("output_tokens")
                        or 0
                    )
                if prompt_tokens <= 0:
                    prompt_tokens = max(1, len(prompt_text) // 4) if prompt_text else 0
                if completion_tokens <= 0:
                    completion_tokens = max(1, len(response_text) // 4) if response_text else 0
                total_tokens = prompt_tokens + completion_tokens

                phase_metrics = generator_self._llm_metrics["phases"].setdefault(
                    phase,
                    {
                        "calls": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "wall_seconds": 0.0,
                    },
                )
                for bucket in (generator_self._llm_metrics["total"], phase_metrics):
                    bucket["calls"] += 1
                    bucket["prompt_tokens"] += prompt_tokens
                    bucket["completion_tokens"] += completion_tokens
                    bucket["total_tokens"] += total_tokens
                    bucket["wall_seconds"] += elapsed

        llm_model.generate = wrapped_generate
        llm_model._kpfu_metrics_wrapped = True
        self._llm_metrics_instrumented = True

        def restore():
            if getattr(llm_model, "_kpfu_metrics_wrapped", False):
                llm_model.generate = original_generate
                llm_model._kpfu_metrics_wrapped = False

        self._llm_metrics_restore = restore
        return restore

    def _set_llm_metrics_phase(self, phase: str) -> None:
        self._llm_metrics_phase = phase

    def _finalize_llm_metrics(self, step_times: Dict[str, float]) -> None:
        metrics = getattr(self, "_llm_metrics", None) or {}
        total = metrics.get("total", {})
        step_times["llm_total_calls"] = float(total.get("calls", 0))
        step_times["llm_total_prompt_tokens"] = float(total.get("prompt_tokens", 0))
        step_times["llm_total_completion_tokens"] = float(total.get("completion_tokens", 0))
        step_times["llm_total_tokens"] = float(total.get("total_tokens", 0))
        step_times["llm_total_wall_seconds"] = float(total.get("wall_seconds", 0.0))

        for phase, bucket in metrics.get("phases", {}).items():
            prefix = f"llm_{phase}"
            step_times[f"{prefix}_calls"] = float(bucket.get("calls", 0))
            step_times[f"{prefix}_prompt_tokens"] = float(bucket.get("prompt_tokens", 0))
            step_times[f"{prefix}_completion_tokens"] = float(bucket.get("completion_tokens", 0))
            step_times[f"{prefix}_total_tokens"] = float(bucket.get("total_tokens", 0))
            step_times[f"{prefix}_wall_seconds"] = float(bucket.get("wall_seconds", 0.0))
    
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
        
        if result["success"]:
            if book_id not in self._book_catalog:
                stem = Path(book_path).stem
                self._book_catalog[book_id] = {"title": stem, "url": ""}
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
            step1_detail: Dict[str, float] = {}
            selected_pages = await self._step1_optimized_page_selection(
                theme, book_ids, step1_detail
            )
            step_times["step1_optimized_page_selection"] = time.time() - step1_start
            for k, v in step1_detail.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    step_times[str(k)] = float(v)
            
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
        book_ids: List[str],
        metrics_out: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Optimized page selection using cached TOC and targeted extraction
        Target: 5 seconds vs 147 seconds (97% improvement)
        """
        if self.use_mock:
            if metrics_out is not None:
                metrics_out["step1_toc_llm_seconds"] = 0.0
                metrics_out["step1_page_extraction_seconds"] = 0.0
                metrics_out["step1_internal_wall_seconds"] = 0.0
                metrics_out["step1_other_overhead_seconds"] = 0.0
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
        step1_inner_start = time.time()
        toc_llm_acc = 0.0
        extract_acc = 0.0
        
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
            toc_t0 = time.time()
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_data['toc_text'])
            toc_llm_acc += time.time() - toc_t0
            
            if not book_page_numbers or book_page_numbers == [0]:
                logger.info(f"Book {book_id} is not relevant for theme '{theme}' (LLM returned 0)")
                continue
            
            logger.info(f"LLM selected book page numbers: {book_page_numbers}")
            
            # Apply offset to convert book pages to PDF pages
            pdf_page_numbers = [book_page + toc_data['page_offset'] for book_page in book_page_numbers]
            logger.info(f"Converted to PDF page numbers: {pdf_page_numbers}")
            
            # Get pages using optimized processor (cached + targeted extraction)
            ext_t0 = time.time()
            pages_result = await self.optimized_processor.get_pages_for_theme(
                book_id, theme, pdf_page_numbers
            )
            extract_acc += time.time() - ext_t0
            
            if pages_result['success']:
                book_title = self._book_title_for_id(book_id)

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
        
        pre_rerank_count = len(selected_pages)
        rerank_seconds = 0.0
        if settings.semantic_page_rerank_enabled and selected_pages:
            rerank_start = time.time()
            selected_pages = await self._rerank_selected_pages_semantic(theme, selected_pages)
            rerank_seconds = time.time() - rerank_start

        logger.info(
            f"Selected {len(selected_pages)} pages total from {len(book_ids)} books "
            f"(pre-rerank={pre_rerank_count})"
        )
        if selected_pages:
            logger.info(f"Page numbers: {sorted(set([p['page_number'] for p in selected_pages]))}")
        self._last_selected_pages = list(selected_pages)
        
        if metrics_out is not None:
            wall = time.time() - step1_inner_start
            metrics_out["step1_toc_llm_seconds"] = float(toc_llm_acc)
            metrics_out["step1_page_extraction_seconds"] = float(extract_acc)
            metrics_out["step1_internal_wall_seconds"] = float(wall)
            metrics_out["step1_other_overhead_seconds"] = max(
                0.0, wall - float(toc_llm_acc) - float(extract_acc)
            )
            metrics_out["step1_pages_before_semantic_rerank"] = float(pre_rerank_count)
            metrics_out["step1_pages_after_semantic_rerank"] = float(len(selected_pages))
            metrics_out["step1_semantic_rerank_seconds"] = float(rerank_seconds)
        
        return selected_pages

    async def _rerank_selected_pages_semantic(
        self,
        theme: str,
        selected_pages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Rerank TOC-selected pages by embedding similarity to the theme.
        Keeps top-K pages globally if configured (>0).
        """
        top_k = settings.semantic_page_rerank_top_k
        if not selected_pages:
            return selected_pages
        if not self.model_manager:
            return selected_pages

        try:
            embedding_model = await self.model_manager.get_embedding_model()
            page_texts = [p.get("content", "") for p in selected_pages]
            if not any(page_texts):
                return selected_pages

            page_embeddings = embedding_model.encode(page_texts)
            query_embedding = embedding_model.encode([theme])[0]

            query_norm = float(np.linalg.norm(query_embedding))
            if query_norm <= 0:
                return selected_pages

            scored_pages = []
            for idx, page in enumerate(selected_pages):
                emb = page_embeddings[idx]
                emb_norm = float(np.linalg.norm(emb))
                if emb_norm <= 0:
                    score = -1.0
                else:
                    score = float(np.dot(query_embedding, emb) / (query_norm * emb_norm))
                page_copy = dict(page)
                page_copy["semantic_score"] = score
                scored_pages.append(page_copy)

            scored_pages.sort(
                key=lambda p: (
                    -float(p.get("semantic_score", -1.0)),
                    str(p.get("book_id", "")),
                    int(p.get("page_number", 0)),
                )
            )
            if top_k and top_k > 0:
                ranked = scored_pages[:top_k]
            else:
                ranked = scored_pages

            logger.info(
                "Semantic rerank applied: %s -> %s pages (top_k=%s)",
                len(selected_pages),
                len(ranked),
                top_k,
            )
            return ranked
        except Exception as e:
            logger.warning("Semantic page rerank failed, using TOC-selected pages: %s", e)
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
        
        # Phase 1A.6: Theme-filter deduplicated concepts (extra LLM check)
        logger.info("Phase 1A.6: Filtering concepts by theme (post-dedup)...")
        filtered_concepts = await self._filter_concepts_by_theme(theme, unique_concepts)
        logger.info(
            f"✓ Theme-filtered concepts: {len(unique_concepts)} → {len(filtered_concepts)}"
        )

        # Phase 1B: Elaborate concepts in batches
        logger.info("Phase 1B: Batched concept elaboration...")
        core_concepts = await self._elaborate_concepts_batched(theme, filtered_concepts)
        core_concepts = await self._polish_core_concepts(theme, core_concepts, {})
        
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

    async def _generate_package_lab_and_selfcheck(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        concept_cards: List[ConceptCard],
        metrics_detail: Dict[str, float],
    ) -> tuple[str, str]:
        """Generate lab and/or self-check when enabled in settings."""
        lab_content = ""
        selfcheck_content = ""
        if not settings.package_lab_enabled and not settings.package_selfcheck_enabled:
            metrics_detail["step2_lab_generation_seconds"] = 0.0
            metrics_detail["step2_selfcheck_generation_seconds"] = 0.0
            metrics_detail["step2_lab_selfcheck_parallel_wall_seconds"] = 0.0
            metrics_detail["step2_lab_enabled"] = 0.0
            metrics_detail["step2_selfcheck_enabled"] = 0.0
            return lab_content, selfcheck_content

        parallel_start = time.time()

        async def _timed_lab() -> tuple[str, float]:
            t0 = time.time()
            content = await self._generate_lab_from_cards(theme, rpd_data, concept_cards)
            return content, time.time() - t0

        async def _timed_selfcheck() -> tuple[str, float]:
            t0 = time.time()
            content = await self._generate_selfcheck_from_cards(theme, concept_cards)
            return content, time.time() - t0

        lab_sec = 0.0
        sc_sec = 0.0
        if settings.package_lab_enabled and settings.package_selfcheck_enabled:
            (lab_content, lab_sec), (selfcheck_content, sc_sec) = await asyncio.gather(
                _timed_lab(),
                _timed_selfcheck(),
            )
        elif settings.package_lab_enabled:
            lab_content, lab_sec = await _timed_lab()
        elif settings.package_selfcheck_enabled:
            selfcheck_content, sc_sec = await _timed_selfcheck()

        metrics_detail["step2_lab_generation_seconds"] = float(lab_sec)
        metrics_detail["step2_selfcheck_generation_seconds"] = float(sc_sec)
        metrics_detail["step2_lab_selfcheck_parallel_wall_seconds"] = (
            time.time() - parallel_start
        )
        metrics_detail["step2_lab_enabled"] = 1.0 if settings.package_lab_enabled else 0.0
        metrics_detail["step2_selfcheck_enabled"] = (
            1.0 if settings.package_selfcheck_enabled else 0.0
        )
        return lab_content, selfcheck_content

    async def _step2_package_generation(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> tuple[str, str, str, List[ConceptCard]]:
        """Generate lecture + optional lab + optional self-check in one concept-first pass."""
        if self.use_mock or not self.model_manager:
            lecture = f"# {theme}\n\n[Mock lecture content]"
            lab = (
                f"# Лабораторная работа: {theme}\n\n[Mock lab content]"
                if settings.package_lab_enabled
                else ""
            )
            selfcheck = (
                f"# Самопроверка: {theme}\n\n[Mock self-check content]"
                if settings.package_selfcheck_enabled
                else ""
            )
            return lecture, lab, selfcheck, []

        logger.info("Starting package generation (lecture + lab + self-check)...")
        self._current_rpd_data = rpd_data
        metrics_detail: Dict[str, float] = {}
        step2_inner_start = time.time()
        logger.info(f"Processing {len(selected_pages)} pages (single pass)")
        pipeline_mode = (settings.pipeline_mode or "claims").strip().lower()
        pipeline_mode_code = 0.0
        if pipeline_mode == "chunk_rag":
            pipeline_mode_code = 1.0
        elif pipeline_mode == "chunk_rag_direct":
            pipeline_mode_code = 2.0
        elif pipeline_mode == "facet_rag":
            pipeline_mode_code = 3.0
        metrics_detail["step2_pipeline_mode"] = pipeline_mode_code

        if pipeline_mode in {"chunk_rag_direct", "facet_rag"}:
            # Direct semantic generation path:
            # skip concept extraction and retrieve evidence chunks by theme only.
            filtered_concepts = await self._build_direct_grounded_facets(
                theme, selected_pages, rpd_data=rpd_data
            )
            facet_plan = dict(getattr(self, "_last_facet_plan", {}) or {})
            if facet_plan.get("source"):
                metrics_detail["step2_facet_source"] = {"rpd": 1.0, "llm": 2.0, "hybrid": 3.0}.get(
                    str(facet_plan.get("source")), 0.0
                )
                metrics_detail["step2_facet_rpd_subtopics_count"] = float(
                    facet_plan.get("subtopics_count", 0) or 0
                )
            self._checkpoint(1, 7, "Chunk RAG by theme", f"pages={len(selected_pages)}")
            rag_start = time.time()
            concept_claims, rag_metrics, selected_facets = await self._collect_chunk_context_for_theme(
                theme, selected_pages, filtered_concepts
            )
            if selected_facets:
                filtered_concepts = selected_facets
            metrics_detail["step2_chunk_rag_total_seconds"] = time.time() - rag_start
            for k, v in rag_metrics.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    metrics_detail[f"step2_chunk_rag_{k}"] = float(v)
            metrics_detail["step2_claim_harvesting_total_seconds"] = 0.0
            metrics_detail["step2_claim_harvesting_concepts_count"] = 0.0
            metrics_detail["step2_extract_concepts_seconds"] = 0.0
            metrics_detail["step2_dedupe_concepts_seconds"] = 0.0
            metrics_detail["step2_theme_filter_seconds"] = 0.0
            metrics_detail["step2_dedupe_and_theme_filter_seconds"] = 0.0

            self._checkpoint(2, 7, "Elaborate theme from chunks")
            elaborate_start = time.time()
            core_concepts = await self._elaborate_concepts_batched(
                theme, filtered_concepts, concept_claims
            )
            hall_by_facet = dict(getattr(self, "_last_facet_hallucination_metrics", {}) or {})
            if hall_by_facet:
                hall_rates = [
                    float(m.get("hallucination_rate", 0.0) or 0.0) for m in hall_by_facet.values()
                ]
                metrics_detail["step2_facet_hallucination_avg"] = (
                    sum(hall_rates) / len(hall_rates) if hall_rates else 0.0
                )
                metrics_detail["step2_facet_hallucination_regenerations"] = float(
                    sum(int(m.get("regenerations", 0) or 0) for m in hall_by_facet.values())
                )
                metrics_detail["step2_facet_hallucination_sections"] = float(len(hall_by_facet))
            core_concepts = await self._polish_core_concepts(theme, core_concepts, concept_claims)
            metrics_detail["step2_concept_elaboration_seconds"] = time.time() - elaborate_start

            self._checkpoint(3, 7, "Generate intro/conclusion + lecture assembly")
            lecture_sections_start = time.time()
            sections = await self._generate_focused_sections(theme, core_concepts)
            metrics_detail["step2_lecture_intro_conclusion_seconds"] = (
                time.time() - lecture_sections_start
            )

            assembly_t0 = time.time()
            lecture_content = f"""# {theme}

{sections['introduction']}

## Основные концепции

{core_concepts}

{sections['conclusion']}"""
            metrics_detail["step2_lecture_markdown_assembly_seconds"] = (
                time.time() - assembly_t0
            )

            cards_t0 = time.time()
            concept_cards = self._build_concept_cards(
                theme, filtered_concepts, core_concepts, selected_pages, concept_claims
            )
            cache_key = self._build_concept_cache_key(theme, selected_pages)
            self.concept_cache[cache_key] = concept_cards
            metrics_detail["step2_build_concept_cards_and_cache_seconds"] = time.time() - cards_t0

            self._checkpoint(
                4,
                7,
                "Generate lab + selfcheck",
                f"cards={len(concept_cards)} lab={settings.package_lab_enabled} sc={settings.package_selfcheck_enabled}",
            )
            lab_content, selfcheck_content = await self._generate_package_lab_and_selfcheck(
                theme, rpd_data, concept_cards, metrics_detail
            )
            self._checkpoint(5, 7, "Package generation step2 complete")

            metrics_detail["step2_internal_wall_seconds"] = time.time() - step2_inner_start
            _acc = (
                float(metrics_detail.get("step2_extract_concepts_seconds", 0.0))
                + float(metrics_detail.get("step2_dedupe_concepts_seconds", 0.0))
                + float(metrics_detail.get("step2_theme_filter_seconds", 0.0))
                + float(metrics_detail.get("step2_claim_harvesting_total_seconds", 0.0))
                + float(metrics_detail.get("step2_concept_elaboration_seconds", 0.0))
                + float(metrics_detail.get("step2_lecture_intro_conclusion_seconds", 0.0))
                + float(metrics_detail.get("step2_lecture_markdown_assembly_seconds", 0.0))
                + float(metrics_detail.get("step2_build_concept_cards_and_cache_seconds", 0.0))
                + float(metrics_detail.get("step2_lab_selfcheck_parallel_wall_seconds", 0.0))
            )
            metrics_detail["step2_accounted_substeps_seconds"] = _acc
            metrics_detail["step2_unaccounted_overhead_seconds"] = max(
                0.0,
                float(metrics_detail["step2_internal_wall_seconds"]) - _acc,
            )
            self._last_step2_metrics = metrics_detail
            return lecture_content, lab_content, selfcheck_content, concept_cards

        self._checkpoint(1, 7, "Extract concepts", f"pages={len(selected_pages)}")

        extract_start = time.time()
        all_concepts = await self._extract_concepts_batched(theme, selected_pages)
        metrics_detail["step2_extract_concepts_seconds"] = time.time() - extract_start

        self._checkpoint(2, 7, "Deduplicate + theme-filter concepts", f"raw={len(all_concepts)}")
        dedupe_t0 = time.time()
        unique_concepts = self._deduplicate_concepts(all_concepts)
        metrics_detail["step2_dedupe_concepts_seconds"] = time.time() - dedupe_t0

        filter_t0 = time.time()
        filtered_concepts = await self._filter_concepts_by_theme(theme, unique_concepts)
        metrics_detail["step2_theme_filter_seconds"] = time.time() - filter_t0
        metrics_detail["step2_dedupe_and_theme_filter_seconds"] = (
            float(metrics_detail["step2_dedupe_concepts_seconds"])
            + float(metrics_detail["step2_theme_filter_seconds"])
        )

        concept_claims: Dict[str, List[Dict[str, Any]]] = {}
        if pipeline_mode == "chunk_rag":
            self._checkpoint(3, 7, "Chunk RAG by concepts", f"concepts={len(filtered_concepts)}")
            rag_start = time.time()
            concept_claims, rag_metrics = await self._collect_chunk_context_for_concepts(
                theme, filtered_concepts, selected_pages
            )
            metrics_detail["step2_chunk_rag_total_seconds"] = time.time() - rag_start
            for k, v in rag_metrics.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    metrics_detail[f"step2_chunk_rag_{k}"] = float(v)
            # Keep compatibility key for downstream dashboards.
            metrics_detail["step2_claim_harvesting_total_seconds"] = 0.0
            metrics_detail["step2_claim_harvesting_concepts_count"] = float(len(filtered_concepts))
        else:
            self._checkpoint(3, 7, "Harvest claims per concept", f"concepts={len(filtered_concepts)}")
            claims_start = time.time()
            concept_claims = await self._collect_claims_for_concepts(
                theme, filtered_concepts, selected_pages
            )
            metrics_detail["step2_claim_harvesting_total_seconds"] = time.time() - claims_start
            metrics_detail["step2_claim_harvesting_concepts_count"] = float(len(filtered_concepts))

            # Add per-LLM-request perf metrics for claims harvesting (CPU/GPU/tokens).
            claim_perf = getattr(self, "_last_claim_perf_metrics", None) or {}
            for k, v in claim_perf.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    metrics_detail[f"step2_claim_perf_{k}"] = float(v)

            count = float(claim_perf.get("claim_requests_count", 0.0) or 0.0)
            if count > 0:
                tokens_total = float(claim_perf.get("tokens_total", 0.0) or 0.0)
                req_total = float(claim_perf.get("request_seconds_total", 0.0) or 0.0)
                metrics_detail["step2_claim_perf_tokens_per_request_avg"] = (
                    tokens_total / count
                )
                metrics_detail["step2_claim_perf_request_seconds_avg"] = (
                    req_total / count
                )
                if req_total > 0:
                    metrics_detail["step2_claim_perf_tokens_per_second_overall"] = (
                        tokens_total / req_total
                    )
        self._checkpoint(4, 7, "Elaborate concepts from claims")
        elaborate_start = time.time()
        core_concepts = await self._elaborate_concepts_batched(
            theme, filtered_concepts, concept_claims
        )
        core_concepts = await self._polish_core_concepts(theme, core_concepts, concept_claims)
        metrics_detail["step2_concept_elaboration_seconds"] = time.time() - elaborate_start
        self._checkpoint(5, 7, "Generate intro/conclusion + lecture assembly")
        lecture_sections_start = time.time()
        sections = await self._generate_focused_sections(theme, core_concepts)
        metrics_detail["step2_lecture_intro_conclusion_seconds"] = (
            time.time() - lecture_sections_start
        )

        assembly_t0 = time.time()
        lecture_content = f"""# {theme}

{sections['introduction']}

## Основные концепции

{core_concepts}

{sections['conclusion']}"""
        metrics_detail["step2_lecture_markdown_assembly_seconds"] = (
            time.time() - assembly_t0
        )

        cards_t0 = time.time()
        concept_cards = self._build_concept_cards(
            theme, filtered_concepts, core_concepts, selected_pages, concept_claims
        )
        cache_key = self._build_concept_cache_key(theme, selected_pages)
        self.concept_cache[cache_key] = concept_cards
        metrics_detail["step2_build_concept_cards_and_cache_seconds"] = time.time() - cards_t0

        self._checkpoint(
            6,
            7,
            "Generate lab + selfcheck",
            f"cards={len(concept_cards)} lab={settings.package_lab_enabled} sc={settings.package_selfcheck_enabled}",
        )
        lab_content, selfcheck_content = await self._generate_package_lab_and_selfcheck(
            theme, rpd_data, concept_cards, metrics_detail
        )
        self._checkpoint(7, 7, "Package generation step2 complete")

        metrics_detail["step2_internal_wall_seconds"] = time.time() - step2_inner_start
        _acc = (
            float(metrics_detail.get("step2_extract_concepts_seconds", 0.0))
            + float(metrics_detail.get("step2_dedupe_concepts_seconds", 0.0))
            + float(metrics_detail.get("step2_theme_filter_seconds", 0.0))
            + float(metrics_detail.get("step2_claim_harvesting_total_seconds", 0.0))
            + float(metrics_detail.get("step2_concept_elaboration_seconds", 0.0))
            + float(metrics_detail.get("step2_lecture_intro_conclusion_seconds", 0.0))
            + float(metrics_detail.get("step2_lecture_markdown_assembly_seconds", 0.0))
            + float(metrics_detail.get("step2_build_concept_cards_and_cache_seconds", 0.0))
            + float(metrics_detail.get("step2_lab_selfcheck_parallel_wall_seconds", 0.0))
        )
        metrics_detail["step2_accounted_substeps_seconds"] = _acc
        metrics_detail["step2_unaccounted_overhead_seconds"] = max(
            0.0,
            float(metrics_detail["step2_internal_wall_seconds"]) - _acc,
        )

        self._last_step2_metrics = metrics_detail
        return lecture_content, lab_content, selfcheck_content, concept_cards

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if not cleaned:
            return []
        if chunk_size <= 0:
            return [cleaned]
        overlap = max(0, min(overlap, max(0, chunk_size - 1)))
        chunks: List[str] = []
        step = max(1, chunk_size - overlap)
        for start in range(0, len(cleaned), step):
            part = cleaned[start:start + chunk_size].strip()
            if part:
                chunks.append(part)
            if start + chunk_size >= len(cleaned):
                break
        return chunks

    async def _collect_chunk_context_for_concepts(
        self,
        theme: str,
        concepts: List[str],
        selected_pages: List[Dict[str, Any]],
    ) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, float]]:
        """
        Build chunk-level semantic context for each concept using embeddings only.
        Returns concept_claims-compatible structure for reuse in elaboration.
        """
        metrics: Dict[str, float] = {}
        if not concepts or not selected_pages or not self.model_manager:
            return {}, metrics

        chunk_size = max(200, int(settings.chunk_rag_chunk_size_chars))
        overlap = max(0, int(settings.chunk_rag_overlap_chars))
        per_concept_top_k = max(1, int(settings.chunk_rag_top_k_chunks_per_concept))

        chunks: List[Dict[str, Any]] = []
        user_chunk_size = max(200, int(settings.user_source_chunk_size_chars))
        user_overlap = max(0, int(settings.user_source_chunk_overlap_chars))
        for page in selected_pages:
            is_priority = bool(page.get("priority_source") or page.get("user_source"))
            c_size = user_chunk_size if is_priority else chunk_size
            c_overlap = user_overlap if is_priority else overlap
            page_chunks = self._chunk_text(page.get("content", ""), c_size, c_overlap)
            for idx, chunk_text in enumerate(page_chunks):
                chunks.append(
                    {
                        "chunk_id": f'{page.get("book_id","")}_{page.get("page_number",0)}_{idx}',
                        "text": chunk_text,
                        "page": int(page.get("page_number", 0) or 0),
                        "book": str(page.get("book_title", "") or ""),
                        "priority": is_priority,
                    }
                )
        if not chunks:
            return {}, metrics

        metrics["chunks_total"] = float(len(chunks))
        emb_t0 = time.time()
        embedding_model = await self.model_manager.get_embedding_model()
        chunk_embeddings = embedding_model.encode([c["text"] for c in chunks])
        concept_norms = [self._normalize_heading(c) for c in concepts]
        concept_embeddings = embedding_model.encode([f"{theme}. {c}" for c in concepts])
        metrics["embedding_seconds"] = float(time.time() - emb_t0)

        concept_claims: Dict[str, List[Dict[str, Any]]] = {}
        selected_total = 0
        debug_ranked_cap = max(1, int(settings.chunk_rag_debug_ranked_cap))
        similarity_threshold = float(settings.chunk_rag_similarity_threshold)
        mmr_lambda = float(settings.chunk_rag_mmr_lambda)
        mmr_enabled = 0.0 < mmr_lambda <= 1.0
        priority_boost = float(settings.user_source_similarity_boost)
        reserved_priority = max(0, int(settings.user_source_reserved_chunks_per_concept))
        retrieval_debug: Dict[str, Any] = {
            "theme": theme,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "top_k_per_concept": per_concept_top_k,
            "similarity_threshold": similarity_threshold,
            "mmr_lambda": mmr_lambda,
            "mmr_enabled": mmr_enabled,
            "chunks_total": len(chunks),
            "concepts": [],
        }
        rerank_t0 = time.time()
        for c_idx, concept in enumerate(concepts):
            c_norm = concept_norms[c_idx]
            c_emb = concept_embeddings[c_idx]
            c_emb_norm = float(np.linalg.norm(c_emb))
            scored = []
            for i, chunk in enumerate(chunks):
                emb = chunk_embeddings[i]
                emb_norm = float(np.linalg.norm(emb))
                if c_emb_norm <= 0 or emb_norm <= 0:
                    sim = -1.0
                else:
                    sim = float(np.dot(c_emb, emb) / (c_emb_norm * emb_norm))
                if chunk.get("priority") and priority_boost > 0:
                    sim = min(1.0, sim + priority_boost)
                scored.append((sim, chunk))
            scored.sort(key=lambda x: (-x[0], x[1]["page"]))

            priority_scored = [item for item in scored if item[1].get("priority")]
            regular_scored = [item for item in scored if not item[1].get("priority")]
            priority_pick = priority_scored[:reserved_priority] if reserved_priority else []

            remain_k = max(0, per_concept_top_k - len(priority_pick))
            ranked_candidates = regular_scored
            if similarity_threshold >= 0.0:
                ranked_candidates = [item for item in ranked_candidates if item[0] >= similarity_threshold]
                if not ranked_candidates and regular_scored:
                    ranked_candidates = regular_scored[:]

            if mmr_enabled and len(ranked_candidates) > remain_k and remain_k > 0:
                regular_top = self._select_mmr_chunks(
                    ranked_candidates=ranked_candidates,
                    chunk_embeddings=chunk_embeddings,
                    chunk_to_index={chunk["chunk_id"]: i for i, chunk in enumerate(chunks)},
                    top_k=remain_k,
                    lambda_mult=mmr_lambda,
                )
            else:
                regular_top = ranked_candidates[:remain_k]

            top = list(priority_pick) + list(regular_top)
            seen_ids = set()
            deduped_top = []
            for score, item in top:
                cid = item.get("chunk_id")
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                deduped_top.append((score, item))
            top = deduped_top[:per_concept_top_k]

            selected_total += len(top)
            concept_claims[c_norm] = [
                {
                    "text": item["text"],
                    "page": item["page"],
                    "pages": [item["page"]],
                    "books": [item["book"]] if item.get("book") else [],
                    "similarity": float(score),
                }
                for score, item in top
            ]
            retrieval_debug["concepts"].append(
                {
                    "concept": concept,
                    "normalized_concept": c_norm,
                    "ranked_candidates_count": len(ranked_candidates),
                    "selected_count": len(top),
                    "selected": [
                        {
                            "rank": idx + 1,
                            "chunk_id": item["chunk_id"],
                            "page": item["page"],
                            "book": item["book"],
                            "similarity": float(score),
                            "text": item["text"],
                        }
                        for idx, (score, item) in enumerate(top)
                    ],
                    "ranked_preview": [
                        {
                            "rank": idx + 1,
                            "chunk_id": item["chunk_id"],
                            "page": item["page"],
                            "book": item["book"],
                            "similarity": float(score),
                            "text": item["text"],
                        }
                        for idx, (score, item) in enumerate(ranked_candidates[:debug_ranked_cap])
                    ],
                }
            )
        metrics["retrieval_seconds"] = float(time.time() - rerank_t0)
        metrics["chunks_selected_total"] = float(selected_total)
        metrics["top_k_chunks_per_concept"] = float(per_concept_top_k)
        metrics["concept_count"] = float(len(concepts))
        metrics["similarity_threshold"] = float(similarity_threshold)
        metrics["mmr_enabled"] = 1.0 if mmr_enabled else 0.0
        metrics["mmr_lambda"] = float(mmr_lambda)
        self._last_retrieval_debug = retrieval_debug
        return concept_claims, metrics

    def _select_mmr_chunks(
        self,
        ranked_candidates: List[tuple[float, Dict[str, Any]]],
        chunk_embeddings: Any,
        chunk_to_index: Dict[str, int],
        top_k: int,
        lambda_mult: float,
    ) -> List[tuple[float, Dict[str, Any]]]:
        selected: List[tuple[float, Dict[str, Any]]] = []
        remaining = ranked_candidates[:]
        while remaining and len(selected) < top_k:
            best_idx = 0
            best_score = -1e9
            for idx, (rel_score, chunk) in enumerate(remaining):
                rel = float(rel_score)
                if not selected:
                    mmr_score = rel
                else:
                    c_idx = chunk_to_index.get(chunk["chunk_id"])
                    if c_idx is None:
                        mmr_score = rel
                    else:
                        cand_emb = chunk_embeddings[c_idx]
                        cand_norm = float(np.linalg.norm(cand_emb))
                        max_sim_to_selected = 0.0
                        for _, sel_chunk in selected:
                            s_idx = chunk_to_index.get(sel_chunk["chunk_id"])
                            if s_idx is None:
                                continue
                            sel_emb = chunk_embeddings[s_idx]
                            sel_norm = float(np.linalg.norm(sel_emb))
                            if cand_norm <= 0.0 or sel_norm <= 0.0:
                                continue
                            sim = float(np.dot(cand_emb, sel_emb) / (cand_norm * sel_norm))
                            if sim > max_sim_to_selected:
                                max_sim_to_selected = sim
                        mmr_score = lambda_mult * rel - (1.0 - lambda_mult) * max_sim_to_selected
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            selected.append(remaining.pop(best_idx))
        return selected

    async def _collect_chunk_context_for_theme(
        self,
        theme: str,
        selected_pages: List[Dict[str, Any]],
        facets: Optional[List[str]] = None,
    ) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, float], List[str]]:
        """
        Direct semantic retrieval path without concept extraction.
        Retrieves chunks only against the theme query and stores them under one key.
        """
        candidate_facets = facets or await self._build_direct_grounded_facets(
            theme, selected_pages, rpd_data=getattr(self, "_current_rpd_data", None)
        )
        concept_claims, metrics = await self._collect_chunk_context_for_concepts(
            theme=theme,
            concepts=candidate_facets,
            selected_pages=selected_pages,
        )
        selected_facets, pruned_claims, adaptive = self._select_facets_with_coverage_and_budget(
            facets=candidate_facets,
            concept_claims=concept_claims,
        )
        if selected_facets:
            concept_claims = pruned_claims
            metrics["concept_count"] = float(len(selected_facets))
        else:
            metrics["concept_count"] = float(len(candidate_facets))
        for k, v in adaptive.items():
            metrics[f"facet_{k}"] = float(v)
        metrics["direct_theme_mode"] = 1.0
        return concept_claims, metrics, selected_facets

    async def _build_direct_grounded_facets(
        self,
        theme: str,
        selected_pages: List[Dict[str, Any]],
        rpd_data: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build facet headings: RPD §4.2 subtopics first, then LLM outline fallback/hybrid fill."""
        self._last_facet_plan = {"source": "llm", "theme": theme, "facets": [], "subtopics_count": 0}
        min_count = max(2, int(settings.chunk_rag_facet_min_count))
        max_count = max(min_count, int(settings.chunk_rag_facet_max_count))

        if settings.facet_rag_prefer_rpd_subtopics and rpd_data:
            from rpd.rpd_facets import resolve_facets_from_rpd

            rpd_facets, meta = resolve_facets_from_rpd(rpd_data, theme)
            if rpd_facets:
                filtered = await self._filter_direct_facets_by_theme(theme, rpd_facets[:max_count])
                if len(filtered) >= min_count:
                    self._last_facet_plan = {
                        "source": "rpd",
                        "theme": theme,
                        "facets": filtered,
                        "subtopics_count": meta.get("subtopics_count", 0),
                        "matched_theme_title": meta.get("matched_theme_title"),
                        "subtopics": meta.get("subtopics") or [],
                    }
                    logger.info(
                        "Facet plan from RPD subtopics: %s (%s facets)",
                        meta.get("matched_theme_title"),
                        len(filtered),
                    )
                    return filtered
                if filtered and settings.facet_rag_rpd_hybrid_llm_fill:
                    llm_facets = await self._build_llm_grounded_facets(
                        theme, selected_pages, max_extra=max_count - len(filtered)
                    )
                    merged = self._merge_facet_lists(filtered, llm_facets, max_count)
                    merged = await self._filter_direct_facets_by_theme(theme, merged)
                    self._last_facet_plan = {
                        "source": "hybrid",
                        "theme": theme,
                        "facets": merged,
                        "subtopics_count": meta.get("subtopics_count", 0),
                        "matched_theme_title": meta.get("matched_theme_title"),
                        "subtopics": meta.get("subtopics") or [],
                    }
                    logger.info(
                        "Facet plan hybrid RPD+LLM: rpd=%s llm_extra=%s total=%s",
                        len(filtered),
                        max(0, len(merged) - len(filtered)),
                        len(merged),
                    )
                    return merged

        llm_facets = await self._build_llm_grounded_facets(theme, selected_pages)
        self._last_facet_plan = {
            "source": "llm",
            "theme": theme,
            "facets": llm_facets,
            "subtopics_count": 0,
        }
        return llm_facets

    def _merge_facet_lists(
        self, primary: List[str], extra: List[str], max_count: int
    ) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        for facet in list(primary) + list(extra):
            norm = self._normalize_heading(facet)
            if not facet or norm in seen:
                continue
            seen.add(norm)
            out.append(facet)
            if len(out) >= max_count:
                break
        return out

    async def _build_llm_grounded_facets(
        self,
        theme: str,
        selected_pages: List[Dict[str, Any]],
        max_extra: Optional[int] = None,
    ) -> List[str]:
        """LLM outline facets from page previews (legacy direct-mode builder)."""
        fallback = [
            f"{theme}: определения и базовые принципы",
            f"{theme}: математические и теоретические основы",
            f"{theme}: алгоритмы и практическая реализация",
            f"{theme}: угрозы, ограничения и практическая ценность",
            f"{theme}: типовые примеры и разбор сценариев применения",
            f"{theme}: контрольные выводы и проверка понимания",
        ]
        min_count = max(2, int(settings.chunk_rag_facet_min_count))
        max_count = max(min_count, int(settings.chunk_rag_facet_max_count))
        if max_extra is not None:
            max_count = min(max_count, max(min_count, int(max_extra)))
        fallback = fallback[:max_count]
        if not self.model_manager or not selected_pages:
            return fallback
        try:
            llm_model = await self.model_manager.get_llm_model()
            preview_parts: List[str] = []
            for page in selected_pages[:8]:
                text = re.sub(r"\s+", " ", (page.get("content", "") or "")).strip()
                if not text:
                    continue
                preview_parts.append(f"- стр. {int(page.get('page_number', 0) or 0)}: {text[:500]}")
            if not preview_parts:
                return fallback
            prompt = f"""Сформируй структуру разделов конспекта по теме "{theme}".
Используй ТОЛЬКО опорные фрагменты ниже.

Требования:
- Верни от {min_count} до {max_count} заголовков разделов.
- Каждый заголовок: 4-10 слов, предметный, без воды.
- Заголовки на русском языке.
- Заголовки не должны дублировать друг друга.
- Без нумерации.
- Формат ответа: по одному заголовку в строке.

Опорные фрагменты:
{chr(10).join(preview_parts)}
"""
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            )
            raw = (response.get("response", "") or "").strip()
            lines = [re.sub(r"^\s*[-\d\.\)]\s*", "", line).strip() for line in raw.splitlines()]
            facets: List[str] = []
            seen = set()
            for line in lines:
                norm = self._normalize_heading(line)
                if not line or len(norm) < 6 or norm in seen:
                    continue
                if settings.chunk_rag_facet_require_russian and not self._facet_title_is_russian(line):
                    continue
                seen.add(norm)
                facets.append(line)
                if len(facets) >= max_count:
                    break
            chosen = facets if facets else fallback
            return await self._filter_direct_facets_by_theme(theme, chosen)
        except Exception:
            return await self._filter_direct_facets_by_theme(theme, fallback)

    def _facet_title_is_russian(self, facet: str) -> bool:
        """Facet headings should be Russian; drop mostly-Latin titles from source noise."""
        text = (facet or "").strip()
        if not text:
            return False
        cyrillic = len(re.findall(r"[а-яА-ЯёЁ]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))
        if cyrillic == 0:
            return False
        return latin <= cyrillic

    def _count_markdown_body_words(self, section_markdown: str) -> int:
        lines = [ln.strip() for ln in (section_markdown or "").splitlines() if ln.strip()]
        body_lines = [ln for ln in lines if not ln.startswith("#")]
        return len(" ".join(body_lines).split())

    def _strip_polish_meta_leakage(self, text: str) -> str:
        if not text:
            return text
        meta_patterns = [
            r"после\s+тщательн",
            r"я\s+удалил",
            r"я\s+предлагаю",
            r"следующую\s+верси",
            r"отредактировал\s+фрагмент",
            r"^заключение:\s*метод",
        ]
        kept: List[str] = []
        for line in text.splitlines():
            lower = line.lower().strip()
            if any(re.search(pat, lower) for pat in meta_patterns):
                continue
            kept.append(line)
        cleaned = "\n".join(kept).strip()
        return cleaned if cleaned else text

    async def _filter_direct_facets_by_theme(self, theme: str, facets: List[str]) -> List[str]:
        """Filter weakly-related facets to prevent source-structure noise."""
        from rpd.rpd_facets import facets_have_rpd_codes, sort_facets_by_subtopic_code

        if not facets:
            return facets
        if settings.chunk_rag_facet_require_russian:
            russian = [f for f in facets if self._facet_title_is_russian(f)]
            dropped = [f for f in facets if f not in russian]
            if dropped:
                logger.info(
                    "Dropped non-Russian facet titles: %s",
                    dropped[:5],
                )
            facets = russian or facets
        if not facets or not self.model_manager:
            return facets
        threshold = float(settings.chunk_rag_facet_theme_threshold)
        if threshold < 0:
            return sort_facets_by_subtopic_code(facets) if facets_have_rpd_codes(facets) else facets
        preserve_rpd_order = facets_have_rpd_codes(facets)
        try:
            emb_model = await self.model_manager.get_embedding_model()
            theme_vec = emb_model.encode([theme])[0]
            theme_norm = float(np.linalg.norm(theme_vec))
            sim_by_facet: Dict[str, float] = {}
            for facet in facets:
                f_vec = emb_model.encode([f"{theme}. {facet}"])[0]
                f_norm = float(np.linalg.norm(f_vec))
                if theme_norm <= 0.0 or f_norm <= 0.0:
                    sim = -1.0
                else:
                    sim = float(np.dot(theme_vec, f_vec) / (theme_norm * f_norm))
                sim_by_facet[facet] = sim
            if preserve_rpd_order:
                kept = [f for f in facets if sim_by_facet.get(f, -1.0) >= threshold]
                if not kept:
                    kept = facets[: max(2, min(len(facets), 3))]
                return sort_facets_by_subtopic_code(kept)
            scored = sorted(
                ((sim_by_facet[f], f) for f in facets),
                key=lambda x: -x[0],
            )
            kept = [facet for sim, facet in scored if sim >= threshold]
            if kept:
                return kept
            return [facet for _, facet in scored[: max(2, min(len(scored), 3))]]
        except Exception:
            return sort_facets_by_subtopic_code(facets) if preserve_rpd_order else facets

    def _select_facets_with_coverage_and_budget(
        self,
        facets: List[str],
        concept_claims: Dict[str, List[Dict[str, Any]]],
    ) -> tuple[List[str], Dict[str, List[Dict[str, Any]]], Dict[str, float]]:
        """
        Adaptive facet selector:
        - lower bound: coverage-driven (minimum unique evidence coverage)
        - upper bound: budget-aware (strict token caps)
        """
        from rpd.rpd_facets import facets_have_rpd_codes, sort_facets_by_subtopic_code

        if not facets:
            return [], concept_claims, {}

        min_count = max(1, int(settings.chunk_rag_facet_min_count))
        max_count = max(min_count, int(settings.chunk_rag_facet_max_count))
        target_tokens = max(1, int(settings.chunk_rag_body_target_tokens))
        max_tokens = max(target_tokens, int(settings.chunk_rag_body_max_tokens))
        per_facet_tokens = max(1, int(settings.chunk_rag_estimated_tokens_per_facet))
        coverage_min = float(settings.chunk_rag_facet_coverage_min)
        min_gain = float(settings.chunk_rag_facet_min_gain)

        normalized_to_facet: Dict[str, str] = {}
        ordered_norms: List[str] = []
        for facet in facets:
            norm = self._normalize_heading(facet)
            if norm in normalized_to_facet:
                continue
            normalized_to_facet[norm] = facet
            ordered_norms.append(norm)

        # Pre-compute total evidence universe for coverage tracking.
        all_ids = set()
        norm_to_ids: Dict[str, set] = {}
        norm_to_score: Dict[str, float] = {}
        for norm in ordered_norms:
            claims = concept_claims.get(norm, [])
            ids = set()
            score_sum = 0.0
            for idx, claim in enumerate(claims):
                page = int(claim.get("page", 0) or 0)
                text = str(claim.get("text", "") or "")
                cid = f"{page}:{text[:120]}:{idx}"
                ids.add(cid)
                score_sum += float(claim.get("similarity", 0.0) or 0.0)
            norm_to_ids[norm] = ids
            all_ids.update(ids)
            norm_to_score[norm] = score_sum / float(len(claims) or 1)

        total_universe = max(1, len(all_ids))
        use_rpd_order = facets_have_rpd_codes(facets)
        if use_rpd_order:
            ranked_norms = ordered_norms
        else:
            ranked_norms = sorted(
                ordered_norms,
                key=lambda n: (-norm_to_score.get(n, 0.0), n),
            )

        selected_norms: List[str] = []
        selected_ids = set()
        coverage = 0.0
        selected_tokens_est = 0
        reason = 0.0  # 1=max facets, 2=max tokens, 3=no gain after min coverage

        for norm in ranked_norms:
            if len(selected_norms) >= max_count:
                reason = 1.0
                break
            if selected_tokens_est + per_facet_tokens > max_tokens:
                reason = 2.0
                break
            facet_ids = norm_to_ids.get(norm, set())
            new_ids = facet_ids - selected_ids
            gain = float(len(new_ids)) / float(total_universe)
            candidate_count = len(selected_norms) + 1
            if candidate_count > min_count and coverage >= coverage_min and gain < min_gain:
                reason = 3.0
                break
            selected_norms.append(norm)
            selected_ids.update(facet_ids)
            selected_tokens_est += per_facet_tokens
            coverage = float(len(selected_ids)) / float(total_universe)
            if selected_tokens_est >= target_tokens and coverage >= coverage_min and candidate_count >= min_count:
                reason = 2.0
                break

        if not selected_norms:
            selected_norms = ranked_norms[:min(min_count, len(ranked_norms))]
            selected_ids = set()
            for norm in selected_norms:
                selected_ids.update(norm_to_ids.get(norm, set()))
            selected_tokens_est = len(selected_norms) * per_facet_tokens
            coverage = float(len(selected_ids)) / float(total_universe)

        selected_facets = [normalized_to_facet[n] for n in selected_norms]
        if use_rpd_order:
            selected_facets = sort_facets_by_subtopic_code(selected_facets)
            selected_norms = [self._normalize_heading(f) for f in selected_facets]
        pruned_claims = {n: concept_claims.get(n, []) for n in selected_norms}
        stats = {
            "selected_count": float(len(selected_norms)),
            "candidate_count": float(len(ranked_norms)),
            "coverage": float(coverage),
            "target_tokens": float(target_tokens),
            "max_tokens": float(max_tokens),
            "estimated_tokens": float(selected_tokens_est),
            "stop_reason_code": float(reason),
        }
        return selected_facets, pruned_claims, stats

    def _build_concept_cache_key(self, theme: str, selected_pages: List[Dict[str, Any]]) -> str:
        page_key = ",".join([str(p.get("page_number", 0)) for p in selected_pages[:200]])
        return f"{settings.llm_model}|{theme}|{len(selected_pages)}|{hash(page_key)}"

    def _build_concept_cards(
        self,
        theme: str,
        concepts: List[str],
        core_concepts: str,
        selected_pages: List[Dict[str, Any]],
        concept_claims: Dict[str, List[Dict[str, Any]]]
    ) -> List[ConceptCard]:
        """Build concept cards from generated elaboration text with page anchors."""
        sections = self._parse_concept_sections(core_concepts)
        cards: List[ConceptCard] = []
        for concept in concepts:
            elaboration = sections.get(concept.lower().strip(), "")
            if not elaboration:
                elaboration = sections.get(self._normalize_heading(concept), "")
            source_pages = self._find_source_pages_for_concept(concept, selected_pages, max_pages=5)
            claims = concept_claims.get(self._normalize_heading(concept), [])
            cards.append(
                ConceptCard(
                    concept=concept,
                    normalized_concept=self._normalize_heading(concept),
                    elaboration_text=elaboration.strip(),
                    source_pages=source_pages,
                    claims=claims,
                )
            )
        logger.info(f"Built {len(cards)} concept cards for theme '{theme}'")
        return cards

    async def _collect_claims_for_concepts(
        self,
        theme: str,
        concepts: List[str],
        selected_pages: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Variant 1 optimized (per-concept candidate pages):
        - First pass: concepts are already selected for the theme.
        - Candidate pages for each concept are ranked by lexical overlap.
        - Claims are extracted for ONE concept on candidate pages only (top-k).
        - If deduped claims < MIN_CLAIMS_THRESHOLD, expand to next pages in ranking.
        """
        if not concepts or not selected_pages:
            return {}

        import os

        top_k = int(os.getenv("CLAIMS_TOP_K_PER_CONCEPT", "5"))
        # В claims-harvesting балансируем качество и скорость: уменьшаем порог,
        # чтобы реже расширять candidates из-за пограничных кейсов dedup.
        min_claims = int(os.getenv("MIN_CLAIMS_PER_CONCEPT", "4"))
        page_parallelism = int(os.getenv("CLAIMS_PAGE_PARALLELISM", "2"))

        concepts_norm = [self._normalize_heading(c) for c in concepts]
        concept_by_norm = {self._normalize_heading(c): c for c in concepts}

        # Pre-normalize page texts once (cheaper than repeating inside scoring)
        norm_pages: List[Dict[str, Any]] = []
        for p in selected_pages:
            text = p.get("content", "") or ""
            norm_pages.append(
                {
                    **p,
                    "_norm_content": self._normalize_heading(text),
                }
            )

        sema = asyncio.Semaphore(max(1, page_parallelism))

        # Perf aggregation for step2_claim_harvesting (time + tokens + CPU/GPU peaks).
        claim_perf_acc: Dict[str, float] = {
            "claim_requests_count": 0.0,
            "tokens_input_total": 0.0,
            "tokens_output_total": 0.0,
            "tokens_total": 0.0,
            "tokens_per_request_max": 0.0,
            "request_seconds_total": 0.0,
            "request_seconds_max": 0.0,
            "tokens_per_second_max": 0.0,
            "peak_rss_mb_max": 0.0,
            "peak_gpu_mem_mb_max": 0.0,
            "peak_cpu_percent_sample_max": 0.0,
            "json_parse_failed_count": 0.0,
        }
        claim_perf_lock = asyncio.Lock()

        async def limited_extract_pages_batch(
            concept: str, pages_batch: List[Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
            async with sema:
                extracted = await self._extract_claims_from_pages_batch(
                    theme=theme,
                    concept=concept,
                    pages_batch=pages_batch,
                    perf_acc=claim_perf_acc,
                    perf_lock=claim_perf_lock,
                )
                norm_c = self._normalize_heading(concept)
                return extracted.get(norm_c, [])

        def score_page_for_concept(concept: str, page_norm_content: str) -> int:
            terms = [t for t in self._normalize_heading(concept).split() if len(t) > 2]
            if not terms:
                # Fallback: use normalized concept tokens as a single term
                terms = [self._normalize_heading(concept)]
            score = 0
            for t in terms:
                score += page_norm_content.count(t)
            return score

        deduped: Dict[str, List[Dict[str, Any]]] = {}

        # Уменьшаем контекст на один запрос (pages_block станет меньше).
        CLAIMS_BATCH_SIZE = 3
        PARALLEL_BATCHES = 2
        try:
            CLAIMS_BATCH_SIZE = int(os.getenv("CLAIMS_BATCH_SIZE", "3"))
            PARALLEL_BATCHES = int(os.getenv("CLAIMS_PARALLEL_BATCHES", "2"))
        except Exception:
            pass

        # Guard: concepts are processed sequentially (no interleaving prompts between concepts).
        # Parallelism exists only *within a single concept* across page-batches.
        for concept in concepts:
            norm_c = self._normalize_heading(concept)
            concept_title_for_log = concept_by_norm.get(norm_c, norm_c)
            scored = []
            for page in norm_pages:
                score = score_page_for_concept(concept, page.get("_norm_content", ""))
                scored.append((score, page))

            # Higher score first; stable fallback by page_number to keep deterministic behavior
            scored.sort(
                key=lambda x: (x[0], -int(x[1].get("page_number", 0))), reverse=True
            )

            # Expand candidates until we get enough unique claims or we run out of pages
            take = min(top_k, len(scored))
            raw_claims: List[Dict[str, Any]] = []
            start_c = time.time()

            logger.info(
                f"Claim harvesting for concept '{concept_title_for_log}': "
                f"try top_k={top_k}, min_claims={min_claims}"
            )

            while take > 0:
                candidate_pages = [sp[1] for sp in scored[:take]]

                # Batch extraction like concept extraction:
                # - split candidate pages into batches of CLAIMS_BATCH_SIZE
                # - process batch groups in parallel up to PARALLEL_BATCHES
                page_batches: List[List[Dict[str, Any]]] = []
                for i in range(0, len(candidate_pages), CLAIMS_BATCH_SIZE):
                    page_batches.append(candidate_pages[i : i + CLAIMS_BATCH_SIZE])

                for bg in range(0, len(page_batches), PARALLEL_BATCHES):
                    batch_group = page_batches[bg : bg + PARALLEL_BATCHES]
                    tasks = [
                        limited_extract_pages_batch(concept, pages_batch)
                        for pages_batch in batch_group
                    ]
                    pages_claim_lists = await asyncio.gather(*tasks)
                    for lst in pages_claim_lists:
                        raw_claims.extend(lst)

                clean = self._deduplicate_claims(raw_claims)
                if len(clean) >= min_claims or take >= len(scored):
                    logger.info(
                        f"Claims for '{concept_title_for_log}': "
                        f"{len(raw_claims)} -> {len(clean)} after dedup (candidates={take})"
                    )
                    deduped[norm_c] = clean
                    break

                # Not enough claims yet: expand to the next page(s) below
                # "берем ниже в ранжировании" => take more pages
                step = max(1, top_k // 2)
                take = min(len(scored), take + step)
                # continue loop with increased candidate set

            if norm_c not in deduped:
                # Fallback: even if take becomes 0, still return best effort
                deduped[norm_c] = self._deduplicate_claims(raw_claims)

            logger.info(
                f"Claim harvesting done for '{concept_title_for_log}' in "
                f"{time.time() - start_c:.1f}s (final_take={take})"
            )

        # Store for step-level aggregation.
        self._last_claim_perf_metrics = claim_perf_acc
        return deduped

    async def _extract_claims_from_pages_batch(
        self,
        theme: str,
        concept: str,
        pages_batch: List[Dict[str, Any]],
        perf_acc: Optional[Dict[str, Any]] = None,
        perf_lock: Optional[asyncio.Lock] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract claims for ONE concept across multiple pages at once.
        Returns: { normalized_concept: [ {text,pages,books}, ... ] }
        """
        concept_norm = self._normalize_heading(concept)
        concept_title = concept

        # Provide pages to the model with clear separators.
        pages_block = "\n\n".join(
            [
                f"--- PAGE {int(p.get('page_number', 0))} / book: {p.get('book_title','')} ---\n{p.get('content','')}"
                for p in pages_batch
            ]
        )

        prompt = f"""Тема: "{theme}"
Концепт (из списка): "{concept_title}"

Ниже приведены страницы книги. Извлеки для КОНЦЕПТА только те короткие атомарные утверждения, которые
явно следуют из текста каждой страницы.

Правила:
- Не придумывай факты вне текста страниц.
- Утверждения должны быть короткими (1 факт = 1 утверждение).
- Для каждой страницы верни список утверждений (может быть пустым).

Формат результата: объект с полем items, где items — список объектов
с полями page_number и claims.

Страницы:
{pages_block}
"""

        # Lightweight perf sampling around a single LLM request.
        # This is intentionally robust to missing keys in Ollama responses.
        stop_evt = asyncio.Event()

        async def _resource_sampler() -> Dict[str, float]:
            peak_rss = 0.0
            peak_gpu = 0.0
            peak_cpu = 0.0
            proc = psutil.Process()

            # Prime psutil cpu_percent (requires a prior call to get non-zero deltas).
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass

            while not stop_evt.is_set():
                try:
                    rss = float(proc.memory_info().rss)
                    if rss > peak_rss:
                        peak_rss = rss
                    try:
                        cpu = float(psutil.cpu_percent(interval=None))
                        if cpu > peak_cpu:
                            peak_cpu = cpu
                    except Exception:
                        pass

                    if GPUtil is not None:
                        try:
                            gpus = GPUtil.getGPUs()
                            if gpus:
                                gpu_mem = max(float(g.memoryUsed) for g in gpus)
                                if gpu_mem > peak_gpu:
                                    peak_gpu = gpu_mem
                        except Exception:
                            pass
                except Exception:
                    pass
                await asyncio.sleep(0.4)

            return {
                "peak_rss_mb": (peak_rss / (1024.0 * 1024.0)) if peak_rss else 0.0,
                "peak_gpu_mem_mb": peak_gpu,
                "peak_cpu_percent_sample": peak_cpu,
            }

        request_start = time.monotonic()
        sampler_task = asyncio.create_task(_resource_sampler())
        response: Dict[str, Any] = {}
        parse_failed = False

        try:
            data = await self._generate_json_object(
                prompt,
                {"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            ) or {"items": []}
            items = data.get("items", [])

            out: List[Dict[str, Any]] = []
            for item in items:
                page_num = int(item.get("page_number", 0) or 0)
                page_claims = item.get("claims", []) or []
                for claim in page_claims:
                    ctext = str(claim).strip()
                    if not ctext:
                        continue
                    # book_title can be different per page; infer it from provided pages_batch
                    book_title = ""
                    for p in pages_batch:
                        if int(p.get("page_number", 0) or 0) == page_num:
                            book_title = p.get("book_title", "") or ""
                            break
                    out.append(
                        {
                            "text": ctext,
                            "page": page_num,
                            "pages": [page_num],
                            "books": [book_title] if book_title else [],
                        }
                    )

            return {concept_norm: out}
        except Exception as e:
            parse_failed = True
            logger.warning(
                f"Claim batch extraction failed for concept '{concept_title}': {e}"
            )
            return {concept_norm: []}
        finally:
            # Stop sampler and aggregate perf counters (best-effort).
            request_seconds = time.monotonic() - request_start
            stop_evt.set()
            try:
                sampler_metrics = await sampler_task
            except Exception:
                sampler_metrics = {
                    "peak_rss_mb": 0.0,
                    "peak_gpu_mem_mb": 0.0,
                    "peak_cpu_percent_sample": 0.0,
                }

            if perf_acc is not None and perf_lock is not None:
                try:
                    prompt_eval_count = response.get("prompt_eval_count", 0) or 0
                    eval_count = response.get("eval_count", 0) or 0
                    # Fallback for real Ollama responses without usage fields.
                    if prompt_eval_count == 0 and "prompt" in locals():
                        prompt_eval_count = len(prompt.split())
                    if eval_count == 0:
                        eval_count = len((response.get("response") or "").split())

                    input_tokens = float(prompt_eval_count)
                    output_tokens = float(eval_count)
                    total_tokens = input_tokens + output_tokens

                    async with perf_lock:
                        perf_acc["claim_requests_count"] += 1.0
                        perf_acc["tokens_input_total"] += input_tokens
                        perf_acc["tokens_output_total"] += output_tokens
                        perf_acc["tokens_total"] += total_tokens
                        if total_tokens > perf_acc["tokens_per_request_max"]:
                            perf_acc["tokens_per_request_max"] = float(total_tokens)
                        perf_acc["request_seconds_total"] += float(request_seconds)
                        if request_seconds > perf_acc["request_seconds_max"]:
                            perf_acc["request_seconds_max"] = float(request_seconds)
                        if request_seconds > 0:
                            tokens_per_second = float(total_tokens) / float(request_seconds)
                            if tokens_per_second > perf_acc["tokens_per_second_max"]:
                                perf_acc["tokens_per_second_max"] = float(tokens_per_second)

                        # Track peaks across all requests.
                        if sampler_metrics.get("peak_rss_mb", 0.0) > perf_acc["peak_rss_mb_max"]:
                            perf_acc["peak_rss_mb_max"] = float(
                                sampler_metrics.get("peak_rss_mb", 0.0)
                            )
                        if (
                            sampler_metrics.get("peak_gpu_mem_mb", 0.0)
                            > perf_acc["peak_gpu_mem_mb_max"]
                        ):
                            perf_acc["peak_gpu_mem_mb_max"] = float(
                                sampler_metrics.get("peak_gpu_mem_mb", 0.0)
                            )
                        if (
                            sampler_metrics.get("peak_cpu_percent_sample", 0.0)
                            > perf_acc["peak_cpu_percent_sample_max"]
                        ):
                            perf_acc["peak_cpu_percent_sample_max"] = float(
                                sampler_metrics.get("peak_cpu_percent_sample", 0.0)
                            )

                        if parse_failed:
                            perf_acc["json_parse_failed_count"] += 1.0
                except Exception:
                    # Metrics must never break generation.
                    pass

    async def _extract_claims_from_page(
        self,
        theme: str,
        concepts: List[str],
        page_text: str,
        page_number: int,
        book_title: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract claims per concept from a single page.
        No global limit is imposed on claims across the pipeline.
        """
        numbered = "\n".join([f"- {c}" for c in concepts])
        prompt = f"""Тема: "{theme}"

Концепты (целевые):
{numbered}

Страница {page_number} (книга: {book_title}):
{page_text}

Задача:
- Для каждого концепта выпиши утверждения, которые явно поддерживаются содержанием этой страницы.
- Если для концепта нет утверждений на странице, верни пустой массив.
- Утверждения делай короткими и атомарными (1 факт = 1 утверждение).
- Не придумывай факты, которых нет в тексте страницы.

Формат результата: объект с полем items, где каждый элемент содержит:
- concept: точное название концепта из списка
- claims: список утверждений
"""
        try:
            data = await self._generate_json_object(
                prompt,
                {"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            ) or {"items": []}
            items = data.get("items", [])
            result: Dict[str, List[Dict[str, Any]]] = {}
            concept_norm_map = {self._normalize_heading(c): c for c in concepts}

            # If we only asked for one concept, be robust to model paraphrasing in "concept" field
            if len(concepts) == 1:
                norm_single = self._normalize_heading(concepts[0])
                out: List[Dict[str, Any]] = []
                for item in items:
                    for claim in item.get("claims", []) or []:
                        ctext = str(claim).strip()
                        if not ctext:
                            continue
                        out.append(
                            {
                                "text": ctext,
                                "page": page_number,
                                "pages": [page_number],
                                "books": [book_title] if book_title else [],
                            }
                        )
                if out:
                    result[norm_single] = out
                return result

            for item in items:
                raw_concept = str(item.get("concept", "")).strip()
                norm = self._normalize_heading(raw_concept)
                if norm not in concept_norm_map:
                    continue
                out: List[Dict[str, Any]] = []
                for claim in item.get("claims", []) or []:
                    ctext = str(claim).strip()
                    if not ctext:
                        continue
                    out.append(
                        {
                            "text": ctext,
                            "page": page_number,
                            "pages": [page_number],
                            "books": [book_title] if book_title else [],
                        }
                    )
                if out:
                    result.setdefault(norm, []).extend(out)
            return result
        except Exception as e:
            logger.warning(
                f"Claim extraction failed on page {page_number}: {e}"
            )
            return {}

    def _normalize_claim_text(self, text: str) -> str:
        s = self._normalize_heading(text)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _deduplicate_claims(
        self, claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Similarity dedup for claims:
        - exact normalized duplicates
        - substring and high token overlap duplicates
        Aggregates pages/books into one retained claim.
        """
        if not claims:
            return []

        unique: List[Dict[str, Any]] = []
        for claim in claims:
            text = str(claim.get("text", "")).strip()
            if not text:
                continue
            norm = self._normalize_claim_text(text)
            pages = [int(p) for p in claim.get("pages", []) if isinstance(p, int) or str(p).isdigit()]
            page = claim.get("page")
            if (not pages) and (isinstance(page, int) or str(page).isdigit()):
                pages = [int(page)]
            books = [str(b) for b in claim.get("books", []) if str(b).strip()]

            merged = False
            for kept in unique:
                knorm = kept["_norm"]
                if norm == knorm or norm in knorm or knorm in norm:
                    kept["pages"] = sorted(set(kept["pages"] + pages))
                    kept["page"] = min(kept["pages"]) if kept["pages"] else 0
                    kept["books"] = sorted(set(kept["books"] + books))
                    merged = True
                    break

                w1 = set(norm.split())
                w2 = set(knorm.split())
                if w1 and w2:
                    overlap = len(w1 & w2) / min(len(w1), len(w2))
                    if overlap >= 0.8:
                        kept["pages"] = sorted(set(kept["pages"] + pages))
                        kept["page"] = min(kept["pages"]) if kept["pages"] else 0
                        kept["books"] = sorted(set(kept["books"] + books))
                        merged = True
                        break

            if not merged:
                unique.append(
                    {
                        "text": text,
                        "page": min(sorted(set(pages))) if pages else 0,
                        "pages": sorted(set(pages)),
                        "books": sorted(set(books)),
                        "_norm": norm,
                    }
                )

        for item in unique:
            item.pop("_norm", None)
        return unique

    def _normalize_heading(self, text: str) -> str:
        return " ".join(text.lower().replace("ё", "е").split())

    def _parse_concept_sections(self, core_concepts: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        current_title = None
        current_lines: List[str] = []
        for line in core_concepts.splitlines():
            if line.startswith("### "):
                if current_title is not None:
                    sections[current_title] = "\n".join(current_lines).strip()
                current_title = self._normalize_heading(line.replace("### ", "", 1).strip())
                current_lines = []
            else:
                if current_title is not None:
                    current_lines.append(line)
        if current_title is not None:
            sections[current_title] = "\n".join(current_lines).strip()
        return sections

    def _find_source_pages_for_concept(
        self,
        concept: str,
        selected_pages: List[Dict[str, Any]],
        max_pages: int = 5
    ) -> List[int]:
        concept_terms = [t for t in self._normalize_heading(concept).split() if len(t) > 2]
        scored: List[tuple[int, int]] = []
        for page in selected_pages:
            text = self._normalize_heading(page.get("content", ""))
            score = sum(1 for term in concept_terms if term in text)
            if score > 0:
                scored.append((int(page.get("page_number", 0)), score))
        scored.sort(key=lambda x: x[1], reverse=True)
        pages = [p for p, _ in scored[:max_pages]]
        if pages:
            return pages
        # Fallback: keep at least one anchor
        if selected_pages:
            return [int(selected_pages[0].get("page_number", 0))]
        return []

    def _strip_artifact_markdown_fences(self, text: str) -> str:
        """Remove accidental outer ``` / ```markdown wrappers from LLM output."""
        s = (text or "").strip()
        if not s.startswith("```"):
            return text or ""
        lines = s.splitlines()
        if not lines:
            return ""
        lines = lines[1:]
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _as_card_id(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", self._normalize_heading(text).replace(" ", "_"))
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug or "concept"

    def _provenance_claim_max_chars(self) -> int:
        try:
            v = int(os.getenv("PROVENANCE_CLAIM_MAX_CHARS", "0"))
        except Exception:
            v = 0
        return max(0, v)

    def _truncate_claim_text(self, t: str) -> str:
        t = (t or "").strip().replace('"', "'")
        m = self._provenance_claim_max_chars()
        if m and len(t) > m:
            return t[:m] + "..."
        return t

    def _provenance_claim_items_all(self, card: ConceptCard) -> List[Dict[str, Any]]:
        """
        Provenance-friendly claims list:
        - keep per-claim text
        - surface one anchor page per claim (page)
        """
        out: List[Dict[str, Any]] = []
        for cl in card.claims or []:
            raw = (cl.get("text") or "").strip()
            if not raw:
                continue
            page = cl.get("page", 0)
            if not (isinstance(page, int) or str(page).isdigit()):
                page = 0
            out.append({"text": self._truncate_claim_text(raw), "page": int(page) if page else 0})
        return out

    def _format_pages_for_provenance(self, pages: List[int]) -> str:
        uniq = sorted(set([int(x) for x in pages if isinstance(x, int) or str(x).isdigit()]))
        return ",".join(str(x) for x in uniq[:40])

    def _book_from_card(self, card: ConceptCard) -> str:
        books: List[str] = []
        for cl in card.claims or []:
            books.extend(cl.get("books", []) or [])
        for b in books:
            raw = str(b).strip()
            if not raw:
                continue
            for bid, meta in self._book_catalog.items():
                title = (meta.get("title") or "").strip()
                if raw == bid or (title and raw == title):
                    return self._format_book_for_provenance(bid, title or raw)
            return raw
        return ""

    def _aggregated_pages_for_card(self, card: ConceptCard) -> List[int]:
        pages: List[int] = []
        for p in card.source_pages or []:
            try:
                pages.append(int(p))
            except Exception:
                pass
        for cl in card.claims or []:
            for p in cl.get("pages", []) or []:
                try:
                    pages.append(int(p))
                except Exception:
                    pass
        return pages

    def _word_overlap_score(self, a: str, b: str) -> float:
        wa = set(re.findall(r"[a-zа-яё0-9]+", (a or "").lower(), flags=re.I))
        wb = set(re.findall(r"[a-zа-яё0-9]+", (b or "").lower(), flags=re.I))
        if not wa or not wb:
            return 0.0
        inter = len(wa & wb)
        if inter == 0:
            return 0.0
        return float(inter) / float(len(wa | wb)) ** 0.5

    def _card_match_blob(self, card: ConceptCard) -> str:
        parts = [card.concept or "", card.elaboration_text or ""]
        for cl in card.claims or []:
            parts.append((cl.get("text") or ""))
        return " ".join(parts)

    def _best_card_for_chunk(
        self, concept_cards: List[ConceptCard], chunk: str
    ) -> ConceptCard:
        if not concept_cards:
            raise ValueError("empty concept_cards")
        best = concept_cards[0]
        best_s = -1.0
        for c in concept_cards:
            s = self._word_overlap_score(chunk, self._card_match_blob(c))
            if s > best_s:
                best_s = s
                best = c
        return best

    def _lab_section_chunk(self, lines: List[str], idx: int) -> str:
        line = lines[idx]
        parts: List[str] = [line]
        i = idx + 1
        while i < len(lines):
            ln = lines[i]
            if line.startswith("### "):
                if ln.startswith("### ") or ln.startswith("## "):
                    break
            else:
                if ln.startswith("## "):
                    break
            parts.append(ln)
            i += 1
            if len(parts) > 100:
                break
        return "\n".join(parts)

    def _single_line_origin_comment(
        self,
        tag: str,
        card: ConceptCard,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        pages = self._aggregated_pages_for_card(card)
        pages_str = self._format_pages_for_provenance(pages)
        book = self._book_from_card(card)
        claims = self._provenance_claim_items_all(card)
        if not claims:
            claims = [{"text": "[нет извлеченных утверждений]", "page": 0}]
        concept_esc = (card.concept or "").replace('"', "'")
        parts: List[str] = [
            f'concept="{concept_esc}"',
            f"pages=[{pages_str}]",
            f'book="{book}"',
            f"claims={json.dumps(claims, ensure_ascii=False)}",
        ]
        if extra:
            for k, v in extra.items():
                parts.append(f"{k}={json.dumps(v, ensure_ascii=False)}")
        review_note = ""
        if not book or not pages_str:
            review_note = ' <!-- REVIEW_NOTE="missing_origin" -->'
        return f'<!-- {tag}: {"; ".join(parts)} -->' + review_note

    def _annotate_lecture_with_provenance(
        self, markdown: str, concept_cards: List[ConceptCard]
    ) -> str:
        """Insert human-readable origin comments after each concept heading in lecture."""
        lines = (markdown or "").splitlines()
        if not lines:
            return markdown or ""

        card_map: Dict[str, ConceptCard] = {
            self._normalize_heading(c.concept): c for c in concept_cards
        }

        def _format_pages(pages: List[int]) -> str:
            uniq = sorted(set([int(x) for x in pages if isinstance(x, int) or str(x).isdigit()]))
            return ",".join(str(x) for x in uniq[:30])

        out: List[str] = []
        for line in lines:
            out.append(line)
            if not line.startswith("### "):
                continue

            concept_title = line.replace("### ", "", 1).strip()
            norm = self._normalize_heading(concept_title)
            card = card_map.get(norm)
            if not card:
                continue

            pages: List[int] = []
            books: List[str] = []
            for p in (card.source_pages or []):
                try:
                    pages.append(int(p))
                except Exception:
                    pass
            for cl in (card.claims or []):
                pages.extend(cl.get("pages", []) or [])
                books.extend(cl.get("books", []) or [])

            pages_str = _format_pages(pages)
            book = ""
            for b in books:
                if str(b).strip():
                    book = self._book_from_card(card) or str(b).strip()
                    break
            if not book:
                book = self._book_from_card(card)

            claims = self._provenance_claim_items_all(card)
            if not claims:
                claims = [{"text": "[нет извлеченных утверждений]", "page": 0}]

            review_note = ""
            if not book or not pages_str:
                review_note = ' <!-- REVIEW_NOTE="missing_origin" -->'

            out.append(
                f'<!-- CONCEPT_ORIGIN: concept="{concept_title}"; pages=[{pages_str}]; book="{book}"; claims={json.dumps(claims, ensure_ascii=False)} -->'
                + review_note
            )

        return "\n".join(out).strip()

    def _strip_legacy_top_origin_block(self, markdown: str, kind: str) -> str:
        """Remove old <!-- CONCEPT_ORIGINS_LAB|SELFCHECK ... --> inserted after the title."""
        if kind == "lab":
            pat = r"<!--\s*CONCEPT_ORIGINS_LAB\s*\n[\s\S]*?-->\s*\n?"
        else:
            pat = r"<!--\s*CONCEPT_ORIGINS_SELFCHECK\s*\n[\s\S]*?-->\s*\n?"
        return re.sub(pat, "", markdown or "", count=1, flags=re.MULTILINE).strip()

    def _annotate_lab_with_provenance(
        self, markdown: str, concept_cards: List[ConceptCard]
    ) -> str:
        """Lab provenance: per-task origin under each task; keep section origin only for typical errors."""
        md = self._strip_legacy_top_origin_block(markdown or "", "lab")
        lines = md.splitlines()
        if not lines or not concept_cards:
            return md.strip()

        # Tasks in lab are usually marked as "**Задание N. ...**" (or without bold).
        task_re = re.compile(r"^\s*(?:\*\*)?\s*задание\s+(?P<num>\d+)\.", flags=re.I)
        errors_heading_re = re.compile(r"^\s*##\s+.*типичн.*ошиб", flags=re.I)
        heading_re = re.compile(r"^\s*#{2,3}\s+")

        out: List[str] = []
        in_errors = False
        i = 0
        while i < len(lines):
            line = lines[i]
            out.append(line)

            # Track "Типичные ошибки" section for a single section-level marker.
            if errors_heading_re.match(line):
                in_errors = True
                # Keep section-level origin for typical errors only.
                chunk = self._lab_section_chunk(lines, i)
                card = self._best_card_for_chunk(concept_cards, chunk)
                out.append(self._single_line_origin_comment("SECTION_ORIGIN", card))
                i += 1
                continue
            if in_errors and line.startswith("## "):
                in_errors = False

            m = task_re.match(line)
            if m:
                num = int(m.group("num"))
                # Build a chunk for this task: until next task / heading.
                chunk_lines = [line]
                j = i + 1
                while j < len(lines) and len(chunk_lines) < 80:
                    nxt = lines[j]
                    if task_re.match(nxt):
                        break
                    if heading_re.match(nxt):
                        break
                    chunk_lines.append(nxt)
                    j += 1
                chunk = "\n".join(chunk_lines)
                card = self._best_card_for_chunk(concept_cards, chunk)
                out.append(self._single_line_origin_comment("TASK_ORIGIN", card, extra={"n": num}))

            i += 1
        return "\n".join(out).strip()

    def _annotate_selfcheck_with_provenance(
        self, markdown: str, concept_cards: List[ConceptCard]
    ) -> str:
        """Per-question provenance under every detected task line (stops before answer key)."""
        md = self._strip_legacy_top_origin_block(markdown or "", "selfcheck")
        lines = md.splitlines()
        if not lines or not concept_cards:
            return md.strip()

        # Accept common numbering variants:
        # **1. ...**, 1. ..., 1) ...
        q_re = re.compile(r"^(?:\*\*)?\s*(?P<num>\d+)[\.\)]\s+")
        out: List[str] = []
        in_key = False
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("## ") and "ключ" in line.lower():
                in_key = True
            out.append(line)
            if not in_key:
                m = q_re.match(line.strip())
                if m:
                    num = int(m.group("num"))
                    chunk_lines = [line]
                    j = i + 1
                    while j < len(lines) and len(chunk_lines) < 30:
                        nxt = lines[j]
                        if q_re.match(nxt.strip()) and j > i:
                            break
                        if nxt.startswith("## "):
                            break
                        if nxt.strip() == "---":
                            break
                        chunk_lines.append(nxt)
                        j += 1
                    chunk = "\n".join(chunk_lines)
                    card = self._best_card_for_chunk(concept_cards, chunk)
                    out.append(
                        self._single_line_origin_comment(
                            "QUESTION_ORIGIN", card, extra={"n": num}
                        )
                    )
            i += 1
        return "\n".join(out).strip()

    def _build_review_report(
        self,
        theme: str,
        lecture_md: str,
        lab_md: str,
        selfcheck_md: str,
        concept_cards: List[ConceptCard],
    ) -> str:
        """Build concise reviewer report based on missing origin and NEEDS_REVIEW markers."""
        missing_origin: List[str] = []
        for c in concept_cards:
            pages = list(c.source_pages or [])
            books = []
            for cl in (c.claims or []):
                pages.extend(cl.get("pages", []) or [])
                books.extend(cl.get("books", []) or [])
            pages_ok = any(
                [p for p in pages if isinstance(p, int) or str(p).isdigit()]
            )
            book_ok = any([str(b).strip() for b in books])
            if not pages_ok or not book_ok:
                missing_origin.append(
                    f'- concept="{c.concept}"; pages_ok={bool(pages_ok)}; book_ok={bool(book_ok)}'
                )

        needs_review_markers = []
        for text, name in [(lab_md or "", "lab"), (selfcheck_md or "", "selfcheck")]:
            if "NEEDS_REVIEW" in text:
                # Keep it simple: just note existence
                needs_review_markers.append(f'- {name}: found NEEDS_REVIEW')

        if not missing_origin:
            missing_origin = ["- none"]
        if not needs_review_markers:
            needs_review_markers = ["- none"]

        return (
            f"# Review Report: {theme}\n\n"
            "## Origin gaps (concept -> book/pages)\n"
            + "\n".join(missing_origin)
            + "\n\n## Explicit NEEDS_REVIEW markers\n"
            + "\n".join(needs_review_markers)
            + "\n"
        )

    def _structural_validate_lab(self, text: str) -> List[str]:
        w: List[str] = []
        if len((text or "").strip()) < 200:
            w.append("lab: very short content, possible generation failure")
        if (text or "").count("\n") < 5:
            w.append("lab: few lines, structure may be incomplete")
        return w

    def _structural_validate_selfcheck(self, text: str) -> List[str]:
        w: List[str] = []
        body = text or ""
        if len(body.strip()) < 400:
            w.append("selfcheck: very short content, possible generation failure")
        numbered = re.findall(r"\*\*\d+\.", body)
        if len(numbered) < 10:
            w.append(
                f"selfcheck: expected ~15 numbered questions, found {len(numbered)}"
            )
        if not re.search(r"ключ|ответы|правильн", body, re.IGNORECASE):
            w.append("selfcheck: no answer key section detected")
        return w

    def _format_claims_only_block_for_practice(self, concept_cards: List[ConceptCard]) -> str:
        """Facts for lab/self-check generation: harvested claims (+ page refs), no elaboration."""
        chunks: List[str] = []
        for c in concept_cards:
            lines = [f"### {c.concept}", "Утверждения из учебного источника (единственный разрешённый источник фактов):"]
            any_claim = False
            for cl in c.claims or []:
                t = (cl.get("text") or "").strip()
                if not t:
                    continue
                any_claim = True
                pgs = cl.get("pages", []) or []
                if pgs:
                    page_nums: List[str] = []
                    for p in pgs:
                        try:
                            page_nums.append(str(int(p)))
                        except Exception:
                            continue
                    ps = ",".join(page_nums) if page_nums else ""
                    if ps:
                        lines.append(f"- (стр. {ps}) {t}")
                    else:
                        lines.append(f"- {t}")
                else:
                    lines.append(f"- {t}")
            if not any_claim:
                lines.append("- [нет утверждений для концепта]")
            sp = ",".join(str(p) for p in (c.source_pages or []))
            if sp:
                lines.append(f"(якорные страницы концепта: {sp})")
            chunks.append("\n".join(lines))
        return "\n\n".join(chunks).strip()

    def _concept_cards_block_for_verifier(
        self, concept_cards: List[ConceptCard]
    ) -> str:
        """Verifier checks drafts against the same claims-only ground truth as practice generation."""
        return self._format_claims_only_block_for_practice(concept_cards)

    async def _llm_verify_package_artifact(
        self,
        kind: str,
        theme: str,
        concept_cards: List[ConceptCard],
        draft_markdown: str,
    ) -> tuple[str, List[str]]:
        """
        Grounded verifier: only ConceptCards as facts; no full lecture in context.
        Returns (possibly revised markdown, extra warnings).
        """
        extra: List[str] = []
        if not concept_cards or self.use_mock or not self.model_manager:
            return draft_markdown, extra

        cards_block = self._concept_cards_block_for_verifier(concept_cards)
        if kind == "lab":
            prompt = f"""Ты редактор учебных материалов.

Источник истины — ТОЛЬКО утверждения из учебника в блоках ниже (без текста лекции). Не используй внешние знания и не добавляй факты, которых нет в этих утверждениях.

Тема лабораторной: "{theme}"

Утверждения по концептам:
{cards_block}

Черновик лабораторной работы (markdown):
{draft_markdown}

Задача:
- Проверь согласованность с утверждениями: цель, теория и шаги не должны требовать того, чего нет в списке выше.
- Исправь формулировки при необходимости минимально; не переписывай документ целиком без причины.
- Если пункт невозможно обосновать карточками, замени формулировку на нейтральную или пометь строку комментарием HTML: <!-- NEEDS_REVIEW: краткая причина -->.
- Сохрани структуру разделов и markdown.
- Выведи ТОЛЬКО итоговый markdown лабораторной (как один документ), без оборачивания в ```."""
        else:
            prompt = f"""Ты редактор учебных материалов.

Источник истины — ТОЛЬКО утверждения из учебника в блоках ниже. Не используй внешние знания и не добавляй факты, которых нет в этих утверждениях.

Тема самопроверки: "{theme}"

Утверждения по концептам:
{cards_block}

Черновик самопроверки (markdown):
{draft_markdown}

Задача:
- Проверь, что ответы и ключ согласованы с утверждениями выше и что ответ соответствует вопросу.
- Исправь только ошибки; не меняй число заданий (15) и общую структуру (тесты / короткие ответы / мини-задачи / ключ).
- Если для пункта недостаточно оснований в карточках, в ключе или пояснении укажи для этого номера: NEEDS_REVIEW (одной фразой), не выдумывая фактов.
- Выведи ТОЛЬКО итоговый markdown самопроверки (как один документ), без оборачивания в ```."""

        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            )
            revised = (response.get("response") or "").strip()
            revised = self._strip_artifact_markdown_fences(revised)
            min_ok = max(300, int(len(draft_markdown) * 0.35))
            if len(revised) < min_ok:
                extra.append(
                    f"{kind}: verifier returned too short text, keeping draft"
                )
                return draft_markdown, extra
            if "NEEDS_REVIEW" in revised:
                extra.append(
                    f"{kind}: verifier marked NEEDS_REVIEW in output — manual check advised"
                )
            return revised, extra
        except Exception as e:
            logger.error(f"Artifact LLM verify failed ({kind}): {e}", exc_info=True)
            extra.append(f"{kind}: LLM verification failed ({e}), draft unchanged")
            return draft_markdown, extra

    async def _generate_lab_from_cards(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        concept_cards: List[ConceptCard]
    ) -> str:
        cards_block = self._format_claims_only_block_for_practice(concept_cards)
        prompt = f"""Сформируй ОДНУ стандартную лабораторную работу по теме "{theme}" в формате учебного конспекта.

Контекст курса (метаданные, не источник фактов):
- Направление: {rpd_data.get('profession', '')}
- Уровень: {rpd_data.get('academic_degree', '')}
- Кафедра: {rpd_data.get('department', '')}

Источник фактов (только утверждения из учебника; без развёрнутых пояснений лекции — студент опирается на лекцию и книгу сам):
{cards_block}

Требования:
- Не добавляй факты, которых нет в утверждениях выше. Формулировки заданий должны проверять понимание этих утверждений, а не пересказывать готовый "разбор".
- Без обращений к аудитории, нейтральный письменный стиль.
- Структура:
  1) Цель работы
  2) Краткая теоретическая база
  3) Необходимые данные/инструменты
  4) Пошаговое выполнение
  5) Ожидаемые результаты
  6) Критерии оценивания
  7) Типичные ошибки
- Формат Markdown.
"""
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.2, "num_ctx": int(settings.llm_num_ctx)}
            )
            content = response.get("response", "").strip()
            return f"# Лабораторная работа: {theme}\n\n{content}"
        except Exception as e:
            logger.error(f"Error generating lab: {e}")
            return f"# Лабораторная работа: {theme}\n\n[Ошибка генерации лабораторной работы]"

    async def _generate_selfcheck_from_cards(self, theme: str, concept_cards: List[ConceptCard]) -> str:
        cards_block = self._format_claims_only_block_for_practice(concept_cards)
        prompt = f"""Сформируй блок самопроверки (15 заданий) по теме "{theme}".

Источник фактов (только утверждения из учебника; вопросы должны проверять понимание этих утверждений; развёрнутая лекция студенту не подставляется в этот промпт):
{cards_block}

Требования к формату:
- Не добавляй факты, которых нет в утверждениях выше.
- 7 тестовых вопросов (single-choice, 4 варианта, один верный)
- 5 вопросов с коротким ответом
- 3 мини-задачи
- После вопросов: ключ ответов и краткие пояснения
- Без обращений к аудитории, формат markdown
"""
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.2, "num_ctx": int(settings.llm_num_ctx)}
            )
            content = response.get("response", "").strip()
            return f"# Самопроверка: {theme}\n\n{content}"
        except Exception as e:
            logger.error(f"Error generating self-check: {e}")
            return f"# Самопроверка: {theme}\n\n[Ошибка генерации самопроверки]"

    def _strip_lecture_html_for_display(self, lecture_md: str) -> str:
        """Remove HTML comments/tags from student-facing lecture (provenance kept separately)."""
        from presentation.sanitize import strip_html_and_comments

        text = strip_html_and_comments(lecture_md or "")
        # Collapse excessive blank lines after comment removal.
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    def _resolve_book_pdf_path(self, book_id: str) -> Optional[Path]:
        from pathlib import Path

        toc_data = self.toc_cache.get_cached_toc_data(book_id) if self.toc_cache else None
        if toc_data and toc_data.get("pdf_path"):
            p = Path(str(toc_data["pdf_path"]))
            if p.exists():
                return p
        return None

    async def _build_presentation_from_lecture(
        self,
        *,
        theme: str,
        lecture_md: str,
        selected_pages: List[Dict[str, Any]],
        book_ids: List[str],
        rpd_data: Dict[str, Any],
        concept_cards: Optional[List[ConceptCard]] = None,
    ):
        import hashlib
        from pathlib import Path

        from presentation.pipeline import build_presentation_from_lecture

        book_id = book_ids[0] if book_ids else ""
        if not book_id and selected_pages:
            book_id = str(selected_pages[0].get("book_id") or "")
        pdf_path = self._resolve_book_pdf_path(book_id) if book_id else None
        if not pdf_path:
            raise FileNotFoundError(f"PDF path not found for book_id={book_id}")

        theme_key = hashlib.md5(theme.encode("utf-8")).hexdigest()[:12]
        assets_dir = Path(settings.books_cache_dir) / "presentation" / book_id / theme_key
        assets_dir.mkdir(parents=True, exist_ok=True)

        async def llm_generate(prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
            llm_model = await self.model_manager.get_llm_model()
            response = await self._llm_generate_with_timeout(
                llm_model,
                log_label="presentation_slides",
                model=settings.llm_model,
                prompt=prompt,
                options=options,
            )
            from presentation.llm_response import normalize_llm_response

            return normalize_llm_response(response)

        result = await build_presentation_from_lecture(
            theme=theme,
            lecture_md=lecture_md,
            selected_pages=selected_pages,
            pdf_path=pdf_path,
            rpd_data=rpd_data,
            llm_generate=llm_generate,
            assets_dir=assets_dir,
            concept_cards=concept_cards,
        )
        content_slides = [
            s
            for s in (result.manifest.get("slides") or [])
            if s
        ]
        result.manifest["slide_count"] = len(content_slides)
        self._last_presentation_assets_dir = assets_dir
        self._last_presentation_preview = {
            "slides": list(result.slides or []),
            "resolved_paths": [str(p) if p else None for p in (result.resolved_paths or [])],
            "assets_dir": str(assets_dir),
        }
        return result

    def _pages_from_user_sources(
        self, user_sources: Optional[List[Dict[str, Any]]], theme: str
    ) -> List[Dict[str, Any]]:
        from sources.user_attachments import user_sources_to_pages

        pages = user_sources_to_pages(user_sources, theme=theme)
        if pages:
            logger.info("User priority sources: %s attachment(s), bypass TOC", len(pages))
        return pages

    async def generate_package_optimized(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        book_ids: List[str],
        *,
        user_sources: Optional[List[Dict[str, Any]]] = None,
        on_progress=None,
    ) -> OptimizedPackageResult:
        """Generate lecture+lab+self-check package in one optimized pass."""
        start_time = time.time()
        step_times: Dict[str, float] = {}
        warnings: List[str] = []
        errors: List[str] = []
        total_cached_pages = 0
        total_extracted_pages = 0
        toc_cache_hits = 0

        restore_llm_metrics = await self._start_llm_metrics_collection()
        presentation_slides_json = ""
        presentation_pptx: Optional[bytes] = None
        prev_cb = self._progress_callback
        self._progress_callback = on_progress or prev_cb
        try:
            self._emit_progress("init", "Запуск генерации пакета", f"тема: {theme}", pct=0)
            self._set_llm_metrics_phase("step1_selection")
            user_pages = self._pages_from_user_sources(user_sources, theme)
            if user_pages:
                self._emit_progress(
                    "step1_user_sources",
                    "Приоритетные источники",
                    f"вложений: {len(user_pages)} (без TOC)",
                    pct=4,
                )

            self._emit_progress("step1_pages", "Подбор страниц учебника", f"книг: {len(book_ids)}", pct=5)
            self._checkpoint(1, 5, "Step1 TOC/page selection", f"books={len(book_ids)}")
            step1_start = time.time()
            step1_detail: Dict[str, float] = {}
            textbook_pages: List[Dict[str, Any]] = []
            if book_ids:
                textbook_pages = await self._step1_optimized_page_selection(
                    theme, book_ids, step1_detail
                )
            selected_pages = list(user_pages) + list(textbook_pages)
            step_times["step1_optimized_page_selection"] = time.time() - step1_start
            step_times["step1_user_source_pages"] = float(len(user_pages))
            for k, v in step1_detail.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    step_times[str(k)] = float(v)

            if not selected_pages:
                errors.append("No relevant pages found (books or user attachments)")
                return OptimizedPackageResult(
                    success=False,
                    lecture_content="",
                    lab_content="",
                    selfcheck_content="",
                    moodle_questions_xml="",
                    concept_cards=[],
                    citations=[],
                    sources_used=[],
                    generation_time_seconds=time.time() - start_time,
                    confidence_score=0.0,
                    step_times=step_times,
                    warnings=warnings,
                    errors=errors,
                    review_report_content=""
                )

            for page_data in selected_pages:
                if page_data.get("cached", False):
                    total_cached_pages += 1
                else:
                    total_extracted_pages += 1

            toc_cache_hits = len([book_id for book_id in book_ids if self.toc_cache.is_book_cached(book_id)])

            self._set_llm_metrics_phase("step2_package_generation")
            self._emit_progress("step2_rag", "Генерация лекции и материалов", "", pct=15)
            self._checkpoint(2, 5, "Step2 package generation")
            step2_start = time.time()
            lecture_content, lab_content, selfcheck_content, concept_cards = await self._step2_package_generation(
                theme, rpd_data, selected_pages
            )
            step_times["step2_package_generation"] = time.time() - step2_start
            granular = getattr(self, "_last_step2_metrics", None) or {}
            for k, v in granular.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    step_times[str(k)] = float(v)

            # Build Moodle Question XML from raw self-check (before provenance comments).
            moodle_xml = ""
            if (
                settings.package_moodle_xml_enabled
                and settings.package_selfcheck_enabled
                and (selfcheck_content or "").strip()
            ):
                try:
                    from app.moodle.moodle_xml import build_moodle_multichoice_xml

                    moodle_xml = build_moodle_multichoice_xml(
                        quiz_name=theme, selfcheck_md=selfcheck_content, limit=7
                    )
                except Exception as e:
                    warnings.append(f"moodle_xml: failed to build questions xml ({e})")

            step2b_outer_start = time.time()
            strip_t0 = time.time()
            lab_content = self._strip_artifact_markdown_fences(lab_content)
            selfcheck_content = self._strip_artifact_markdown_fences(selfcheck_content)
            step_times["step2b_strip_fences_seconds"] = time.time() - strip_t0

            struct_t0 = time.time()
            if not self.use_mock:
                if lab_content.strip():
                    warnings.extend(self._structural_validate_lab(lab_content))
                if selfcheck_content.strip():
                    warnings.extend(self._structural_validate_selfcheck(selfcheck_content))
            step_times["step2b_structural_validate_seconds"] = time.time() - struct_t0

            self._checkpoint(3, 5, "Step2b sanitize + verifier")
            verify_t0 = time.time()
            self._set_llm_metrics_phase("step2b_artifact_verify")
            if (
                settings.package_artifact_llm_verify
                and concept_cards
                and not self.use_mock
                and self.model_manager
            ):
                verify_tasks = []
                if lab_content.strip():
                    verify_tasks.append(
                        self._llm_verify_package_artifact(
                            "lab", theme, concept_cards, lab_content
                        )
                    )
                if selfcheck_content.strip():
                    verify_tasks.append(
                        self._llm_verify_package_artifact(
                            "selfcheck", theme, concept_cards, selfcheck_content
                        )
                    )
                if verify_tasks:
                    verify_results = await asyncio.gather(*verify_tasks)
                    idx = 0
                    if lab_content.strip():
                        lab_content, w_lab = verify_results[idx]
                        warnings.extend(w_lab)
                        lab_content = self._strip_artifact_markdown_fences(lab_content)
                        idx += 1
                    if selfcheck_content.strip():
                        selfcheck_content, w_sc = verify_results[idx]
                        warnings.extend(w_sc)
                        selfcheck_content = self._strip_artifact_markdown_fences(
                            selfcheck_content
                        )
            step_times["step2b_llm_verify_wall_seconds"] = time.time() - verify_t0
            step_times["step2b_artifact_sanitize_verify"] = time.time() - step2b_outer_start

            prov_t0 = time.time()
            lecture_content = self._annotate_lecture_with_provenance(
                lecture_content, concept_cards
            )
            if lab_content.strip():
                lab_content = self._annotate_lab_with_provenance(lab_content, concept_cards)
            if selfcheck_content.strip():
                selfcheck_content = self._annotate_selfcheck_with_provenance(
                    selfcheck_content, concept_cards
                )
            step_times["step2c_provenance_annotation_seconds"] = time.time() - prov_t0

            self._emit_progress("step2_facets", "Разделы лекции собраны", "", pct=55, status="done")
            self._checkpoint(4, 5, "Step3 validation + formatting")
            self._emit_progress("step3_validate", "Проверка и форматирование", "", pct=70)
            self._set_llm_metrics_phase("step3_validation_formatting")
            step3_start = time.time()
            val_t0 = time.time()
            confidence = await self._validate_against_pages(lecture_content, selected_pages)
            step_times["step3_validate_against_pages_seconds"] = time.time() - val_t0
            if confidence < 0.5:
                warnings.append(f"Low confidence score: {confidence:.2%} - content may contain hallucinations")
            fgos_t0 = time.time()
            formatted_lecture, citations = await self._fgos_formatting(lecture_content, rpd_data, selected_pages)
            step_times["step3_fgos_formatting_seconds"] = time.time() - fgos_t0
            step_times["step3_validation_formatting"] = time.time() - step3_start

            lecture_for_pptx = formatted_lecture
            if settings.lecture_strip_html_comments:
                self._last_lecture_with_provenance = formatted_lecture
                formatted_lecture = self._strip_lecture_html_for_display(formatted_lecture)

            if settings.package_pptx_enabled and not self.use_mock and self.model_manager:
                pptx_t0 = time.time()
                self._set_llm_metrics_phase("step3b_presentation_pptx")
                self._emit_progress("step3_pptx", "Сборка презентации", "слайды и иллюстрации", pct=85)
                try:
                    pres = await self._build_presentation_from_lecture(
                        theme=theme,
                        lecture_md=lecture_for_pptx,
                        selected_pages=selected_pages,
                        book_ids=book_ids,
                        rpd_data=rpd_data,
                        concept_cards=concept_cards,
                    )
                    presentation_slides_json = pres.slides_json or ""
                    presentation_pptx = (
                        pres.pptx_bytes if pres.pptx_bytes and len(pres.pptx_bytes) > 0 else None
                    )
                    warnings.extend(pres.warnings or [])
                    step_times["step3b_presentation_slides"] = float(
                        pres.manifest.get("slide_count", 0) or 0
                    )
                except Exception as e:
                    warnings.append(f"pptx: failed ({e})")
                step_times["step3b_presentation_pptx_seconds"] = time.time() - pptx_t0

            rr_t0 = time.time()
            review_report = self._build_review_report(
                theme, formatted_lecture, lab_content, selfcheck_content, concept_cards
            )
            step_times["step3_review_report_seconds"] = time.time() - rr_t0
            self._emit_progress("step3_pptx", "Презентация готова", "", pct=92, status="done")
            self._checkpoint(5, 5, "Finalize package result")
            self._set_llm_metrics_phase("step5_finalize")
            self._finalize_llm_metrics(step_times)
            self._emit_progress("done", "Пакет сформирован", "", pct=100, status="done")

            books_used = {}
            for page in selected_pages:
                books_used[page["book_id"]] = page["book_title"]
            sources_used = [{"book_id": bid, "title": title} for bid, title in books_used.items()]

            return OptimizedPackageResult(
                success=True,
                lecture_content=formatted_lecture,
                lab_content=lab_content,
                selfcheck_content=selfcheck_content,
                moodle_questions_xml=moodle_xml,
                concept_cards=concept_cards,
                citations=citations,
                sources_used=sources_used,
                generation_time_seconds=time.time() - start_time,
                confidence_score=confidence,
                step_times=step_times,
                warnings=warnings,
                errors=errors,
                review_report_content=review_report,
                cached_pages_used=total_cached_pages,
                extracted_pages_count=total_extracted_pages,
                toc_cache_hit=(toc_cache_hits > 0),
                presentation_slides_json=presentation_slides_json,
                presentation_pptx=presentation_pptx,
            )
        except Exception as e:
            logger.error(f"Error in optimized package generation: {e}", exc_info=True)
            errors.append(str(e))
            self._emit_progress("error", "Ошибка генерации", str(e), status="error")
            self._finalize_llm_metrics(step_times)
            return OptimizedPackageResult(
                success=False,
                lecture_content="",
                lab_content="",
                selfcheck_content="",
                moodle_questions_xml="",
                concept_cards=[],
                citations=[],
                sources_used=[],
                generation_time_seconds=time.time() - start_time,
                confidence_score=0.0,
                step_times=step_times,
                warnings=warnings,
                errors=errors,
                review_report_content=""
            )
        finally:
            self._progress_callback = prev_cb
            try:
                restore_llm_metrics()
            except Exception:
                pass

    async def _filter_concepts_by_theme(self, theme: str, concepts: List[str]) -> List[str]:
        """
        Extra LLM step to keep concepts aligned with `theme`,
        while avoiding semantic duplicates after rule-based deduplication.
        """
        if not concepts:
            return []

        import os
        import json
        import re

        # Keep input size bounded (still "no page limiters", just keeps the filter prompt sane)
        max_input_concepts = int(os.getenv("MAX_CONCEPTS_FOR_THEME_FILTER_INPUT", "60"))
        concepts_in = concepts[:max_input_concepts]

        try:
            min_keep = int(os.getenv("MIN_CONCEPTS_FOR_THEME_FILTER", "4"))
            max_keep = int(os.getenv("MAX_CONCEPTS_FOR_THEME_FILTER_OUTPUT", "12"))
            min_keep = max(1, min(min_keep, max_keep))

            numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(concepts_in)])
            prompt = f"""Тема лекции: "{theme}"

Кандидаты (нумерация 1..N):
{numbered}

Задача:
- Выбери концепции, которые максимально помогают раскрыть именно ЭТУ тему.
- Не сокращай до 1 пункта. Верни минимум {min_keep} и максимум {max_keep} концепций.
- Если есть сомнение, выбирай ближайшие по смыслу к теме (пусть даже не идеально), чтобы сохранить полноту.
- УДАЛЯЙ дубли и почти-дубли (синонимы, перефраз, "X" и "коэффициент X" без новой сути).
- Сохраняй разнообразие: механизмы/процессы важнее вторичных повторов параметров.
- Не выбирай два пункта с одинаковым смыслом.
- Не выбирай одновременно sibling-концепты из одного семейства:
  - "адиабатический инвариант" и "адиабатическая инвариантность"
  - "дрейф частиц" и "дрейф в неоднородном магнитном поле"
  - "отражение частиц" и "отражение от магнитной пробки"
  Оставляй только более конкретный и физически содержательный вариант.

Формат результата: объект с полем keep, где keep — список индексов.
"""

            parsed = await self._generate_json_object(
                prompt,
                {"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            )
            if not parsed:
                return concepts_in
            keep = parsed.get("keep", [])

            if not isinstance(keep, list):
                return concepts_in

            keep_indices = []
            for x in keep:
                try:
                    keep_indices.append(int(x) - 1)  # model uses 1-based indices
                except Exception:
                    continue

            keep_indices = [i for i in keep_indices if 0 <= i < len(concepts_in)]
            # Preserve original order from `concepts_in`
            keep_indices_set = set(keep_indices)
            filtered = [c for i, c in enumerate(concepts_in) if i in keep_indices_set]

            # Helpful debugging: show what the filter kept
            logger.info(
                "Theme-filter keep indices "
                f"(len={len(keep_indices)}): {keep_indices[:20]}"
            )
            logger.info(
                "Theme-filter kept concepts: "
                f"{[filtered[i][:80] for i in range(min(len(filtered), 10))]}"
            )

            # Safety floor: if the model under-selects heavily, revert to unfiltered list.
            if len(filtered) < min_keep:
                logger.warning(
                    "Theme-filter under-selected concepts "
                    f"(kept {len(filtered)} < min_keep={min_keep}); falling back to unfiltered concepts"
                )
                return concepts_in

            # Also cap output length (in case the model returns too many)
            if len(filtered) > max_keep:
                filtered = filtered[:max_keep]

            return filtered
        except Exception as e:
            logger.warning(f"Theme concept filtering failed, fallback to unfiltered: {e}")
            return concepts_in
    
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
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)}
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
        
        # Step 3: Merge/ban sibling concepts (keep one representative per family)
        sibling_patterns = [
            ["адиабатический инвариант", "адиабатическая инвариантность", "адиабатичность"],
            ["дрейф частиц", "дрейф в неоднородном магнитном поле", "градиентный дрейф", "дрейф кривизны"],
            ["отражение частиц", "отражение от магнитной пробки", "магнитное зеркало"],
            ["пробкотрон", "магнитная пробка", "магнитная ловушка"],
            ["запертые частицы", "захваченные частицы", "конус потерь", "опасный конус потерь"],
        ]

        sibling_collapsed = []
        family_used = set()
        for concept in merged:
            c_low = concept.lower().strip()
            family_id = None
            for idx, fam in enumerate(sibling_patterns):
                if any(token in c_low for token in fam):
                    family_id = idx
                    break

            if family_id is not None:
                if family_id in family_used:
                    continue
                family_used.add(family_id)

            sibling_collapsed.append(concept)

        logger.info(f"Deduplication details:")
        logger.info(f"  Original: {len(concepts)} concepts")
        logger.info(f"  After normalization: {len(unique_concepts)} concepts")
        logger.info(f"  After merging similar: {len(merged)} concepts")
        logger.info(f"  After sibling collapse: {len(sibling_collapsed)} concepts")
        
        return sibling_collapsed
    
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
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)}
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
    
    async def _elaborate_concepts_batched(
        self,
        theme: str,
        all_concepts: List[str],
        concept_claims: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> str:
        """Phase 1B: Elaborate concepts in configurable parallel batches."""
        import time

        pipeline_mode = (settings.pipeline_mode or "claims").strip().lower()
        if (
            pipeline_mode == "facet_rag"
            and bool(settings.facet_rag_section_per_facet)
            and all_concepts
        ):
            return await self._elaborate_sections_per_facet(
                theme=theme,
                facets=all_concepts,
                concept_claims=concept_claims or {},
            )

        BATCH_SIZE = max(1, int(settings.elaboration_batch_size))
        PARALLEL_BATCHES = max(1, int(settings.elaboration_parallel_batches))
        
        logger.info(f"Elaborating {len(all_concepts)} concepts")
        logger.info(f"Batch size: {BATCH_SIZE}, Parallel: {PARALLEL_BATCHES}")
        
        # Create fixed-size concept batches (small batches improve focus and reduce drift)
        concept_batches = []
        for i in range(0, len(all_concepts), BATCH_SIZE):
            concept_batches.append(all_concepts[i:i + BATCH_SIZE])
        
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
                task = self._elaborate_concept_batch(
                    theme, concept_batch, global_batch_num, concept_claims or {}
                )
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

    async def _elaborate_sections_per_facet(
        self,
        theme: str,
        facets: List[str],
        concept_claims: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Facet mode: one request per facet, then concatenate sections."""
        parallel = max(1, int(settings.elaboration_parallel_batches))
        if (
            bool(getattr(settings, "facet_section_hallucination_enabled", True))
            and bool(getattr(settings, "facet_section_serial_when_hallucination_check", True))
        ):
            parallel = 1
        body_target_tokens = max(1, int(settings.chunk_rag_body_target_tokens))
        per_facet_target = max(320, int(body_target_tokens / max(1, len(facets))))
        logger.info(
            f"Facet mode: section-per-facet enabled, facets={len(facets)}, "
            f"parallel={parallel}, per_facet_target_tokens={per_facet_target}"
        )
        self._last_facet_hallucination_metrics = {}

        sem = asyncio.Semaphore(parallel)

        async def _run_one(idx: int, facet: str) -> tuple[int, str]:
            async with sem:
                text = await self._elaborate_single_facet(
                    theme=theme,
                    facet=facet,
                    facet_num=idx + 1,
                    concept_claims=concept_claims,
                    per_facet_target_tokens=per_facet_target,
                )
                return idx, text

        results = await asyncio.gather(*[_run_one(i, f) for i, f in enumerate(facets)])
        results.sort(key=lambda x: x[0])
        self._last_facet_sections_map = {
            facets[idx]: (txt or "") for idx, txt in results if idx < len(facets)
        }
        sections = [txt for _, txt in results if (txt or "").strip()]
        combined = f"""## Основные концепции

""" + "\n\n".join(sections)
        logger.info(f"✓ Combined facet sections: {len(combined.split())} words total")
        return combined

    def _claims_evidence_word_count(self, claims: List[Dict[str, Any]]) -> int:
        parts = [re.sub(r"\s+", " ", str(c.get("text", "") or "")).strip() for c in claims]
        return len(" ".join(p for p in parts if p).split())

    def _format_numbered_claims(self, claims: List[Dict[str, Any]], max_items: int = 12) -> str:
        lines: List[str] = []
        for idx, claim in enumerate(claims[:max_items], start=1):
            text = re.sub(r"\s+", " ", str(claim.get("text", "") or "")).strip()
            if not text:
                continue
            page = int(claim.get("page", 0) or 0)
            page_hint = f" (стр. {page})" if page > 0 else ""
            lines.append(f"{idx}. {text}{page_hint}")
        return "\n".join(lines) if lines else "- [нет собранных утверждений]"

    def _facet_effective_min_words(
        self,
        per_facet_target_tokens: int,
        claims: List[Dict[str, Any]],
    ) -> int:
        configured = max(
            int(settings.chunk_rag_facet_section_min_words),
            int(per_facet_target_tokens // 6),
        )
        claims_words = self._claims_evidence_word_count(claims)
        if claims_words <= 0:
            return min(configured, 100)
        ratio = float(getattr(settings, "chunk_rag_facet_evidence_word_cap_ratio", 1.35) or 1.35)
        evidence_cap = max(80, int(claims_words * ratio))
        effective = min(configured, evidence_cap)
        if effective < configured:
            logger.info(
                "Facet min_words capped by evidence: %s -> %s (claims_words=%s)",
                configured,
                effective,
                claims_words,
            )
        return effective

    def _text_token_set(self, text: str) -> set[str]:
        normalized = re.sub(r"\s+", " ", (text or "").lower())
        return set(re.findall(r"[a-zа-яё0-9]+", normalized))

    def _jaccard_token_similarity(self, left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _split_grounding_sentences(self, text: str, min_len: int = 35) -> List[str]:
        cleaned = re.sub(r"<!--[\s\S]*?-->", "", text or "")
        raw = re.split(r"(?<=[\.\!\?])\s+", cleaned)
        return [s.strip() for s in raw if len(s.strip()) >= min_len]

    def _section_body_for_grounding_check(self, section_markdown: str) -> str:
        lines: List[str] = []
        for line in (section_markdown or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(line)
        return re.sub(r"<!--[\s\S]*?-->", "", "\n".join(lines)).strip()

    @staticmethod
    def _sentence_is_grounded(
        jaccard_score: float,
        embedding_score: float,
        *,
        jaccard_min: float,
        embedding_min: float,
        mode: str,
    ) -> bool:
        """hybrid = lexical OR semantic (common when LLM paraphrases chunks)."""
        m = (mode or "hybrid").strip().lower()
        if m == "jaccard":
            return jaccard_score >= jaccard_min
        if m == "embedding":
            return embedding_score >= embedding_min
        return jaccard_score >= jaccard_min or embedding_score >= embedding_min

    def _should_skip_grounding_sentence(self, sentence: str) -> bool:
        """Skip short / transitional sentences (RAG evaluators often exclude boilerplate)."""
        s = (sentence or "").strip()
        if len(s) < 45:
            return True
        if len(self._text_token_set(s)) < 5:
            return True
        lowered = s.lower()
        skip_prefixes = (
            "понимание ",
            "это позволяет",
            "таким образом",
            "важно отметить",
            "следует отметить",
            "практическая ценность",
        )
        return any(lowered.startswith(p) for p in skip_prefixes)

    def _normalize_embedding_matrix(self, encoded: Any) -> np.ndarray:
        """Ensure shape (n_vectors, dim); ST/mock may return 1d for a single string."""
        if encoded is None:
            return np.zeros((0, 0), dtype=float)
        arr = np.asarray(encoded, dtype=float)
        if arr.size == 0:
            return np.zeros((0, 0), dtype=float)
        if arr.ndim == 1:
            return arr.reshape(1, -1)
        return arr

    def _max_cosine_to_matrix(self, query_vec: Any, matrix: Any) -> float:
        mat = self._normalize_embedding_matrix(matrix)
        if mat.shape[0] == 0:
            return 0.0
        q = np.asarray(query_vec, dtype=float).reshape(-1)
        qn = float(np.linalg.norm(q))
        if qn <= 0:
            return 0.0
        norms = np.linalg.norm(mat, axis=1)
        valid = norms > 0
        if not np.any(valid):
            return 0.0
        dots = mat[valid] @ q / (norms[valid] * qn)
        return float(np.max(dots)) if len(dots) else 0.0

    async def _measure_facet_hallucination(
        self,
        section_markdown: str,
        claims: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Hallucination rate = share of scored body sentences not supported by claim chunks.
        hybrid mode: sentence grounded if Jaccard>=min OR cosine(emb)>=min (Self-RAG / RAGAS-style).
        """
        body = self._section_body_for_grounding_check(section_markdown)
        sentences = [
            s for s in self._split_grounding_sentences(body) if not self._should_skip_grounding_sentence(s)
        ]
        claim_texts: List[str] = []
        claim_token_sets: List[set[str]] = []
        for claim in claims:
            text = re.sub(r"\s+", " ", str(claim.get("text", "") or "")).strip()
            if text:
                claim_texts.append(text)
                claim_token_sets.append(self._text_token_set(text))
        if not claim_token_sets:
            claim_token_sets.append(self._text_token_set(body))
            if body:
                claim_texts.append(body)

        jaccard_min = float(
            getattr(settings, "facet_section_hallucination_similarity_min", 0.07) or 0.07
        )
        embedding_min = float(
            getattr(settings, "facet_section_hallucination_embedding_min", 0.52) or 0.52
        )
        grounding_mode = str(
            getattr(settings, "facet_section_hallucination_grounding_mode", "hybrid") or "hybrid"
        ).strip().lower()
        use_embeddings = grounding_mode in ("embedding", "hybrid") and bool(claim_texts)
        claim_embeddings = None
        if use_embeddings and self.model_manager:
            try:
                emb_model = await self.model_manager.get_embedding_model()
                claim_embeddings = self._normalize_embedding_matrix(
                    emb_model.encode(claim_texts)
                )
            except Exception as ex:
                logger.warning("Facet grounding embeddings unavailable: %s", ex)
                use_embeddings = False

        sentence_embeddings = None
        if use_embeddings and sentences and claim_embeddings is not None:
            try:
                emb_model = await self.model_manager.get_embedding_model()
                sentence_embeddings = self._normalize_embedding_matrix(
                    emb_model.encode(sentences[:80])
                )
            except Exception as ex:
                logger.warning("Facet sentence embeddings failed: %s", ex)
                use_embeddings = False

        supported = 0
        unsupported = 0
        skipped = 0
        details: List[Dict[str, Any]] = []
        for idx, sent in enumerate(sentences[:80]):
            s_tokens = self._text_token_set(sent)
            best_jaccard = 0.0
            for c_tokens in claim_token_sets:
                score = self._jaccard_token_similarity(s_tokens, c_tokens)
                if score > best_jaccard:
                    best_jaccard = score
            best_embedding = 0.0
            if use_embeddings and sentence_embeddings is not None and claim_embeddings is not None:
                best_embedding = self._max_cosine_to_matrix(
                    sentence_embeddings[idx, :], claim_embeddings
                )
            is_supported = self._sentence_is_grounded(
                best_jaccard,
                best_embedding,
                jaccard_min=jaccard_min,
                embedding_min=embedding_min,
                mode=grounding_mode,
            )
            if is_supported:
                supported += 1
            else:
                unsupported += 1
            details.append(
                {
                    "sentence": sent[:400],
                    "jaccard": round(best_jaccard, 4),
                    "embedding": round(best_embedding, 4),
                    "similarity": round(max(best_jaccard, best_embedding), 4),
                    "supported": is_supported,
                }
            )

        skipped = max(0, len(self._split_grounding_sentences(body)) - len(sentences[:80]))
        checked = supported + unsupported
        if checked == 0:
            return {
                "sentences_checked": 0,
                "supported_sentences": 0,
                "unsupported_sentences": 0,
                "sentences_skipped": skipped,
                "grounded_rate": 1.0,
                "hallucination_rate": 0.0,
                "grounding_mode": grounding_mode,
                "details": [],
            }
        grounded_rate = supported / checked
        return {
            "sentences_checked": checked,
            "supported_sentences": supported,
            "unsupported_sentences": unsupported,
            "sentences_skipped": skipped,
            "grounded_rate": round(grounded_rate, 4),
            "hallucination_rate": round(unsupported / checked, 4),
            "jaccard_threshold": jaccard_min,
            "embedding_threshold": embedding_min,
            "similarity_threshold": jaccard_min,
            "grounding_mode": grounding_mode,
            "details": details,
        }

    def _facet_grounding_rules(self) -> str:
        return """Правила опоры на источник:
- Используй только факты из списка ОПОРНЫХ УТВЕРЖДЕНИЙ (и черновика, если он уже содержит эти факты)
- Не добавляй формулы, имена, даты, шаги алгоритма и оценки, которых нет в списке
- Для увеличения объёма: перефразируй, группируй и связывай пункты списка, без новых утверждений
- Если данных недостаточно для детали, пропусти её или укажи одной короткой фразой, что в источнике это не раскрыто"""

    def _facet_coverage_checklist(self, facet: str, theme: str) -> str:
        """Theme-specific must-cover items (when present in evidence)."""
        facet_l = (facet or "").lower()
        theme_l = (theme or "").lower()
        code_m = re.match(r"^(\d+\.\d+)", (facet or "").strip())
        code = code_m.group(1) if code_m else ""

        if code == "2.1" or ("2.1" in facet_l and "уязвим" in facet_l):
            return """
ОБЯЗАТЕЛЬНОЕ ПОКРЫТИЕ (включи явно, если есть в опорных утверждениях):
- Определение уязвимости; связь с триадой CIA
- Стандарты идентификации: CVE, CWE (CAPEC — если есть в опоре)
- Оценка критичности: CVSS (уровни: низкий / средний / высокий / критический)
- Жизненный цикл уязвимости и zero-day (кратко)
"""
        if code == "2.2" or ("2.2" in facet_l and "угроз" in facet_l):
            return """
ОБЯЗАТЕЛЬНОЕ ПОКРЫТИЕ (включи явно, если есть в опорных утверждениях):
- Чёткое различие **угроза** vs **атака** (таблица из 2 строк или 2 абзаца с определениями)
- Классификация угроз: по источнику (инсайдер / внешний), по CIA
ЗАПРЕЩЕНО: классификация «прямые / непрямые угрозы» — не использовать.
"""
        if code == "2.3" or ("2.3" in facet_l and "атак" in facet_l):
            return """
ОБЯЗАТЕЛЬНОЕ ПОКРЫТИЕ (включи явно, если есть в опорных утверждениях):
- **Пассивные** vs **активные** атаки (определения + по 1 примеру)
- Хотя бы одна таксономия: STRIDE, MITRE ATT&CK или Cyber Kill Chain (кратко, 1 абзац)
- Методы защиты от атак (если в названии фасета или опоре)
"""
        if "уязвим" in theme_l and "угроз" in theme_l and "атак" in theme_l:
            return """
ОБЯЗАТЕЛЬНОЕ ПОКРЫТИЕ (по фасету, если есть в опоре):
- Уязвимости: CVE/CWE/CVSS; угрозы vs атаки; пассивные/активные атаки; STRIDE или ATT&CK
ЗАПРЕЩЕНО: «прямые / непрямые угрозы».
"""
        return ""

    def _strip_forbidden_facet_content(self, text: str) -> str:
        """Remove LLM-invented classifications we explicitly forbid."""
        if not text:
            return text
        out_lines: List[str] = []
        skip_block = False
        for line in text.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if re.match(r"^\*\*\d+\.", stripped) or re.match(r"^\d+\.\s+\*\*", stripped):
                if any(k in lower for k in ("непрям", "прям", "прямые", "непрямые")):
                    if "угроз" in lower or "воздейств" in lower:
                        skip_block = True
                        continue
                skip_block = False
            if skip_block:
                if stripped.startswith("**") and re.match(r"^\*\*\d+\.", stripped):
                    skip_block = False
                elif stripped.startswith("###") or stripped.startswith("##"):
                    skip_block = False
                else:
                    continue
            if re.match(r"^[-*]\s+", stripped) and any(
                k in lower for k in ("непрям", "прямые угроз", "непрямые угроз", "прямые —", "непрямые —")
            ):
                continue
            if "непрямые" in lower and "угроз" in lower and len(stripped) < 120:
                continue
            if "прямые" in lower and "угроз" in lower and "непрям" not in lower and len(stripped) < 120:
                continue
            out_lines.append(line)
        cleaned = "\n".join(out_lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned if cleaned else text

    async def _expand_facet_evidence_locked(
        self,
        theme: str,
        facet: str,
        draft: str,
        claims: List[Dict[str, Any]],
        min_words: int,
        target_words: int,
    ) -> str:
        claims_block = self._format_numbered_claims(claims)
        coverage = self._facet_coverage_checklist(facet, theme)
        llm_model = await self.model_manager.get_llm_model()
        expand_prompt = f"""Расширь раздел конспекта по теме "{theme}" для фасета "{facet}".

ЧЕРНОВИК (сохрани корректные факты):
{draft}

ОПОРНЫЕ УТВЕРЖДЕНИЯ ИЗ КНИГИ (единственный источник новых фактов):
{claims_block}

{self._facet_grounding_rules()}
{coverage}

ТРЕБОВАНИЯ:
- Верни полный раздел markdown, начинается с заголовка "### {facet}"
- Объём тела: ориентир {min_words}–{target_words} слов за счёт перефразирования списка
- Структура: 3–5 абзацев; не телеграфные теги
- Не используй «прямые / непрямые угрозы»
- Формат ответа: только markdown раздела
"""
        expand_response = await self._llm_generate_with_timeout(
            llm_model,
            log_label=f"facet_expand:{facet[:40]}",
            model=settings.llm_model,
            prompt=expand_prompt,
            options={"temperature": 0.08, "num_ctx": int(settings.llm_num_ctx)},
        )
        return (expand_response.get("response", "") or "").strip()

    async def _generate_facet_section_json(
        self,
        theme: str,
        facet: str,
        claims_block: str,
        min_words: int,
        target_words: int,
        regen_hints: Optional[List[str]] = None,
    ) -> str:
        regen_block = ""
        if regen_hints:
            samples = "\n".join([f"- {s[:220]}" for s in regen_hints[:6]])
            regen_block = f"""
ПРЕДЫДУЩАЯ ВЕРСИЯ СОДЕРЖАЛА НЕПОДТВЕРЖДЁННЫЕ ФРАЗЫ (не повторяй их дословно):
{samples}
"""
        coverage = self._facet_coverage_checklist(facet, theme)
        prompt = f"""Составь раздел конспекта по теме "{theme}" для фасета "{facet}".

ОПОРНЫЕ УТВЕРЖДЕНИЯ ИЗ КНИГИ:
{claims_block}

{self._facet_grounding_rules()}
{coverage}
{regen_block}
ТРЕБОВАНИЯ:
- Текст раскрывает фасет "{facet}" через опорные утверждения и чеклист выше
- Формат раздела: markdown, начинается с заголовка "### {facet}"
- Объём тела (после заголовка): ориентир {min_words}–{target_words} слов
- Структура: 3–5 связных абзацев; markdown-таблица допустима для «угроза vs атака»
- Списки — только если в опоре есть перечисление; иначе связный текст
- Стиль: нейтральный учебный конспект, не телеграфные теги
- Не используй классификацию «прямые / непрямые угрозы»
"""
        payload = await self._generate_json_object(
            prompt=prompt,
            options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            log_label=f"facet_section:{facet[:40]}",
        )
        result = str(payload.get("section_markdown", "") or "").strip()
        if not result:
            retry_payload = await self._generate_json_object(
                prompt=(
                    f'Верни объект с полем "section_markdown" для фасета "{facet}". '
                    f'Текст должен начинаться с заголовка "### {facet}" и содержать '
                    f"не менее {min_words} слов в теле раздела."
                ),
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
                log_label=f"facet_section_retry:{facet[:40]}",
            )
            result = str(retry_payload.get("section_markdown", "") or "").strip()
        return result

    async def _elaborate_single_facet(
        self,
        theme: str,
        facet: str,
        facet_num: int,
        concept_claims: Dict[str, List[Dict[str, Any]]],
        per_facet_target_tokens: int,
    ) -> str:
        norm = self._normalize_heading(facet)
        claims = concept_claims.get(norm, [])
        claims_block = self._format_numbered_claims(claims)
        min_words = self._facet_effective_min_words(per_facet_target_tokens, claims)
        target_words = max(min_words + 40, int(per_facet_target_tokens / 1.6))
        target_words = min(target_words, max(min_words, int(self._claims_evidence_word_count(claims) * 1.35) + 20))
        hall_enabled = bool(getattr(settings, "facet_section_hallucination_enabled", True))
        hall_threshold = float(
            getattr(settings, "facet_section_hallucination_threshold", 0.35) or 0.35
        )
        hall_min_sentences = int(
            getattr(settings, "facet_section_hallucination_min_sentences", 4) or 4
        )
        max_regens = max(
            0, int(getattr(settings, "facet_section_hallucination_max_regenerations", 2) or 0)
        )
        regen_strategy = str(
            getattr(settings, "facet_section_hallucination_regen_strategy", "adaptive") or "adaptive"
        ).strip().lower()
        try:
            best_result = ""
            best_hallucination = 1.0
            best_diag: Dict[str, Any] = {}
            regen_hints: List[str] = []
            regenerations = 0
            final_diag: Dict[str, Any] = {}
            regen_target_words = target_words

            for attempt in range(max_regens + 1):
                if attempt == 0:
                    result = await self._generate_facet_section_json(
                        theme=theme,
                        facet=facet,
                        claims_block=claims_block,
                        min_words=min_words,
                        target_words=target_words,
                    )
                else:
                    use_evidence_locked = regen_strategy == "evidence_locked" or (
                        regen_strategy == "adaptive"
                        and best_hallucination > 0.5
                        and bool(best_result)
                    )
                    if use_evidence_locked and claims:
                        logger.info(
                            f"  Facet {facet_num}: evidence-locked regen "
                            f"(strategy={regen_strategy}, best_hall={best_hallucination:.2%})"
                        )
                        result = await self._expand_facet_evidence_locked(
                            theme=theme,
                            facet=facet,
                            draft=best_result,
                            claims=claims,
                            min_words=min_words,
                            target_words=regen_target_words,
                        )
                    else:
                        result = await self._generate_facet_section_json(
                            theme=theme,
                            facet=facet,
                            claims_block=claims_block,
                            min_words=min_words,
                            target_words=regen_target_words,
                            regen_hints=regen_hints or None,
                        )
                if not result and claims:
                    bullet = "\n".join(
                        [
                            f"- {re.sub(r'\s+', ' ', str(c.get('text', '') or '')).strip()}"
                            for c in claims[:6]
                            if str(c.get("text", "") or "").strip()
                        ]
                    )
                    result = f"### {facet}\n\n{bullet}"
                if not result.startswith("###"):
                    result = f"### {facet}\n\n{result}".strip()

                body_words = self._count_markdown_body_words(result)
                claims_words = self._claims_evidence_word_count(claims)
                if (
                    attempt == 0
                    and body_words < min_words
                    and self.model_manager
                    and claims_words >= 40
                    and regen_strategy != "evidence_locked"
                ):
                    logger.info(
                        f"  Facet {facet_num}: section too short ({body_words} < {min_words}), "
                        f"evidence-locked expand (claims_words={claims_words})"
                    )
                    expanded = await self._expand_facet_evidence_locked(
                        theme=theme,
                        facet=facet,
                        draft=result,
                        claims=claims,
                        min_words=min_words,
                        target_words=target_words,
                    )
                    if expanded:
                        if not expanded.startswith("###"):
                            expanded = f"### {facet}\n\n{expanded}".strip()
                        expanded_words = self._count_markdown_body_words(expanded)
                        if expanded_words >= body_words:
                            result = expanded
                            body_words = expanded_words

                diag = await self._measure_facet_hallucination(result, claims)
                final_diag = diag
                hall_rate = float(diag.get("hallucination_rate", 0.0) or 0.0)
                if hall_rate <= best_hallucination:
                    best_hallucination = hall_rate
                    best_result = result
                    best_diag = diag

                logger.info(
                    f"  Facet {facet_num} attempt {attempt + 1}: "
                    f"body_words={body_words}, hallucination_rate={hall_rate:.2%}, "
                    f"grounded_rate={float(diag.get('grounded_rate', 0.0) or 0.0):.2%}"
                )

                if not hall_enabled or hall_threshold < 0:
                    break
                if int(diag.get("sentences_checked", 0) or 0) < hall_min_sentences:
                    break
                if hall_rate <= hall_threshold:
                    break
                if attempt > 0 and hall_rate >= 0.9 and best_hallucination <= 0.6:
                    logger.warning(
                        f"  Facet {facet_num}: regen degraded badly "
                        f"({hall_rate:.2%} vs best {best_hallucination:.2%}), stop retries"
                    )
                    break
                if attempt > 0 and hall_rate > best_hallucination + 0.2:
                    logger.warning(
                        f"  Facet {facet_num}: regen worse than best "
                        f"({hall_rate:.2%} > {best_hallucination:.2%}), stop retries"
                    )
                    break
                if attempt >= max_regens:
                    logger.warning(
                        f"  Facet {facet_num}: hallucination_rate {hall_rate:.2%} "
                        f"still above {hall_threshold:.2%} after {max_regens} regen(s); "
                        f"keeping best attempt ({best_hallucination:.2%})"
                    )
                    break

                regenerations += 1
                regen_hints = [
                    str(d.get("sentence", "") or "")
                    for d in (diag.get("details") or [])
                    if not d.get("supported")
                ]
                regen_target_words = max(min_words, int(regen_target_words * 0.85))
                logger.info(
                    f"  Facet {facet_num}: regen {regenerations}/{max_regens} "
                    f"(hallucination_rate {hall_rate:.2%} > {hall_threshold:.2%}, "
                    f"target_words<={regen_target_words})"
                )

            result = best_result or result
            result = self._strip_forbidden_facet_content(result)
            final_diag = best_diag or final_diag
            self._last_facet_hallucination_metrics[facet] = {
                **final_diag,
                "facet": facet,
                "regenerations": regenerations,
                "threshold": hall_threshold,
                "accepted": (
                    float(
                        final_diag.get("hallucination_rate")
                        if final_diag.get("hallucination_rate") is not None
                        else 1.0
                    )
                    <= hall_threshold
                    or int(final_diag.get("sentences_checked", 0) or 0) < hall_min_sentences
                ),
            }
            logger.info(
                f"  Facet {facet_num}: final body_words={self._count_markdown_body_words(result)}, "
                f"hallucination_rate={float(final_diag.get('hallucination_rate', 0.0) or 0.0):.2%}, "
                f"regenerations={regenerations}"
            )
            return result
        except TimeoutError as e:
            logger.error(f"Facet {facet_num} timed out: {e}")
            if best_result:
                return best_result
            return f"### {facet}\n[Таймаут генерации раздела]"
        except Exception as e:
            logger.error(f"Error elaborating facet {facet_num}: {e}")
            if best_result:
                return best_result
            return f"### {facet}\n[Ошибка генерации раздела]"
    
    async def _elaborate_concept_batch(
        self,
        theme: str,
        concept_batch: List[str],
        batch_num: int,
        concept_claims: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Elaborate a single batch of concepts"""
        logger.info(f"  Batch {batch_num}: Elaborating {len(concept_batch)} concepts")
        
        concepts_payload: List[str] = []
        for concept in concept_batch:
            norm = self._normalize_heading(concept)
            claims = concept_claims.get(norm, [])
            claims_text = "\n".join([f"  - {c.get('text', '')}" for c in claims if c.get("text")])
            concepts_payload.append(
                f"- {concept}\n  Утверждения из книги:\n{claims_text or '  - [нет собранных утверждений]'}"
            )
        concepts_list = "\n".join(concepts_payload)
        
        prompt = f"""Составь КОНСПЕКТ по следующим концепциям темы "{theme}":

{concepts_list}

ТРЕБОВАНИЯ:
- Объясни ТОЛЬКО эти концепции из списка
- Опирайся в первую очередь на "Утверждения из книги" для каждого концепта
- Не игнорируй утверждения; расширяй их объяснениями и примерами
- Пиши в формате учебного конспекта, а не как устный сценарий лекции
- БЕЗ обращений к аудитории ("уважаемые коллеги", "давайте разберем")
- БЕЗ фраз-паразитов ("конечно", "сегодня мы", "в этой лекции")
- БЕЗ нумерации (1., 2., 3.)
- Используй заголовки: ### Название концепции
- Сразу начинай с первой концепции
- Пиши на русском языке (без английских вставок)
- Старайся полно раскрыть ключевые идеи и добавить практические примеры, если это уместно
- (TRY TO FULLY DESCRIBE THE CORE CONCEPTS WITH PRACTICE IF POSSIBLE)
- Структурированное изложение с примерами и практической ценностью
- Не добавляй сведения, которых нет в "Утверждениях из книги"
- Для каждого концепта: 2-4 абзаца предметного текста, без воды
- Для каждого концепта: цель по содержанию в пределах 220-360 выходных токенов
- Если фактов по концепту недостаточно, явно зафиксируй ограничение в 1 коротком предложении

ФОРМАТ:
### Название первой концепции
[Объяснение с примерами]

### Название второй концепции
[Объяснение с примерами]

Конспект:"""
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.15, "num_ctx": int(settings.llm_num_ctx)}
            )
            
            result = response.get('response', '').strip()
            completion_tokens = int(response.get("eval_count", 0) or 0)
            if completion_tokens <= 0:
                completion_tokens = len(result.split())
            min_completion_tokens = max(560, 220 * max(1, len(concept_batch)))

            if completion_tokens < min_completion_tokens:
                expand_prompt = f"""Расширь КОНСПЕКТ по теме "{theme}" без добавления новых неподтвержденных фактов.

ТЕКУЩИЙ КОНСПЕКТ:
{result}

УТОЧНЕННЫЕ ИСТОЧНИКИ (утверждения из книги):
{concepts_list}

ТРЕБОВАНИЯ К РАСШИРЕНИЮ:
- Увеличь содержательность, а не "воду"
- Для каждого концепта добавь: определения, механизм, практический пример, типичные ошибки/ограничения (если подтверждается утверждениями)
- Сохрани формат заголовков: ### Название концепции
- Без англоязычных вставок и без обращений к аудитории
- Не выдумывай факты вне утверждений
- Целевой суммарный объем: {min_completion_tokens}-{min_completion_tokens + 700} выходных токенов
- Не раздувай текст повторениями, добавляй только новую предметную конкретику

Верни только обновленный конспект."""
                expand_resp = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=expand_prompt,
                    options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
                )
                expanded = (expand_resp.get("response", "") or "").strip()
                if expanded:
                    result = expanded
                    completion_tokens = int(expand_resp.get("eval_count", 0) or 0)
                    if completion_tokens <= 0:
                        completion_tokens = len(result.split())
                    logger.info(
                        f"  Batch {batch_num}: Expanded to {completion_tokens} completion tokens "
                        f"(target>={min_completion_tokens})"
                    )
            logger.info(f"  Batch {batch_num}: Generated {completion_tokens} completion tokens")
            
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
            prompt = f"""Напиши краткое введение к теме "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

Требования:
- 1 короткий абзац (примерно 3-6 предложений), без подзаголовков и списков
- Нейтральный академический стиль, без обращения к аудитории
- Кратко обозначь: зачем тема важна и какой практический смысл
- НЕ цитируй и НЕ пересказывай дословно фрагменты из "КЛЮЧЕВЫЕ КОНЦЕПЦИИ"
- НЕ перечисляй все разделы; это только вводный контекст
- Допускается только общий смысловой анонс без частных формул и длинных определений"""
            
            try:
                llm_model = await self.model_manager.get_llm_model()
                response = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.2, "num_ctx": int(settings.llm_num_ctx)}
                )
                result = response.get('response', '')
                intro_tokens = int(response.get("eval_count", 0) or 0)
                if intro_tokens <= 0:
                    intro_tokens = len(result.split())
                logger.info(f"✓ Introduction generated: {intro_tokens} completion tokens")
                return result
            except Exception as e:
                logger.error(f"Error generating introduction: {e}")
                return "[Ошибка генерации введения]"
        
        async def generate_conclusion() -> str:
            prompt = f"""Напиши краткое заключение по теме "{theme}".

КЛЮЧЕВЫЕ КОНЦЕПЦИИ:
{core_concepts}

Требования:
- 1 короткий абзац (примерно 3-6 предложений), без подзаголовков и списков
- Нейтральный академический стиль, без обращения к аудитории
- Дай целостный итог: что усвоено и в чем практическая применимость
- НЕ цитируй и НЕ дублируй дословно фрагменты из "КЛЮЧЕВЫЕ КОНЦЕПЦИИ"
- НЕ добавляй новые факты, которых нет в материале
- Не упоминай конкретные будущие темы"""
            
            try:
                llm_model = await self.model_manager.get_llm_model()
                response = await llm_model.generate(
                    model=settings.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.2, "num_ctx": int(settings.llm_num_ctx)}
                )
                result = response.get('response', '')
                concl_tokens = int(response.get("eval_count", 0) or 0)
                if concl_tokens <= 0:
                    concl_tokens = len(result.split())
                logger.info(f"✓ Conclusion generated: {concl_tokens} completion tokens")
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

    async def _polish_core_concepts(
        self,
        theme: str,
        core_concepts: str,
        concept_claims: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Evidence-locked editorial pass: improve flow without adding new facts."""
        if not core_concepts or not self.model_manager:
            return core_concepts
        evidence_lines: List[str] = []
        if concept_claims:
            for concept, claims in concept_claims.items():
                snippets = [
                    str(c.get("text", "") or "").strip()
                    for c in claims[:4]
                    if str(c.get("text", "") or "").strip()
                ]
                if not snippets:
                    continue
                evidence_lines.append(f"### {concept}")
                evidence_lines.extend([f"- {s[:280]}" for s in snippets])
        evidence_block = "\n".join(evidence_lines).strip() or "- [нет отдельного evidence-блока]"
        prompt = f"""Отредактируй фрагмент "Основные концепции" по теме "{theme}".

ТЕКСТ:
{core_concepts}

РАЗРЕШЕННЫЕ ОПОРНЫЕ ФАКТЫ (EVIDENCE):
{evidence_block}

Сделай:
- Сохрани смысл, факты и заголовки разделов `### ...`
- Плавные переходы между разделами, без резких скачков
- Убери повторы и тавтологию
- Сохрани HTML-комментарии происхождения источников как есть
- Смягчи или убери утверждения без опоры в EVIDENCE и исходном тексте
- Используй только факты из EVIDENCE и исходного текста
- Не добавляй новые формулы, шаги алгоритма, имена и даты, которых нет в EVIDENCE

Формат ответа: только markdown-текст раздела "Основные концепции", без предисловий, пояснений редактора и мета-комментариев.
"""
        try:
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model=settings.llm_model,
                prompt=prompt,
                options={"temperature": 0.1, "num_ctx": int(settings.llm_num_ctx)},
            )
            polished = (response.get("response", "") or "").strip()
            if polished:
                polished = self._strip_polish_meta_leakage(polished)
            return polished if polished else core_concepts
        except Exception as e:
            logger.warning(f"Core concepts polish skipped due to error: {e}")
            return core_concepts
    
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

async def get_optimized_content_generator(
    model_manager=None,
    pdf_processor=None,
    use_mock: bool = False
) -> OptimizedContentGenerator:
    """
    Backward-compatible factory.
    Delegates to production generator v4 so all runtime paths use one generator.
    """
    from generation.generator_v4 import get_production_content_generator
    return await get_production_content_generator(
        model_manager=model_manager,
        pdf_processor=pdf_processor,
        use_mock=use_mock,
    )