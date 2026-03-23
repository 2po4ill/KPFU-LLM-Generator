"""
Literature processing: PDF extraction, chunking, and embedding generation
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    import PyPDF2

logger = logging.getLogger(__name__)


@dataclass
class BookChunk:
    """Represents a chunk of book content"""
    chunk_id: str
    book_id: str
    page_number: int
    content: str
    char_count: int
    embedding: Optional[List[float]] = None


@dataclass
class TableOfContents:
    """Table of contents entry"""
    title: str
    page_number: int
    level: int  # 1 for chapter, 2 for section, etc.


class PDFProcessor:
    """Process PDF books: extract text, parse TOC, create chunks"""
    
    def __init__(self):
        self.chunk_size = 1000  # characters
        self.chunk_overlap = 200  # characters overlap between chunks
        self.book_tocs = {}  # Store TOC by book_id
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            if HAS_PDFPLUMBER:
                return self._extract_with_pdfplumber(pdf_path)
            elif HAS_PYMUPDF:
                return self._extract_with_pymupdf(pdf_path)
            else:
                return self._extract_with_pypdf2(pdf_path)
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text using pdfplumber (best quality for TOC)"""
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_text = []
            
            logger.info(f"Extracting text from {total_pages} pages using pdfplumber...")
            
            for page_num in range(total_pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    pages_text.append({
                        'page_number': page_num + 1,
                        'text': text,
                        'char_count': len(text)
                    })
            
            # Extract metadata
            metadata = pdf.metadata or {}
            
            full_text = '\n\n'.join([p['text'] for p in pages_text])
            
            return {
                'success': True,
                'total_pages': total_pages,
                'pages': pages_text,
                'full_text': full_text,
                'total_chars': len(full_text),
                'metadata': metadata
            }
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text using PyMuPDF (better quality)"""
        doc = fitz.open(pdf_path)
        
        total_pages = len(doc)
        pages_text = []
        
        logger.info(f"Extracting text from {total_pages} pages using PyMuPDF...")
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append({
                'page_number': page_num + 1,
                'text': text,
                'char_count': len(text)
            })
        
        # Extract metadata
        metadata = doc.metadata
        
        full_text = '\n\n'.join([p['text'] for p in pages_text])
        
        doc.close()
        
        return {
            'success': True,
            'total_pages': total_pages,
            'pages': pages_text,
            'full_text': full_text,
            'total_chars': len(full_text),
            'metadata': metadata
        }
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text using PyPDF2 (fallback)"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            total_pages = len(pdf_reader.pages)
            pages_text = []
            
            logger.info(f"Extracting text from {total_pages} pages using PyPDF2...")
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                pages_text.append({
                    'page_number': page_num + 1,
                    'text': text,
                    'char_count': len(text)
                })
            
            # Extract metadata
            metadata = {}
            if pdf_reader.metadata:
                metadata = {
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'creator': pdf_reader.metadata.get('/Creator', '')
                }
            
            full_text = '\n\n'.join([p['text'] for p in pages_text])
            
            return {
                'success': True,
                'total_pages': total_pages,
                'pages': pages_text,
                'full_text': full_text,
                'total_chars': len(full_text),
                'metadata': metadata
            }
    
    def find_toc_pages(self, pages_text: List[Dict[str, Any]]) -> List[int]:
        """
        Find pages that contain table of contents
        
        Args:
            pages_text: List of page dictionaries
            
        Returns:
            List of page numbers that likely contain TOC
        """
        toc_keywords = [
            'оглавление', 'содержание', 'contents', 'table of contents',
            'оглавленіе', 'содержаніе'  # Old Russian spelling
        ]
        
        toc_pages = []
        
        # Check first 15 pages for TOC keywords
        for page_data in pages_text[:15]:
            text_lower = page_data['text'].lower()
            
            # Check if page contains TOC keywords
            if any(keyword in text_lower for keyword in toc_keywords):
                toc_pages.append(page_data['page_number'])
                logger.info(f"Found TOC keyword on page {page_data['page_number']}")
        
        # If we found TOC start, include next 4-5 pages only (TOC is usually 3-5 pages)
        if toc_pages:
            start_page = toc_pages[0]
            # Include only 4 pages after TOC start
            for page_num in range(start_page + 1, min(start_page + 5, 16)):
                if page_num not in toc_pages:
                    toc_pages.append(page_num)
        
        logger.info(f"Identified TOC pages: {toc_pages}")
        return sorted(toc_pages)
    
    async def extract_toc_with_llm(
        self,
        pages_text: List[Dict[str, Any]],
        model_manager=None
    ) -> List[TableOfContents]:
        """
        Extract table of contents using LLM
        
        Args:
            pages_text: List of page dictionaries
            model_manager: ModelManager instance for LLM access
            
        Returns:
            List of TOC entries
        """
        if not model_manager:
            logger.warning("No model_manager provided, falling back to regex parsing")
            return self.parse_table_of_contents('\n\n'.join([p['text'] for p in pages_text[:10]]))
        
        # Find TOC pages
        toc_page_numbers = self.find_toc_pages(pages_text)
        
        if not toc_page_numbers:
            logger.warning("No TOC pages found, trying first 10 pages")
            toc_page_numbers = list(range(1, 11))
        
        # Extract text from TOC pages
        toc_text = '\n\n'.join([
            p['text'] for p in pages_text 
            if p['page_number'] in toc_page_numbers
        ])
        
        # Limit text size (max 10000 chars to avoid context issues)
        if len(toc_text) > 10000:
            toc_text = toc_text[:10000]
        
        logger.info(f"Extracting TOC from {len(toc_page_numbers)} pages ({len(toc_text)} chars)")
        
        # LLM prompt for TOC extraction - Few-shot with actual examples
        prompt = f"""Extract table of contents entries. For each entry, write one line: Title → Page

EXAMPLE from a Python book:
Input:
"7 Основы
35
7.1
Комментарии . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
35
7.3
Числа . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
36
14 Объектно-ориентированное программирование
101
14.1
self . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
102"

Output:
Основы → 35
Комментарии → 35
Числа → 36
Объектно-ориентированное программирование → 101
self → 102

Now extract from this table of contents:

{toc_text}

Output (one line per entry, format: Title → Page):"""
        
        try:
            llm_model = await model_manager.get_llm_model()
            
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={
                    "temperature": 0.1,  # Low temperature for precise extraction
                    "num_predict": 6000,  # Increased for large TOC
                    "top_p": 0.9,
                    "repeat_penalty": 1.0
                }
            )
            
            response_text = response.get('response', '').strip()
            logger.info(f"LLM TOC extraction response length: {len(response_text)} chars")
            
            # Save response for debugging
            with open('toc_extraction_response.txt', 'w', encoding='utf-8') as f:
                f.write(response_text)
            logger.info("TOC extraction response saved to toc_extraction_response.txt")
            
            # Parse simple format: "Title → Page"
            toc_entries = []
            
            for line in response_text.split('\n'):
                line = line.strip()
                
                # Skip empty lines and explanatory text
                if not line or '→' not in line:
                    continue
                
                # Parse "Title → Page"
                parts = line.split('→')
                if len(parts) == 2:
                    title = parts[0].strip()
                    page_str = parts[1].strip()
                    
                    # Extract page number (might have extra text)
                    import re
                    page_match = re.search(r'\d+', page_str)
                    if page_match:
                        page_num = int(page_match.group())
                        
                        # Determine level based on title (simple heuristic)
                        # If title is short and looks like a subsection, it's level 2
                        # Otherwise level 1
                        if len(title) < 30 and not any(word in title.lower() for word in ['программирование', 'введение', 'основы']):
                            level = 2
                        else:
                            level = 1
                        
                        toc_entries.append(TableOfContents(
                            title=title,
                            page_number=page_num,
                            level=level
                        ))
            
            if toc_entries:
                logger.info(f"Successfully extracted {len(toc_entries)} TOC entries with LLM")
                return toc_entries
            else:
                logger.error("No TOC entries parsed from LLM response")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting TOC with LLM: {e}", exc_info=True)
            logger.warning("Falling back to regex parsing")
            return self.parse_table_of_contents(toc_text)
    
    def parse_table_of_contents(self, text: str) -> List[TableOfContents]:
        """
        Parse table of contents from text
        Handles multiple TOC formats:
        
        Format 1 (PyMuPDF multi-line - 4 lines):
        Line 1: Section number (e.g., "14.1")
        Line 2: Title (e.g., "self")
        Line 3: Dots
        Line 4: Page number (e.g., "102")
        
        Format 2 (Single line with dots):
        Line: "14 Объектно-ориентированное программирование . . . 101"
        
        Format 3 (Simple format):
        Line: "14 Объектно-ориентированное программирование 101"
        
        Format 4 (Russian academic format):
        Line: "Глава 1. Введение в Python ........................ 15"
        
        Args:
            text: Full text or TOC section
            
        Returns:
            List of TOC entries
        """
        toc_entries = []
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines) - 1:
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Format 2 & 3: Single line formats
            # Pattern: number + title + optional dots + page number
            patterns = [
                # "14.1 Title . . . . 102" or "14.1 Title 102"
                r'^(\d+(?:\.\d+)?)\s+(.+?)\s+[.\s]*(\d+)\s*$',
                
                # "Глава 1. Title .... 15" 
                r'^(?:Глава|Chapter|Раздел)\s+(\d+)\.?\s+(.+?)\s+[.\s]*(\d+)\s*$',
                
                # "1. Title .... 15"
                r'^(\d+)\.?\s+(.+?)\s+[.\s]*(\d+)\s*$',
                
                # More flexible: any number + text + number at end
                r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\d+)$'
            ]
            
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    section_num = match.group(1)
                    title = match.group(2).strip()
                    
                    # Clean title: remove excessive dots and spaces
                    title = re.sub(r'[.\s]+$', '', title)  # Remove trailing dots/spaces
                    title = re.sub(r'\s+', ' ', title)     # Normalize spaces
                    
                    try:
                        page_num = int(match.group(3))
                        
                        # Determine level based on section number
                        if '.' in section_num:
                            level = section_num.count('.') + 1
                        else:
                            level = 1
                        
                        # Only add if title is meaningful (not too short, not just dots)
                        if len(title) > 2 and not re.match(r'^[.\s]*$', title):
                            toc_entries.append(TableOfContents(
                                title=title,
                                page_number=page_num,
                                level=level
                            ))
                            logger.debug(f"TOC entry (single line): [{level}] {title} → page {page_num}")
                        
                        matched = True
                        break
                        
                    except ValueError:
                        continue
            
            if matched:
                i += 1
                continue
            
            # Format 1: Multi-line format (original PyMuPDF format)
            # Pattern: Section number alone (e.g., "14.1")
            if re.match(r'^\d+\.\d+$', line):
                section_num = line
                
                # Check if we have at least 3 more lines
                if i + 3 < len(lines):
                    title_line = lines[i + 1].strip()
                    dots_line = lines[i + 2].strip()
                    page_line = lines[i + 3].strip()
                    
                    # Verify dots line (should be mostly dots)
                    if dots_line.count('.') > 5:
                        # Verify page line is a number
                        if page_line.isdigit():
                            page_num = int(page_line)
                            level = section_num.count('.') + 1
                            
                            # Only add if title is not empty and not too short
                            if title_line and len(title_line) > 2:
                                toc_entries.append(TableOfContents(
                                    title=title_line,
                                    page_number=page_num,
                                    level=level
                                ))
                                logger.debug(f"TOC entry (multi-line): [{level}] {title_line} → page {page_num}")
                            
                            i += 4
                            continue
            
            i += 1
        
        logger.info(f"Parsed {len(toc_entries)} TOC entries")
        return toc_entries
    
    def create_chunks(self, pages_text: List[Dict[str, Any]], book_id: str) -> List[BookChunk]:
        """
        Create overlapping chunks from page text
        
        Args:
            pages_text: List of page dictionaries with text
            book_id: Unique book identifier
            
        Returns:
            List of BookChunk objects
        """
        chunks = []
        chunk_counter = 0
        
        for page_data in pages_text:
            page_num = page_data['page_number']
            text = page_data['text']
            
            # Skip empty pages
            if not text.strip():
                continue
            
            # Create chunks from this page
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]
                
                # Try to break at sentence boundary
                if end < len(text):
                    # Look for sentence end in last 100 chars
                    last_period = chunk_text.rfind('.')
                    last_question = chunk_text.rfind('?')
                    last_exclamation = chunk_text.rfind('!')
                    
                    sentence_end = max(last_period, last_question, last_exclamation)
                    
                    if sentence_end > self.chunk_size - 100:
                        chunk_text = chunk_text[:sentence_end + 1]
                        end = start + sentence_end + 1
                
                chunk_id = f"{book_id}_chunk_{chunk_counter}"
                
                chunks.append(BookChunk(
                    chunk_id=chunk_id,
                    book_id=book_id,
                    page_number=page_num,
                    content=chunk_text.strip(),
                    char_count=len(chunk_text.strip())
                ))
                
                chunk_counter += 1
                
                # Move start position with overlap
                start = end - self.chunk_overlap
                
                # Prevent infinite loop
                if start >= len(text):
                    break
        
        logger.info(f"Created {len(chunks)} chunks from {len(pages_text)} pages")
        return chunks
    
    def extract_keywords_from_text(self, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """
        Extract keywords from text using simple frequency analysis
        
        Args:
            text: Text to analyze
            top_n: Number of top keywords to return
            
        Returns:
            List of (keyword, frequency) tuples
        """
        # Remove common Russian stop words
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'для', 'как', 'что', 'это', 'не',
            'из', 'к', 'о', 'от', 'до', 'при', 'за', 'у', 'или', 'а',
            'но', 'же', 'бы', 'так', 'только', 'еще', 'уже', 'если',
            'то', 'все', 'этот', 'быть', 'мочь', 'весь', 'свой', 'один'
        }
        
        # Tokenize and clean
        words = re.findall(r'\b[а-яёa-z]{3,}\b', text.lower())
        
        # Count frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_words[:top_n]
    
    async def process_book(
        self,
        pdf_path: Path,
        book_id: str,
        model_manager=None
    ) -> Dict[str, Any]:
        """
        Complete book processing pipeline
        
        Args:
            pdf_path: Path to PDF file
            book_id: Unique book identifier
            model_manager: Optional ModelManager (not used anymore, kept for compatibility)
            
        Returns:
            Processing results with chunks and metadata
        """
        logger.info(f"Processing book: {pdf_path}")
        
        # Step 1: Extract text
        extraction_result = self.extract_text_from_pdf(pdf_path)
        
        if not extraction_result['success']:
            return extraction_result
        
        # Step 2: Find TOC pages (but don't parse them - we'll use raw text later)
        toc_page_numbers = self.find_toc_pages(extraction_result['pages'])
        
        # Step 3: Create chunks for embedding
        chunks = self.create_chunks(extraction_result['pages'], book_id)
        
        # Step 4: Extract keywords
        keywords = self.extract_keywords_from_text(extraction_result['full_text'])
        
        return {
            'success': True,
            'book_id': book_id,
            'total_pages': extraction_result['total_pages'],
            'total_chars': extraction_result['total_chars'],
            'chunks_count': len(chunks),
            'chunks': chunks,
            'toc_page_numbers': toc_page_numbers,  # Store TOC page numbers for later use
            'keywords': keywords,
            'metadata': extraction_result['metadata']
        }
    
    def detect_page_offset(self, pages_data: List[Dict[str, Any]]) -> int:
        """
        Detect offset between book page numbers (колонтитул) and PDF page numbers.
        
        Strategy: Find the first page where page number = 1 (book page 1).
        Supports both footer (нижний колонтитул) and header (верхний колонтитул).
        Offset = PDF page number - 1
        
        Args:
            pages_data: List of page dictionaries with 'page_number' and 'text'
            
        Returns:
            Offset value (e.g., 8 means PDF page 44 = book page 36)
        """
        logger.info("Detecting page offset between PDF pages and book pages...")
        
        # Method 1: Look for page "1" in footer (нижний колонтитул)
        logger.info("Method 1: Checking footer page numbers...")
        for page in pages_data[:50]:
            pdf_page_num = page['page_number']
            text = page['text']
            
            # Extract footer number from last few lines
            lines = text.strip().split('\n')
            last_lines = lines[-5:] if len(lines) >= 5 else lines
            
            # Look for standalone number in footer (usually last line)
            for line in reversed(last_lines):
                line = line.strip()
                
                # Pattern 1: Just "1" on a line
                if line == "1":
                    offset = pdf_page_num - 1
                    logger.info(f"Found footer '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
                
                # Pattern 2: "1 Chapter X" or "1 Глава X"
                match = re.match(r'^1\s+(?:Глава|Chapter|Раздел)', line, re.IGNORECASE)
                if match:
                    offset = pdf_page_num - 1
                    logger.info(f"Found footer '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
                
                # Pattern 3: Number at end of line (e.g., "Chapter 1")
                match = re.search(r'(?:Глава|Chapter|Раздел)\s+1$', line, re.IGNORECASE)
                if match:
                    offset = pdf_page_num - 1
                    logger.info(f"Found footer '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
        
        # Method 2: Look for page "1" in header (верхний колонтитул)
        logger.info("Method 2: Checking header page numbers...")
        for page in pages_data[:50]:
            pdf_page_num = page['page_number']
            text = page['text']
            
            # Extract header number from first few lines
            lines = text.strip().split('\n')
            first_lines = lines[:5] if len(lines) >= 5 else lines
            
            for line in first_lines:
                line = line.strip()
                
                # Pattern 1: Just "1" on a line (header)
                if line == "1":
                    offset = pdf_page_num - 1
                    logger.info(f"Found header '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
                
                # Pattern 2: "Глава 1" or "Chapter 1" at start
                match = re.match(r'^(?:Глава|Chapter|Раздел)\s+1$', line, re.IGNORECASE)
                if match:
                    offset = pdf_page_num - 1
                    logger.info(f"Found header '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
                
                # Pattern 3: Number at start of line
                match = re.match(r'^1\s+', line)
                if match and len(line) > 5:  # Avoid false positives
                    offset = pdf_page_num - 1
                    logger.info(f"Found header '1' on PDF page {pdf_page_num} → offset = {offset}")
                    return offset
        
        # Method 3: Look for any page number and calculate offset
        logger.info("Method 3: Trying alternative method with any page number...")
        
        # Check both footer and header for any clear page numbers
        for page in pages_data[10:40]:  # Skip first 10 pages (usually TOC/intro)
            pdf_page_num = page['page_number']
            text = page['text']
            lines = text.strip().split('\n')
            
            # Check footer (last line)
            if lines:
                last_line = lines[-1].strip()
                match = re.search(r'(\d{1,3})$', last_line)
                if match:
                    footer_num = int(match.group(1))
                    # Reasonable page number (not too high, not 0)
                    if 1 <= footer_num <= 500:
                        offset = pdf_page_num - footer_num
                        logger.info(f"Found footer '{footer_num}' on PDF page {pdf_page_num} → offset = {offset}")
                        return offset
            
            # Check header (first few lines)
            for line in lines[:3]:
                line = line.strip()
                # Look for isolated numbers at start or end
                match = re.search(r'^(\d{1,3})\s|(\d{1,3})$', line)
                if match:
                    header_num = int(match.group(1) or match.group(2))
                    # Reasonable page number
                    if 1 <= header_num <= 500:
                        offset = pdf_page_num - header_num
                        logger.info(f"Found header '{header_num}' on PDF page {pdf_page_num} → offset = {offset}")
                        return offset
        
        logger.warning("Could not detect page offset, defaulting to 0")
        return 0
    def extract_specific_pages(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """
        Extract only specific pages from PDF (optimized for performance)

        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers to extract (1-indexed)

        Returns:
            Dictionary with extracted pages and metadata
        """
        try:
            if HAS_PDFPLUMBER:
                return self._extract_specific_pages_pdfplumber(pdf_path, page_numbers)
            elif HAS_PYMUPDF:
                return self._extract_specific_pages_pymupdf(pdf_path, page_numbers)
            else:
                return self._extract_specific_pages_pypdf2(pdf_path, page_numbers)

        except Exception as e:
            logger.error(f"Error extracting specific pages from PDF: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_specific_pages_pdfplumber(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """Extract specific pages using pdfplumber"""
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_text = []

            # Filter valid page numbers
            valid_pages = [p for p in page_numbers if 1 <= p <= total_pages]

            logger.info(f"Extracting {len(valid_pages)} specific pages using pdfplumber...")

            for page_num in valid_pages:
                try:
                    page = pdf.pages[page_num - 1]  # Convert to 0-indexed
                    text = page.extract_text()
                    if text:
                        pages_text.append({
                            'page_number': page_num,
                            'text': text,
                            'char_count': len(text)
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            # Extract metadata
            metadata = pdf.metadata or {}

            full_text = '\n\n'.join([p['text'] for p in pages_text])

            return {
                'success': True,
                'total_pages': len(pages_text),
                'pages': pages_text,
                'full_text': full_text,
                'total_chars': len(full_text),
                'metadata': metadata,
                'extracted_page_numbers': [p['page_number'] for p in pages_text]
            }

    def _extract_specific_pages_pymupdf(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """Extract specific pages using PyMuPDF"""
        import fitz

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        pages_text = []

        # Filter valid page numbers
        valid_pages = [p for p in page_numbers if 1 <= p <= total_pages]

        logger.info(f"Extracting {len(valid_pages)} specific pages using PyMuPDF...")

        for page_num in valid_pages:
            try:
                page = doc[page_num - 1]  # Convert to 0-indexed
                text = page.get_text()
                if text:
                    pages_text.append({
                        'page_number': page_num,
                        'text': text,
                        'char_count': len(text)
                    })
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num}: {e}")
                continue

        doc.close()

        full_text = '\n\n'.join([p['text'] for p in pages_text])

        return {
            'success': True,
            'total_pages': len(pages_text),
            'pages': pages_text,
            'full_text': full_text,
            'total_chars': len(full_text),
            'metadata': {},
            'extracted_page_numbers': [p['page_number'] for p in pages_text]
        }

    def _extract_specific_pages_pypdf2(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """Extract specific pages using PyPDF2"""
        import PyPDF2

        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            pages_text = []

            # Filter valid page numbers
            valid_pages = [p for p in page_numbers if 1 <= p <= total_pages]

            logger.info(f"Extracting {len(valid_pages)} specific pages using PyPDF2...")

            for page_num in valid_pages:
                try:
                    page = reader.pages[page_num - 1]  # Convert to 0-indexed
                    text = page.extract_text()
                    if text:
                        pages_text.append({
                            'page_number': page_num,
                            'text': text,
                            'char_count': len(text)
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            full_text = '\n\n'.join([p['text'] for p in pages_text])

            return {
                'success': True,
                'total_pages': len(pages_text),
                'pages': pages_text,
                'full_text': full_text,
                'total_chars': len(full_text),
                'metadata': {},
                'extracted_page_numbers': [p['page_number'] for p in pages_text]
            }

    def initialize_book_toc_cache(self, pdf_path: Path, book_id: str) -> Dict[str, Any]:
        """
        Initialize TOC cache for a book (extract first 30 pages, detect TOC, cache data)
        This is done once per book during initialization

        Args:
            pdf_path: Path to PDF file
            book_id: Unique book identifier

        Returns:
            Dictionary with cached TOC data
        """
        try:
            logger.info(f"Initializing TOC cache for book {book_id}...")

            # Step 1: Extract first 30 pages only
            first_30_pages = list(range(1, 31))
            pages_data = self.extract_specific_pages(pdf_path, first_30_pages)

            if not pages_data['success']:
                logger.error(f"Failed to extract first 30 pages from {pdf_path}")
                return {'success': False, 'error': 'Failed to extract pages'}

            logger.info(f"Extracted {len(pages_data['pages'])} pages for TOC detection")

            # Step 2: Detect page offset
            page_offset = self.detect_page_offset(pages_data['pages'])
            logger.info(f"Detected page offset: {page_offset}")

            # Step 3: Find TOC pages
            toc_page_numbers = self.find_toc_pages(pages_data['pages'])

            if not toc_page_numbers:
                logger.warning(f"No TOC found in first 30 pages of {book_id}")
                return {'success': False, 'error': 'No TOC found'}

            logger.info(f"Found TOC pages: {toc_page_numbers}")

            # Step 4: Extract TOC text
            toc_text = '\n\n'.join([
                p['text'] for p in pages_data['pages']
                if p['page_number'] in toc_page_numbers
            ])

            # Limit TOC text size
            if len(toc_text) > 10000:
                toc_text = toc_text[:10000]

            # Step 5: Parse TOC sections (if we have the method available)
            parsed_sections = []
            try:
                # This would use the regex parsing from generator_v2
                # For now, we'll store the raw text and parse it when needed
                pass
            except Exception as e:
                logger.warning(f"Failed to parse TOC sections: {e}")

            # Step 6: Create cache data
            toc_cache_data = {
                'success': True,
                'book_id': book_id,
                'pdf_path': str(pdf_path),
                'toc_pages': toc_page_numbers,
                'toc_text': toc_text,
                'page_offset': page_offset,
                'parsed_sections': parsed_sections,
                'first_30_pages': pages_data['pages'],
                'cache_created': time.time()
            }

            logger.info(f"TOC cache initialized for {book_id}: {len(toc_text)} chars, offset {page_offset}")

            return toc_cache_data

        except Exception as e:
            logger.error(f"Error initializing TOC cache for {book_id}: {e}")
            return {'success': False, 'error': str(e)}

    
    def get_book_toc(self, book_id: str) -> List[TableOfContents]:
        """
        Get stored TOC for a book
        
        Args:
            book_id: Book identifier
            
        Returns:
            List of TOC entries
        """
        return self.book_tocs.get(book_id, [])

    def extract_specific_pages(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """
        Extract only specific pages from PDF (optimized for performance)

        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers to extract (1-indexed)

        Returns:
            Dictionary with extracted pages and metadata
        """
        try:
            if HAS_PDFPLUMBER:
                return self._extract_specific_pages_pdfplumber(pdf_path, page_numbers)
            elif HAS_PYMUPDF:
                return self._extract_specific_pages_pymupdf(pdf_path, page_numbers)
            else:
                return self._extract_specific_pages_pypdf2(pdf_path, page_numbers)

        except Exception as e:
            logger.error(f"Error extracting specific pages from PDF: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_specific_pages_pdfplumber(self, pdf_path: Path, page_numbers: List[int]) -> Dict[str, Any]:
        """Extract specific pages using pdfplumber"""
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_text = []

            # Filter valid page numbers
            valid_pages = [p for p in page_numbers if 1 <= p <= total_pages]

            logger.info(f"Extracting {len(valid_pages)} specific pages using pdfplumber...")

            for page_num in valid_pages:
                try:
                    page = pdf.pages[page_num - 1]  # Convert to 0-indexed
                    text = page.extract_text()
                    if text:
                        pages_text.append({
                            'page_number': page_num,
                            'text': text,
                            'char_count': len(text)
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            # Extract metadata
            metadata = pdf.metadata or {}

            full_text = '\n\n'.join([p['text'] for p in pages_text])

            return {
                'success': True,
                'total_pages': len(pages_text),
                'pages': pages_text,
                'full_text': full_text,
                'total_chars': len(full_text),
                'metadata': metadata,
                'extracted_page_numbers': [p['page_number'] for p in pages_text]
            }


# Global processor instance
pdf_processor = PDFProcessor()


def get_pdf_processor() -> PDFProcessor:
    """Get global PDF processor instance"""
    return pdf_processor
