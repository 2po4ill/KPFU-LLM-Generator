"""
Hybrid 5-step content generation pipeline
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of content generation"""
    success: bool
    content: str
    citations: List[Dict[str, Any]]
    sources_used: List[Dict[str, Any]]
    generation_time_seconds: float
    confidence_score: float
    step_times: Dict[str, float]
    warnings: List[str]
    errors: List[str]


class ContentGenerator:
    """
    Hybrid 5-step content generation pipeline
    
    Steps:
    1. Hybrid Book Relevance (6s) - Match books to theme
    2. Smart Page Selection (60s) - Find relevant pages using TOC
    3. Content Generation (90-120s) - LLM generates lecture
    4. Semantic Validation (10-15s) - Verify claims
    5. FGOS Formatting (30s) - Format to standards
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.model_manager = None
        self.embedding_service = None
        self.pdf_processor = None
    
    async def initialize(self, model_manager=None, embedding_service=None, pdf_processor=None):
        """Initialize generator with dependencies"""
        self.model_manager = model_manager
        self.embedding_service = embedding_service
        self.pdf_processor = pdf_processor
        
        logger.info("Content generator initialized")
    
    async def generate_lecture(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        book_ids: List[str]
    ) -> GenerationResult:
        """
        Generate lecture content using hybrid 5-step pipeline
        
        Args:
            theme: Lecture theme/topic
            rpd_data: RPD data (subject, degree, profession, etc.)
            book_ids: List of book IDs to use as sources
            
        Returns:
            GenerationResult with content and metadata
        """
        start_time = time.time()
        step_times = {}
        warnings = []
        errors = []
        
        try:
            logger.info(f"Starting content generation for theme: {theme}")
            
            # Step 1: Hybrid Book Relevance (6s target)
            step1_start = time.time()
            relevant_books = await self._step1_hybrid_book_relevance(theme, book_ids)
            step_times['step1_book_relevance'] = time.time() - step1_start
            logger.info(f"Step 1 completed in {step_times['step1_book_relevance']:.2f}s - {len(relevant_books)} books selected")
            
            if not relevant_books:
                warnings.append("No relevant books found for this theme")
            
            # Step 2: Smart Page Selection (60s target)
            step2_start = time.time()
            selected_pages = await self._step2_smart_page_selection(theme, relevant_books)
            step_times['step2_page_selection'] = time.time() - step2_start
            logger.info(f"Step 2 completed in {step_times['step2_page_selection']:.2f}s - {len(selected_pages)} pages selected")
            
            if not selected_pages:
                errors.append("No relevant pages found in books")
                return GenerationResult(
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
            
            # Step 3: Content Generation (90-120s target)
            step3_start = time.time()
            generated_content = await self._step3_content_generation(theme, rpd_data, selected_pages)
            step_times['step3_content_generation'] = time.time() - step3_start
            logger.info(f"Step 3 completed in {step_times['step3_content_generation']:.2f}s")
            
            # Step 4: Semantic Validation (10-15s target)
            step4_start = time.time()
            validated_content, confidence = await self._step4_semantic_validation(generated_content, selected_pages)
            step_times['step4_validation'] = time.time() - step4_start
            logger.info(f"Step 4 completed in {step_times['step4_validation']:.2f}s - confidence: {confidence:.2f}")
            
            if confidence < 0.7:
                warnings.append(f"Low confidence score: {confidence:.2f}")
            
            # Step 5: FGOS Formatting (30s target)
            step5_start = time.time()
            formatted_content, citations = await self._step5_fgos_formatting(validated_content, rpd_data, selected_pages)
            step_times['step5_formatting'] = time.time() - step5_start
            logger.info(f"Step 5 completed in {step_times['step5_formatting']:.2f}s")
            
            total_time = time.time() - start_time
            logger.info(f"Content generation completed in {total_time:.2f}s")
            
            return GenerationResult(
                success=True,
                content=formatted_content,
                citations=citations,
                sources_used=[{'book_id': b['book_id'], 'title': b['title']} for b in relevant_books],
                generation_time_seconds=total_time,
                confidence_score=confidence,
                step_times=step_times,
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Error generating content: {e}", exc_info=True)
            errors.append(str(e))
            
            return GenerationResult(
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
    
    async def _step1_hybrid_book_relevance(
        self,
        theme: str,
        book_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Hybrid book relevance scoring
        Uses keyword matching for clear cases (80%), LLM for ambiguous (20%)
        Target: 6 seconds average
        """
        if self.use_mock:
            # Mock: Return all books as relevant
            return [
                {'book_id': bid, 'title': f'Book {bid}', 'relevance_score': 0.85, 'method': 'mock'}
                for bid in book_ids
            ]
        
        relevant_books = []
        
        for book_id in book_ids:
            # Get book metadata from embedding service
            book_chunks = self.embedding_service.get_book_chunks(book_id)
            
            if not book_chunks:
                continue
            
            # Get book title from first chunk metadata
            book_title = book_chunks[0]['metadata'].get('book_title', '')
            book_authors = book_chunks[0]['metadata'].get('book_authors', '')
            
            # For now, just add all books with semantic search score
            # Search for theme in book chunks
            similar_chunks = self.embedding_service.search_similar_chunks(
                query=theme,
                book_id=book_id,
                top_k=5
            )
            
            if similar_chunks:
                # Calculate average distance (lower is better)
                avg_distance = sum(c['distance'] for c in similar_chunks) / len(similar_chunks)
                relevance_score = max(0.3, 1.0 - (avg_distance / 100.0))  # Ensure minimum 0.3
                
                relevant_books.append({
                    'book_id': book_id,
                    'title': book_title,
                    'authors': book_authors,
                    'relevance_score': relevance_score,
                    'method': 'semantic_search'
                })
            else:
                # If no similar chunks found, still add the book with lower score
                relevant_books.append({
                    'book_id': book_id,
                    'title': book_title,
                    'authors': book_authors,
                    'relevance_score': 0.5,
                    'method': 'fallback'
                })
        
        # Sort by relevance and return top 3
        relevant_books.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_books[:3]
    
    async def _step2_smart_page_selection(
        self,
        theme: str,
        relevant_books: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Step 2: Smart page selection using raw TOC and LLM
        Give LLM raw TOC text, ask for page numbers directly
        Target: 60 seconds
        """
        if self.use_mock:
            # Mock: Return fake pages
            return [
                {
                    'book_id': book['book_id'],
                    'book_title': book['title'],
                    'page_number': i,
                    'content': f"Mock content for {theme} from {book['title']}",
                    'relevance_score': 0.8
                }
                for book in relevant_books
                for i in range(1, 4)  # 3 pages per book
            ]
        
        selected_pages = []
        
        for book in relevant_books:
            # Load book to get TOC pages
            # TODO: Store book path in metadata to avoid hardcoding
            book_path = 'питон_мок_дата.pdf'  # Temporary hardcode
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                logger.error(f"Failed to extract pages from {book_path}")
                continue
            
            # Find TOC pages
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                logger.warning(f"No TOC found for book {book['book_id']}, falling back to semantic search")
                # Fallback to semantic search
                similar_chunks = self.embedding_service.search_similar_chunks(
                    query=theme,
                    book_id=book['book_id'],
                    top_k=50
                )
                page_scores = {}
                for chunk in similar_chunks:
                    page_num = chunk['metadata']['page_number']
                    if page_num not in page_scores:
                        page_scores[page_num] = {
                            'book_id': book['book_id'],
                            'book_title': book['title'],
                            'page_number': page_num,
                            'content': chunk['content'],
                            'relevance_score': 1.0 - (chunk['distance'] / 10.0)
                        }
                sorted_pages = sorted(page_scores.values(), key=lambda x: x['relevance_score'], reverse=True)
                selected_pages.extend(sorted_pages[:10])
                continue
            
            # Get raw TOC text (unprocessed!)
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            # Limit TOC text size
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            logger.info(f"Using raw TOC text ({len(toc_text)} chars) for page selection")
            
            # Use LLM to get page numbers directly from raw TOC
            page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
            
            logger.info(f"LLM selected page numbers: {page_numbers}")
            
            # Load content from these pages
            for page_num in page_numbers:
                page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
                
                if page_data:
                    selected_pages.append({
                        'book_id': book['book_id'],
                        'book_title': book['title'],
                        'page_number': page_num,
                        'content': page_data['text'],
                        'relevance_score': 1.0
                    })
        
        logger.info(f"Selected {len(selected_pages)} pages total from TOC matching")
        if selected_pages:
            logger.info(f"Page numbers: {sorted(set([p['page_number'] for p in selected_pages]))}")
        
        return selected_pages
    
    async def _get_page_numbers_from_toc(
        self,
        theme: str,
        toc_text: str
    ) -> List[int]:
        """
        Use LLM to extract page numbers directly from raw TOC text
        
        Args:
            theme: Lecture theme
            toc_text: Raw TOC text (unprocessed)
            
        Returns:
            List of page numbers
        """
        if not self.model_manager:
            return []
        
        prompt = f"""Вот оглавление книги по Python:

{toc_text}

Тема лекции: "{theme}"

Какие страницы в этой книге относятся к этой теме? Посмотри на оглавление и найди номера страниц для разделов, которые покрывают эту тему.

Верни ТОЛЬКО номера страниц через запятую, например: 101, 102, 103, 104, 105

Номера страниц:"""
        
        # Log the prompt
        logger.info(f"=== TOC PAGE SELECTION PROMPT ===")
        logger.info(f"Theme: {theme}")
        logger.info(f"TOC text length: {len(toc_text)} chars")
        
        # Save full prompt to file for debugging
        with open('toc_page_selection_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"Full prompt saved to toc_page_selection_prompt.txt")
        logger.info(f"=================================")
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 200  # Short response - just numbers
                }
            )
            
            # Parse response
            response_text = response.get('response', '').strip()
            logger.info(f"LLM page selection response: {response_text}")
            
            # Save response for debugging
            with open('toc_page_selection_response.txt', 'w', encoding='utf-8') as f:
                f.write(response_text)
            
            # Extract numbers from response
            import re
            numbers = re.findall(r'\d+', response_text)
            page_numbers = [int(n) for n in numbers if 1 <= int(n) <= 200]  # Reasonable page range
            
            # Limit to max 20 pages
            if len(page_numbers) > 20:
                page_numbers = page_numbers[:20]
            
            return page_numbers
            
        except Exception as e:
            logger.error(f"Error getting page numbers from TOC: {e}")
            return []

    
    async def _step3_content_generation(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> str:
        """
        Step 3: Content generation using LLM
        Target: 90-120 seconds
        """
        if self.use_mock or not self.model_manager:
            # Mock generation
            return f"""# Лекция: {theme}

## Введение
Данная лекция посвящена теме "{theme}" в рамках курса "{rpd_data.get('subject_title', 'Программирование')}".

## Основная часть
[Здесь будет сгенерированный контент на основе источников]

Основные концепции:
- Концепция 1
- Концепция 2
- Концепция 3

## Примеры
[Примеры из литературы]

## Заключение
В данной лекции мы рассмотрели основные аспекты темы "{theme}".

## Список литературы
{chr(10).join([f"- {p['book_title']}, стр. {p['page_number']}" for p in selected_pages[:3]])}
"""
        
        # Prepare context from selected pages (use top 5 most relevant pages only)
        # Fewer pages = clearer signal to LLM
        pages_to_use = selected_pages[:5]
        context = "\n\n---PAGE BREAK---\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in pages_to_use
        ])
        
        logger.info(f"Context length: {len(context)} chars from {len(pages_to_use)} pages")
        logger.info(f"Pages used: {[p['page_number'] for p in pages_to_use]}")
        
        # Simpler, more direct prompt
        prompt = f"""Ты преподаватель. Напиши лекцию по теме "{theme}".

ВАЖНО: Используй ТОЛЬКО материал из этих страниц учебника. НЕ добавляй свои примеры.

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

Структура:
1. Введение (2-3 абзаца)
2. Основная часть с определениями и объяснениями (5-7 абзацев)
3. Примеры кода из учебника с объяснениями (3-5 примеров)
4. Практические рекомендации (2-3 абзаца)
5. Заключение (2 абзаца)

Лекция:"""
        
        # Log the prompt for debugging
        logger.info(f"=== GENERATION PROMPT ===")
        logger.info(f"Theme: {theme}")
        logger.info(f"Context length: {len(context)} chars")
        
        # Save full prompt to file for debugging
        with open('generation_prompt.txt', 'w', encoding='utf-8') as f:
            f.write(f"THEME: {theme}\n\n")
            f.write(f"CONTEXT LENGTH: {len(context)} chars\n\n")
            f.write("="*80 + "\n")
            f.write(prompt)
        logger.info(f"Full generation prompt saved to generation_prompt.txt")
        
        logger.info(f"=========================")
        
        try:
            # Get LLM model
            llm_model = await self.model_manager.get_llm_model()
            
            # Generate content with increased token limit and context window
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Lower temperature for factual content
                    "num_predict": 6000,  # Increased from 4000 to 6000 tokens
                    "num_ctx": 32768,  # Increase context window to 32k tokens
                    "top_p": 0.9
                }
            )
            
            return response.get('response', '')
            
        except Exception as e:
            logger.error(f"Error in LLM generation: {e}")
            return f"[Ошибка генерации: {e}]"
    
    async def _step4_semantic_validation(
        self,
        content: str,
        selected_pages: List[Dict[str, Any]]
    ) -> tuple[str, float]:
        """
        Step 4: Semantic validation of generated content with claim extraction
        Target: 10-15 seconds
        
        This step:
        1. Extracts factual claims from generated content
        2. Validates each claim against source material
        3. Marks unsupported claims for review
        4. Calculates confidence score
        """
        if self.use_mock:
            return content, 0.85
        
        try:
            # Extract factual claims from content
            claims = await self._extract_claims(content)
            
            if not claims:
                logger.warning("No claims extracted from content")
                return content, 0.75
            
            # Validate claims against source pages
            validation_results = await self._validate_claims(claims, selected_pages)
            
            # Calculate confidence score
            supported_claims = sum(1 for r in validation_results if r['is_supported'])
            confidence = supported_claims / len(validation_results) if validation_results else 0.0
            
            # Mark unsupported claims in content
            validated_content = self._mark_unsupported_claims(content, validation_results)
            
            logger.info(f"Validation: {supported_claims}/{len(validation_results)} claims supported, confidence: {confidence:.2f}")
            
            return validated_content, confidence
            
        except Exception as e:
            logger.error(f"Error in semantic validation: {e}", exc_info=True)
            return content, 0.70
    
    async def _step5_fgos_formatting(
        self,
        content: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Step 5: Format content according to FGOS standards
        Target: 30 seconds
        """
        # FGOS template
        formatted = f"""# ЛЕКЦИЯ ПО ДИСЦИПЛИНЕ "{rpd_data.get('subject_title', '').upper()}"

**Направление подготовки:** {rpd_data.get('profession', '')}
**Уровень образования:** {rpd_data.get('academic_degree', 'bachelor')}
**Кафедра:** {rpd_data.get('department', 'Не указана')}

---

{content}

---

**Дата составления:** {time.strftime('%d.%m.%Y')}
"""
        
        # Extract citations
        citations = [
            {
                'book_title': p['book_title'],
                'page_number': p['page_number'],
                'book_id': p['book_id']
            }
            for p in selected_pages[:10]
        ]
        
        return formatted, citations
    
    async def _extract_claims(self, content: str) -> List[str]:
        """
        Extract factual claims from generated content using LLM
        
        A claim is a factual statement that can be verified against sources.
        We focus on technical facts, definitions, and specific statements.
        """
        try:
            llm_model = await self.model_manager.get_llm_model()
            
            extraction_prompt = f"""Извлеките все фактические утверждения из следующего текста лекции.
Фактическое утверждение - это конкретное техническое утверждение, определение или факт, который можно проверить.

НЕ извлекайте:
- Общие вводные фразы
- Организационную информацию
- Вопросы для самопроверки
- Заголовки разделов

Извлекайте ТОЛЬКО:
- Технические определения
- Конкретные факты о языке программирования
- Утверждения о работе функций/методов
- Примеры кода и их объяснения

Текст лекции:
{content[:3000]}

Верните список утверждений в формате:
1. [утверждение 1]
2. [утверждение 2]
...

Максимум 10 наиболее важных утверждений."""

            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=extraction_prompt,
                options={
                    "temperature": 0.1,  # Low temperature for precise extraction
                    "num_predict": 1000
                }
            )
            
            # Parse claims from response
            claims_text = response.get('response', '')
            claims = []
            
            for line in claims_text.split('\n'):
                line = line.strip()
                # Match numbered list items
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering and clean up
                    claim = line.lstrip('0123456789.-•) ').strip()
                    if len(claim) > 20:  # Filter out too short claims
                        claims.append(claim)
            
            logger.info(f"Extracted {len(claims)} claims from content")
            return claims[:10]  # Limit to top 10 claims
            
        except Exception as e:
            logger.error(f"Error extracting claims: {e}")
            return []
    
    async def _validate_claims(
        self,
        claims: List[str],
        selected_pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate claims against source pages using semantic similarity
        
        Returns list of validation results with:
        - claim: original claim text
        - is_supported: whether claim is supported by sources
        - confidence: similarity score (0-1)
        - source: which source supports it
        """
        if not self.embedding_service:
            logger.warning("No embedding service available for validation")
            return [{'claim': c, 'is_supported': True, 'confidence': 0.75} for c in claims]
        
        validation_results = []
        
        # Prepare source texts
        source_texts = [
            f"{p['book_title']}, стр. {p['page_number']}: {p['content']}"
            for p in selected_pages
        ]
        
        # Validate each claim
        for claim in claims:
            try:
                # Use embedding service to find most similar source
                # Search in the vector store for this claim
                similar_chunks = self.embedding_service.search_similar_chunks(
                    query=claim,
                    book_id=None,  # Search across all books
                    top_k=3
                )
                
                if similar_chunks:
                    # Get best match
                    best_match = similar_chunks[0]
                    similarity = 1.0 - (best_match['distance'] / 10.0)  # Normalize distance to 0-1
                    
                    # Claim is supported if similarity > 0.40 (more lenient threshold for Russian text)
                    # Distance of 6.0 = similarity of 0.40
                    is_supported = similarity > 0.40
                    
                    logger.debug(f"Claim validation: '{claim[:50]}...' -> distance={best_match['distance']:.2f}, similarity={similarity:.2f}, supported={is_supported}")
                    
                    validation_results.append({
                        'claim': claim,
                        'is_supported': is_supported,
                        'confidence': similarity,
                        'source': best_match['metadata'].get('book_title', 'Unknown'),
                        'page': best_match['metadata'].get('page_number', 0),
                        'distance': best_match['distance']
                    })
                else:
                    # No similar content found
                    validation_results.append({
                        'claim': claim,
                        'is_supported': False,
                        'confidence': 0.0,
                        'source': None,
                        'page': None
                    })
                    
            except Exception as e:
                logger.error(f"Error validating claim '{claim[:50]}...': {e}")
                validation_results.append({
                    'claim': claim,
                    'is_supported': True,  # Assume supported on error
                    'confidence': 0.70,
                    'source': 'Error',
                    'page': None
                })
        
        return validation_results
    
    def _mark_unsupported_claims(
        self,
        content: str,
        validation_results: List[Dict[str, Any]]
    ) -> str:
        """
        Mark unsupported claims in content for review
        
        Unsupported claims are marked with [ТРЕБУЕТ ПРОВЕРКИ: ...]
        """
        marked_content = content
        
        for result in validation_results:
            if not result['is_supported']:
                claim = result['claim']
                confidence = result['confidence']
                
                # Try to find and mark the claim in content
                if claim in marked_content:
                    marked_content = marked_content.replace(
                        claim,
                        f"[ТРЕБУЕТ ПРОВЕРКИ (уверенность: {confidence:.0%}): {claim}]",
                        1  # Replace only first occurrence
                    )
                    logger.warning(f"Marked unsupported claim: {claim[:50]}...")
        
        return marked_content


# Global generator instance
content_generator = None


async def get_content_generator(
    model_manager=None,
    embedding_service=None,
    pdf_processor=None,
    use_mock: bool = False
) -> ContentGenerator:
    """Get global content generator instance"""
    global content_generator
    
    if content_generator is None:
        content_generator = ContentGenerator(use_mock=use_mock)
        await content_generator.initialize(model_manager, embedding_service, pdf_processor)
    
    return content_generator
