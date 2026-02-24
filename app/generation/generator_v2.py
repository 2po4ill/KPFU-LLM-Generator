"""
Simplified 3-step content generation pipeline
Version 2 - No chunking, proper validation
"""

import logging
import time
import numpy as np
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
    Simplified 3-step content generation pipeline
    
    Steps:
    1. Smart Page Selection (60s) - TOC-based, skip irrelevant books
    2. Content Generation (90-120s) - LLM generates lecture
    3. Validation & Formatting (30s) - Validate against used pages + FGOS format
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.model_manager = None
        self.pdf_processor = None
    
    async def initialize(self, model_manager=None, pdf_processor=None, **kwargs):
        """Initialize generator with dependencies"""
        self.model_manager = model_manager
        self.pdf_processor = pdf_processor
        
        logger.info("Content generator v2 initialized (simplified architecture)")
    
    async def generate_lecture(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        book_ids: List[str]
    ) -> GenerationResult:
        """
        Generate lecture content using simplified 3-step pipeline
        
        Args:
            theme: Lecture theme/topic
            rpd_data: RPD data (subject, degree, profession, etc.)
            book_ids: List of book IDs provided by user
            
        Returns:
            GenerationResult with content and metadata
        """
        start_time = time.time()
        step_times = {}
        warnings = []
        errors = []
        
        try:
            logger.info(f"Starting content generation for theme: {theme}")
            logger.info(f"Using books: {book_ids}")
            
            # Step 1: Smart Page Selection (60s target)
            step1_start = time.time()
            selected_pages = await self._step1_smart_page_selection(theme, book_ids)
            step_times['step1_page_selection'] = time.time() - step1_start
            logger.info(f"Step 1 completed in {step_times['step1_page_selection']:.2f}s - {len(selected_pages)} pages selected")
            
            if not selected_pages:
                errors.append("No relevant pages found in provided books")
                warnings.append("Try different books or check if theme matches book content")
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
            
            # Step 2: Content Generation (90-120s target)
            step2_start = time.time()
            generated_content = await self._step2_content_generation(theme, rpd_data, selected_pages)
            step_times['step2_content_generation'] = time.time() - step2_start
            logger.info(f"Step 2 completed in {step_times['step2_content_generation']:.2f}s")
            
            # Step 3: Validation & Formatting (30s target)
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
            logger.info(f"Content generation completed in {total_time:.2f}s")
            
            # Get unique books used
            books_used = {}
            for page in selected_pages:
                books_used[page['book_id']] = page['book_title']
            sources_used = [{'book_id': bid, 'title': title} for bid, title in books_used.items()]
            
            return GenerationResult(
                success=True,
                content=formatted_content,
                citations=citations,
                sources_used=sources_used,
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
    
    async def _step1_smart_page_selection(
        self,
        theme: str,
        book_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Step 1: Smart page selection using raw TOC and LLM
        LLM returns "0" if book is irrelevant
        Target: 60 seconds
        """
        if self.use_mock:
            return [
                {
                    'book_id': book_ids[0],
                    'book_title': 'Mock Book',
                    'page_number': i,
                    'content': f"Mock content for {theme}",
                    'relevance_score': 1.0
                }
                for i in range(101, 106)
            ]
        
        selected_pages = []
        
        for book_id in book_ids:
            logger.info(f"Processing book: {book_id}")
            
            # Load book
            # TODO: Get book path from database/config
            book_path = 'питон_мок_дата.pdf'  # Temporary hardcode
            pages_data = self.pdf_processor.extract_text_from_pdf(book_path)
            
            if not pages_data['success']:
                logger.error(f"Failed to extract pages from {book_path}")
                continue
            
            # CRITICAL: Detect page offset between TOC page numbers and PDF page numbers
            page_offset = self.pdf_processor.detect_page_offset(pages_data['pages'])
            logger.info(f"Page offset detected: {page_offset} (TOC page + {page_offset} = PDF page)")
            
            # Find TOC pages
            toc_page_numbers = self.pdf_processor.find_toc_pages(pages_data['pages'])
            
            if not toc_page_numbers:
                logger.warning(f"No TOC found for book {book_id}, skipping")
                continue
            
            # Get raw TOC text
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages'] 
                if p['page_number'] in toc_page_numbers
            ])
            
            # Limit TOC text size
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]
            
            logger.info(f"Using raw TOC text ({len(toc_text)} chars) for page selection")
            
            # Use LLM to get page numbers (returns "0" if irrelevant)
            # These are BOOK page numbers (колонтитул), not PDF page numbers
            book_page_numbers = await self._get_page_numbers_from_toc(theme, toc_text)
            
            if not book_page_numbers or book_page_numbers == [0]:
                logger.info(f"Book {book_id} is not relevant for theme '{theme}' (LLM returned 0)")
                continue
            
            logger.info(f"LLM selected book page numbers: {book_page_numbers}")
            
            # CRITICAL: Apply offset to convert book pages to PDF pages
            pdf_page_numbers = [book_page + page_offset for book_page in book_page_numbers]
            logger.info(f"Converted to PDF page numbers: {pdf_page_numbers}")
            
            # Load content from these pages
            book_title = pages_data['metadata'].get('title', book_id)
            
            for page_num in pdf_page_numbers:
                page_data = next((p for p in pages_data['pages'] if p['page_number'] == page_num), None)
                
                if page_data:
                    selected_pages.append({
                        'book_id': book_id,
                        'book_title': book_title,
                        'page_number': page_num,
                        'content': page_data['text'],
                        'relevance_score': 1.0
                    })
                else:
                    logger.warning(f"PDF page {page_num} not found (book page {page_num - page_offset})")
        
        logger.info(f"Selected {len(selected_pages)} pages total from {len(book_ids)} books")
        if selected_pages:
            logger.info(f"Page numbers: {sorted(set([p['page_number'] for p in selected_pages]))}")
        
        return selected_pages
    
    def _clean_toc_text(self, toc_text: str) -> str:
        """
        Add spaces to stuck-together words in TOC
        Example: "Ещёостроках" → "Ещё о строках"
        """
        import re
        # lowercase + uppercase → add space
        cleaned = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', toc_text)
        # letter + number → add space  
        cleaned = re.sub(r'([а-яёА-ЯЁa-zA-Z])(\d)', r'\1 \2', cleaned)
        return cleaned
    
    def _chunk_toc_by_chapters(self, toc_text: str, chapters_per_chunk: int = 5) -> List[str]:
        """
        Split TOC into chunks by chapter boundaries
        Each chunk contains ~5 chapters for manageable context
        """
        import re
        lines = toc_text.split('\n')
        chunks = []
        current_chunk = []
        chapter_count = 0
        
        for line in lines:
            # Detect main chapter (e.g., "7 Основы")
            if re.match(r'^\d+\s+[А-ЯЁA-Z]', line):
                chapter_count += 1
                if chapter_count > chapters_per_chunk and current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    chapter_count = 1
            
            current_chunk.append(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _parse_page_ranges(self, ranges_text: str) -> List[tuple]:
        """
        Parse "36-38, 89-90" into [(36, 38), (89, 90)]
        """
        import re
        
        if not ranges_text or ranges_text == "0" or "не найд" in ranges_text.lower():
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
    
    def _add_buffer_to_ranges(self, ranges: List[tuple], buffer_pages: int = 1) -> List[int]:
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
    
    def _parse_toc_with_regex(self, toc_text: str) -> List[Dict[str, Any]]:
        """
        Parse TOC using regex to extract sections
        
        Returns:
            List of dicts: [{'number': '7.4', 'title': 'Строки', 'page': 36}, ...]
        """
        import re
        
        sections = []
        lines = toc_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern: "7.4 Строки . . . . 36" or "14 Объектно-ориентированное программирование 101"
            # Match: section_number + title + dots/spaces + page_number
            match = re.match(r'^(\d+(?:\.\d+)?)\s+(.+?)\s+[.\s]+(\d+)$', line)
            
            if match:
                section_num = match.group(1)
                title = match.group(2).strip()
                page = int(match.group(3))
                
                # Clean title: add spaces to stuck-together words
                title = self._add_spaces_to_russian_text(title)
                
                sections.append({
                    'number': section_num,
                    'title': title,
                    'page': page
                })
        
        # Calculate page ranges (end = next section's start - 1)
        for i in range(len(sections)):
            if i < len(sections) - 1:
                sections[i]['end_page'] = sections[i + 1]['page'] - 1
            else:
                # Last section: assume 10 pages
                sections[i]['end_page'] = sections[i]['page'] + 10
            
            # Fix: ensure start <= end (swap if needed)
            if sections[i]['page'] > sections[i]['end_page']:
                sections[i]['page'], sections[i]['end_page'] = sections[i]['end_page'], sections[i]['page']
        
        logger.info(f"Parsed {len(sections)} sections from TOC using regex")
        return sections
    
    async def _add_spaces_to_russian_text_with_llm(self, text: str) -> str:
        """
        Use Llama 3.1 8B to add spaces to stuck-together Russian words
        Fast (~1s for entire TOC) and accurate
        """
        if not self.model_manager:
            return text
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            
            prompt = f"""Добавь пробелы между словами в русском тексте. Не меняй ничего кроме пробелов.

Текст: {text}

Исправленный текст:"""
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": len(text) + 50
                }
            )
            
            result = response.get('response', '').strip()
            return result if result else text
            
        except Exception as e:
            logger.warning(f"Failed to add spaces with LLM: {e}")
            return text
    
    def _add_spaces_to_russian_text(self, text: str) -> str:
        """
        Add spaces to stuck-together Russian words using simple regex patterns
        
        Examples:
            "Литеральныеконстанты" → "Литеральные константы"
            "Ещёостроках" → "Ещё о строках"
        """
        import re
        
        # Pattern 1: lowercase + uppercase → add space
        text = re.sub(r'([а-яё])([А-ЯЁ])', r'\1 \2', text)
        
        # Pattern 2: letter + number → add space
        text = re.sub(r'([а-яёА-ЯЁa-zA-Z])(\d)', r'\1 \2', text)
        
        # Pattern 3: number + letter → add space
        text = re.sub(r'(\d)([а-яёА-ЯЁa-zA-Z])', r'\1 \2', text)
        
        # Pattern 4: Common Russian word boundaries
        replacements = [
            ('остроках', 'о строках'),
            ('ифизических', 'и физических'),
            ('ифизические', 'и физические'),
            ('иклассы', 'и классы'),
            ('вобъекты', 'в объекты'),
            ('Логическиеи', 'Логические и'),
            ('физическиестроки', 'физические строки'),
            ('Строкидокументации', 'Строки документации'),
            ('Необрабатываемыестроки', 'Необрабатываемые строки'),
            ('Литеральныеконстанты', 'Литеральные константы'),
            ('Именаидентификаторов', 'Имена идентификаторов'),
            ('Типыданных', 'Типы данных'),
            ('Локальныепеременные', 'Локальные переменные'),
            ('Параметрыфункций', 'Параметры функций'),
            ('Ключевыеаргументы', 'Ключевые аргументы'),
            ('Переменноечисло', 'Переменное число'),
            ('Толькоключевые', 'Только ключевые'),
            ('Порядоквычисления', 'Порядок вычисления'),
            ('Изменениепорядка', 'Изменение порядка'),
        ]
        
        for stuck, spaced in replacements:
            text = text.replace(stuck, spaced)
        
        return text
    
    async def _get_page_numbers_from_toc(
        self,
        theme: str,
        toc_text: str
    ) -> List[int]:
        """
        Parse TOC with regex, then use Gemma 3 27B to select relevant sections
        No chunking - send full parsed TOC in one call
        
        Args:
            theme: Lecture theme
            toc_text: Raw TOC text
            
        Returns:
            List of page numbers, or [0] if irrelevant
        """
        if not self.model_manager:
            return []
        
        try:
            # Step 1: Parse TOC with regex (~0.1s)
            sections = self._parse_toc_with_regex(toc_text)
            
            if not sections:
                logger.warning("No sections parsed from TOC")
                return [0]
            
            logger.info(f"Parsed {len(sections)} sections from TOC")
            
            # Step 2: Format all sections for LLM (with ranges already calculated)
            formatted_sections = []
            for section in sections:
                # Format: "7.4 Строки (pages 36-38)"
                formatted_sections.append(
                    f"{section['number']} {section['title']} (pages {section['page']}-{section['end_page']})"
                )
            
            full_toc = '\n'.join(formatted_sections)
            
            # Step 3: Send full TOC to Gemma 3 27B (no chunking!)
            llm_model = await self.model_manager.get_llm_model()
            
            prompt = f"""Тема: "{theme}"

Выбери разделы, которые учат этой теме.

Оглавление:
{full_toc}

Ответ (номера разделов):"""
            
            logger.info(f"Sending full TOC ({len(full_toc)} chars) to Gemma")
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 100
                }
            )
            
            response_text = response.get('response', '').strip()
            logger.info(f"Gemma response: {response_text}")
            
            # Parse section numbers from response
            section_numbers = self._parse_section_numbers(response_text)
            
            # Convert section numbers to page ranges
            all_ranges = []
            for sec_num in section_numbers:
                matching_section = next((s for s in sections if s['number'] == sec_num), None)
                if matching_section:
                    all_ranges.append((matching_section['page'], matching_section['end_page']))
            
            # Step 4: Add +1 buffer to ranges
            final_pages = self._add_buffer_to_ranges(all_ranges, buffer_pages=1)
            
            if not final_pages:
                return [0]
            
            logger.info(f"Selected {len(final_pages)} pages: {final_pages}")
            
            # Limit to max 30 pages
            if len(final_pages) > 30:
                logger.warning(f"Too many pages ({len(final_pages)}), limiting to 30")
                final_pages = final_pages[:30]
            
            return final_pages
            
        except Exception as e:
            logger.error(f"Error getting page numbers from TOC: {e}", exc_info=True)
            return []
    
    def _parse_section_numbers(self, response_text: str) -> List[str]:
        """
        Parse section numbers from LLM response
        
        Examples:
            "7.4, 12.8" → ["7.4", "12.8"]
            "7.4, 12.8, 18.11" → ["7.4", "12.8", "18.11"]
        """
        import re
        
        # Find all patterns like "7.4" or "12.8"
        pattern = r'\b\d+(?:\.\d+)?\b'
        matches = re.findall(pattern, response_text)
        
        return matches
    
    def _expand_page_ranges(
        self,
        toc_pages: List[int],
        max_pages_per_section: int = 5,
        max_gap: int = 10
    ) -> List[int]:
        """
        Expand TOC page numbers to include content pages between entries.
        
        Problem: TOC shows "Strings p.12" and "Lists p.15", but pages 13-14
        also contain string content. LLM only returns [12, 15], missing 13-14.
        
        Solution: Intelligently expand ranges based on gaps between TOC entries.
        
        Args:
            toc_pages: List of page numbers from TOC (e.g., [12, 15, 20])
            max_pages_per_section: Max pages to add after each TOC entry
            max_gap: Max gap between entries to fully expand
            
        Returns:
            Expanded list of page numbers
            
        Examples:
            Input: [12, 15] (gap=3, small)
            Output: [12, 13, 14, 15] (include all between)
            
            Input: [12, 50] (gap=38, large)
            Output: [12, 13, 14, 15, 16, 50, 51, 52, 53, 54] (only add max_pages_per_section)
        """
        if not toc_pages:
            return []
        
        # Sort pages first
        toc_pages = sorted(set(toc_pages))
        
        expanded = []
        
        for i, page in enumerate(toc_pages):
            expanded.append(page)
            
            if i < len(toc_pages) - 1:
                next_page = toc_pages[i + 1]
                gap = next_page - page
                
                if gap <= max_gap:
                    # Small gap: likely same topic, include all pages between
                    for p in range(page + 1, next_page):
                        expanded.append(p)
                    logger.debug(f"Expanded {page}-{next_page} (gap={gap}, included all)")
                else:
                    # Large gap: different topics, only add a few pages
                    for p in range(page + 1, min(page + max_pages_per_section, next_page)):
                        expanded.append(p)
                    logger.debug(f"Expanded {page} by {max_pages_per_section} pages (gap={gap}, large)")
            else:
                # Last entry: add a few more pages to complete the section
                for p in range(page + 1, page + max_pages_per_section):
                    expanded.append(p)
                logger.debug(f"Expanded last entry {page} by {max_pages_per_section} pages")
        
        result = sorted(set(expanded))
        logger.info(f"Page expansion: {len(toc_pages)} TOC pages → {len(result)} total pages")
        
        return result
    
    async def _step2_content_generation(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> str:
        """
        Step 2: Two-stage content generation
        Stage 1: Generate detailed outline
        Stage 2: Generate each section separately
        Target: 120-180 seconds
        """
        if self.use_mock or not self.model_manager:
            return f"# Лекция: {theme}\n\n[Mock generated content]"
        
        # Prepare context from selected pages (use top 15 pages for better coverage)
        pages_to_use = selected_pages[:15]
        context = "\n\n---PAGE BREAK---\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in pages_to_use
        ])
        
        logger.info(f"Context length: {len(context)} chars from {len(pages_to_use)} pages")
        
        # Stage 1: Generate outline
        logger.info("Stage 1: Generating outline...")
        outline = await self._generate_outline(theme, context)
        logger.info(f"Outline generated: {len(outline)} sections")
        
        # Stage 2: Generate each section
        logger.info("Stage 2: Generating sections...")
        sections = []
        for i, section_info in enumerate(outline, 1):
            logger.info(f"Generating section {i}/{len(outline)}: {section_info['title']}")
            section_content = await self._generate_section(
                theme, 
                section_info, 
                context,
                i,
                len(outline)
            )
            sections.append(section_content)
        
        # Combine sections
        final_content = "\n\n".join(sections)
        logger.info(f"Final content length: {len(final_content)} chars, ~{len(final_content.split())} words")
        
        return final_content
    
    async def _generate_outline(self, theme: str, context: str) -> List[Dict[str, Any]]:
        """Generate detailed outline for the lecture"""
        
        outline_prompt = f"""Создай ПОДРОБНЫЙ план лекции по теме "{theme}".

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context[:5000]}

Создай план из 5 разделов:
1. Введение (400-500 слов)
2. Основные концепции (1000-1200 слов)
3. Примеры кода (600-800 слов)
4. Практические советы (300-400 слов)
5. Заключение (200-300 слов)

Для каждого раздела укажи:
- Название раздела
- Целевое количество слов
- 3-5 ключевых пунктов, которые нужно раскрыть

Формат ответа:
РАЗДЕЛ 1: [название]
СЛОВ: [количество]
ПУНКТЫ:
- [пункт 1]
- [пункт 2]
- [пункт 3]

План:"""

        try:
            llm_model = await self.model_manager.get_llm_model()
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=outline_prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 1000
                }
            )
            
            outline_text = response.get('response', '')
            
            # Parse outline
            outline = self._parse_outline(outline_text)
            
            # If parsing failed, use default outline
            if not outline:
                outline = [
                    {'title': 'Введение', 'words': 450, 'points': ['Важность темы', 'Применение', 'Что узнаем']},
                    {'title': 'Основные концепции', 'words': 1100, 'points': ['Определения', 'Технические детали', 'Особенности']},
                    {'title': 'Примеры кода', 'words': 700, 'points': ['Базовые примеры', 'Продвинутые примеры', 'Объяснения']},
                    {'title': 'Практические советы', 'words': 350, 'points': ['Типичные ошибки', 'Лучшие практики', 'Советы']},
                    {'title': 'Заключение', 'words': 250, 'points': ['Резюме', 'Ключевые моменты', 'Дальнейшее изучение']}
                ]
            
            return outline
            
        except Exception as e:
            logger.error(f"Error generating outline: {e}")
            # Return default outline
            return [
                {'title': 'Введение', 'words': 450, 'points': ['Важность темы', 'Применение', 'Что узнаем']},
                {'title': 'Основные концепции', 'words': 1100, 'points': ['Определения', 'Технические детали', 'Особенности']},
                {'title': 'Примеры кода', 'words': 700, 'points': ['Базовые примеры', 'Продвинутые примеры', 'Объяснения']},
                {'title': 'Практические советы', 'words': 350, 'points': ['Типичные ошибки', 'Лучшие практики', 'Советы']},
                {'title': 'Заключение', 'words': 250, 'points': ['Резюме', 'Ключевые моменты', 'Дальнейшее изучение']}
            ]
    
    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        """Parse outline from LLM response"""
        import re
        
        outline = []
        sections = re.split(r'РАЗДЕЛ \d+:', outline_text)
        
        for section in sections[1:]:  # Skip first empty split
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            title = lines[0].strip()
            words = 500  # default
            points = []
            
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('СЛОВ:'):
                    try:
                        words = int(re.search(r'\d+', line).group())
                    except:
                        pass
                elif line.startswith('-') or line.startswith('•'):
                    point = line.lstrip('-•').strip()
                    if point:
                        points.append(point)
            
            if title:
                outline.append({
                    'title': title,
                    'words': words,
                    'points': points if points else ['Раскрыть тему']
                })
        
        return outline
    
    async def _generate_section(
        self,
        theme: str,
        section_info: Dict[str, Any],
        context: str,
        section_num: int,
        total_sections: int
    ) -> str:
        """Generate a single section of the lecture"""
        
        section_title = section_info['title']
        target_words = section_info['words']
        key_points = section_info['points']
        
        points_text = '\n'.join([f"- {p}" for p in key_points])
        
        section_prompt = f"""Напиши раздел лекции по теме "{theme}".

РАЗДЕЛ: {section_title} (раздел {section_num} из {total_sections})

ЦЕЛЕВОЙ ОБЪЕМ: {target_words} слов (это ОБЯЗАТЕЛЬНОЕ требование!)

КЛЮЧЕВЫЕ ПУНКТЫ, которые нужно раскрыть:
{points_text}

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ТРЕБОВАНИЯ:
- Напиши МИНИМУМ {target_words} слов
- Используй ТОЛЬКО информацию из предоставленных страниц учебника
- Для примеров кода указывай номер страницы: # Пример со страницы [номер]
- Пиши ПОДРОБНО, с множеством деталей
- Раскрой ВСЕ ключевые пункты

ФОРМАТ:
**{section_title}**

[Подробное содержание раздела минимум {target_words} слов]

Начни писать раздел:"""

        try:
            llm_model = await self.model_manager.get_llm_model()
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=section_prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": int(target_words * 2),  # 2x words for tokens
                    "num_ctx": 32768,
                    "top_p": 0.9
                }
            )
            
            section_content = response.get('response', '')
            logger.info(f"Section '{section_title}' generated: {len(section_content.split())} words")
            
            return section_content
            
        except Exception as e:
            logger.error(f"Error generating section '{section_title}': {e}")
            return f"**{section_title}**\n\n[Ошибка генерации раздела]"
    
    async def _step2_content_generation_old(
        self,
        theme: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> str:
        """
        OLD: Single-stage content generation (kept for reference)
        """
        if self.use_mock or not self.model_manager:
            return f"# Лекция: {theme}\n\n[Mock generated content]"
        
        # Prepare context from selected pages (use top 15 pages for better coverage)
        pages_to_use = selected_pages[:15]
        context = "\n\n---PAGE BREAK---\n\n".join([
            f"[СТРАНИЦА {p['page_number']}]\n{p['content']}"
            for p in pages_to_use
        ])
        
        logger.info(f"Context length: {len(context)} chars from {len(pages_to_use)} pages")
        
        prompt = f"""Ты опытный преподаватель программирования. Напиши ОЧЕНЬ ПОДРОБНУЮ лекцию по теме "{theme}".

КРИТИЧЕСКИ ВАЖНО - ДЛИНА ЛЕКЦИИ:
- Лекция должна быть МИНИМУМ 2000-2500 слов (это ОБЯЗАТЕЛЬНОЕ требование!)
- Если лекция короче 2000 слов - это ОШИБКА
- Пиши ПОДРОБНО, с множеством деталей и объяснений
- НЕ останавливайся, пока не напишешь ВСЁ содержание

КРИТИЧЕСКИ ВАЖНО - ИСТОЧНИКИ:
- Используй ТОЛЬКО информацию из предоставленных страниц учебника
- Все примеры кода должны быть ТОЧНО из учебника (копируй код как есть)
- Для КАЖДОГО примера кода указывай номер страницы в формате: # Пример со страницы [номер]
- НЕ используй примеры из других источников или своей памяти

МАТЕРИАЛ ИЗ УЧЕБНИКА:
{context}

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА ЛЕКЦИИ (каждый раздел должен быть ПОДРОБНЫМ):

1. ВВЕДЕНИЕ (400-500 слов - НЕ МЕНЬШЕ!)
   - Объясни важность темы (2-3 абзаца)
   - Где применяется в реальных задачах (2-3 абзаца)
   - Что студент узнает из лекции (2 абзаца)
   - Исторический контекст или интересные факты (1-2 абзаца)

2. ОСНОВНЫЕ КОНЦЕПЦИИ (1000-1200 слов - НЕ МЕНЬШЕ!)
   - Подробные определения из учебника (3-4 абзаца на каждую концепцию)
   - Технические детали и особенности (множество деталей!)
   - Объяснение каждой концепции с примерами
   - Для темы о строках: типы строк, методы, форматирование, срезы
   - Каждая подтема должна быть раскрыта ПОЛНОСТЬЮ (минимум 200-300 слов на подтему)

3. ПРИМЕРЫ КОДА (600-800 слов - НЕ МЕНЬШЕ!)
   - Минимум 10-15 примеров кода
   - Каждый пример в отдельном блоке кода
   - Обязательно указывай страницу: # Пример со страницы [номер]
   - После каждого примера - ПОДРОБНОЕ объяснение (минимум 3-5 предложений)
   - Объясни ЧТО делает код, КАК он работает, ПОЧЕМУ это важно
   - Примеры должны покрывать ВСЕ аспекты темы

4. ПРАКТИЧЕСКИЕ СОВЕТЫ (300-400 слов - НЕ МЕНЬШЕ!)
   - Типичные ошибки и как их избежать (5-7 пунктов с подробными объяснениями)
   - Лучшие практики из учебника (5-7 пунктов)
   - Советы по применению в реальных задачах (3-5 пунктов)
   - Каждый совет должен быть ПОДРОБНО объяснен (2-3 предложения на каждый)

5. ЗАКЛЮЧЕНИЕ (200-300 слов - НЕ МЕНЬШЕ!)
   - Краткое резюме ВСЕХ ключевых моментов (3-4 абзаца)
   - Что студент должен запомнить (2 абзаца)
   - Связь с будущими темами (1-2 абзаца)
   - Мотивация к дальнейшему изучению (1 абзац)

ФОРМАТ ПРИМЕРОВ КОДА:
```python
# Пример со страницы [номер]
[точный код из учебника]
```

ПОМНИ: Лекция должна быть МИНИМУМ 2000 слов! Пиши ПОДРОБНО, НЕ сокращай!

НАЧНИ ПИСАТЬ ПОДРОБНУЮ ЛЕКЦИЮ СЕЙЧАС (минимум 2000 слов):"""
        
        try:
            llm_model = await self.model_manager.get_llm_model()
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 15000,  # Increased for 2000-2500 words
                    "num_ctx": 32768,
                    "top_p": 0.9
                }
            )
            
            return response.get('response', '')
            
        except Exception as e:
            logger.error(f"Error in LLM generation: {e}")
            return f"[Ошибка генерации: {e}]"
    
    async def _validate_against_pages(
        self,
        generated_content: str,
        selected_pages: List[Dict[str, Any]]
    ) -> float:
        """
        Validate generated content against the actual pages used
        This is the anti-hallucination check
        
        Args:
            generated_content: The lecture content
            selected_pages: The pages we gave to LLM
            
        Returns:
            Confidence score 0-1
        """
        try:
            # Extract claims from generated content
            claims = await self._extract_claims(generated_content)
            
            if not claims:
                logger.warning("No claims extracted, returning default confidence")
                return 0.75
            
            logger.info(f"Extracted {len(claims)} claims for validation")
            
            # Get embedding model
            embedding_model = await self.model_manager.get_embedding_model()
            
            # Generate embeddings for selected pages
            page_texts = [p['content'] for p in selected_pages]
            page_embeddings = embedding_model.encode(page_texts)
            
            # Validate each claim
            supported = 0
            for claim in claims:
                claim_embedding = embedding_model.encode([claim])[0]
                
                # Calculate cosine similarity with each page
                max_similarity = 0
                for page_emb in page_embeddings:
                    similarity = np.dot(claim_embedding, page_emb) / (
                        np.linalg.norm(claim_embedding) * np.linalg.norm(page_emb)
                    )
                    max_similarity = max(max_similarity, similarity)
                
                # Claim is supported if similarity > 0.4
                if max_similarity > 0.4:
                    supported += 1
                    logger.debug(f"Claim supported (sim={max_similarity:.2f}): {claim[:50]}...")
                else:
                    logger.debug(f"Claim NOT supported (sim={max_similarity:.2f}): {claim[:50]}...")
            
            confidence = supported / len(claims)
            logger.info(f"Validation: {supported}/{len(claims)} claims supported = {confidence:.2%}")
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error in validation: {e}", exc_info=True)
            return 0.70  # Default confidence on error
    
    async def _extract_claims(self, content: str) -> List[str]:
        """Extract factual claims from generated content using LLM"""
        try:
            llm_model = await self.model_manager.get_llm_model()
            
            extraction_prompt = f"""Извлеките все фактические утверждения из следующего текста лекции.
Фактическое утверждение - это конкретное техническое утверждение, определение или факт.

НЕ извлекайте:
- Общие вводные фразы
- Организационную информацию
- Вопросы
- Заголовки

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
                    "temperature": 0.1,
                    "num_predict": 1000
                }
            )
            
            claims_text = response.get('response', '')
            claims = []
            
            for line in claims_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    claim = line.lstrip('0123456789.-•) ').strip()
                    if len(claim) > 20:
                        claims.append(claim)
            
            return claims[:10]
            
        except Exception as e:
            logger.error(f"Error extracting claims: {e}")
            return []
    
    async def _fgos_formatting(
        self,
        content: str,
        rpd_data: Dict[str, Any],
        selected_pages: List[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Format content according to FGOS standards
        """
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


# Global generator instance
content_generator = None


async def get_content_generator(
    model_manager=None,
    pdf_processor=None,
    use_mock: bool = False
) -> ContentGenerator:
    """Get global content generator instance"""
    global content_generator
    
    if content_generator is None:
        content_generator = ContentGenerator(use_mock=use_mock)
        await content_generator.initialize(model_manager, pdf_processor)
    
    return content_generator
