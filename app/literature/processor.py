"""
Literature processing: PDF extraction, chunking, and embedding generation
"""

import logging
import re
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
        Handles PyMuPDF multi-line format with TWO patterns:
        
        Pattern 1 (subsections - 4 lines):
        Line 1: Section number (e.g., "14.1")
        Line 2: Title (e.g., "self")
        Line 3: Dots
        Line 4: Page number (e.g., "102")
        
        Pattern 2 (main sections - 2 lines):
        Line 1: Section number + Title (e.g., "14 Объектно-ориентированное программирование")
        Line 2: Page number (e.g., "101")
        
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
            
            # Pattern 2: Section number + Title on same line (e.g., "14 Объектно-ориентированное программирование")
            # Match: number(s) followed by space and text
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                section_num = match.group(1)
                title = match.group(2).strip()
                next_line = lines[i + 1].strip()
                
                # Check if next line is a page number
                if next_line.isdigit():
                    page_num = int(next_line)
                    level = 1  # Main sections are level 1
                    
                    toc_entries.append(TableOfContents(
                        title=title,
                        page_number=page_num,
                        level=level
                    ))
                    logger.debug(f"TOC entry (pattern 2): [{level}] {title} → page {page_num}")
                    i += 2
                    continue
            
            # Pattern 1: Section number alone (e.g., "14.1")
            if line and re.match(r'^\d+\.\d+', line):
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
                                logger.debug(f"TOC entry (pattern 1): [{level}] {title_line} → page {page_num}")
                            
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
        Detect offset between book page numbers (колонтитул/footer) and PDF page numbers.
        
        Strategy: Find the first page where footer number = 1 (book page 1).
        Offset = PDF page number - 1
        
        Args:
            pages_data: List of page dictionaries with 'page_number' and 'text'
            
        Returns:
            Offset value (e.g., 8 means PDF page 44 = book page 36)
        """
        logger.info("Detecting page offset between PDF pages and book pages...")
        
        # Scan first 50 pages to find footer page "1"
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
        
        # If not found, try alternative: look for any footer number and match with TOC
        logger.warning("Could not find footer page '1', trying alternative method...")
        
        # Look for pages with clear footer numbers (2-digit numbers at end)
        for page in pages_data[10:40]:  # Skip first 10 pages (usually TOC/intro)
            pdf_page_num = page['page_number']
            text = page['text']
            
            lines = text.strip().split('\n')
            last_line = lines[-1].strip() if lines else ""
            
            # Look for 2-digit number at end
            match = re.search(r'(\d{2})$', last_line)
            if match:
                footer_num = int(match.group(1))
                offset = pdf_page_num - footer_num
                logger.info(f"Found footer '{footer_num}' on PDF page {pdf_page_num} → offset = {offset}")
                return offset
        
        logger.warning("Could not detect page offset, defaulting to 0")
        return 0
    
    def get_book_toc(self, book_id: str) -> List[TableOfContents]:
        """
        Get stored TOC for a book
        
        Args:
            book_id: Book identifier
            
        Returns:
            List of TOC entries
        """
        return self.book_tocs.get(book_id, [])


# Global processor instance
pdf_processor = PDFProcessor()


def get_pdf_processor() -> PDFProcessor:
    """Get global PDF processor instance"""
    return pdf_processor
