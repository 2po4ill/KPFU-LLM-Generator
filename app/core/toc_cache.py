"""
TOC Cache Management System
Implements the optimized TOC caching strategy for fast page selection

STRATEGY:
1. Initialization: Extract first 30 pages, detect TOC, cache data
2. Runtime: Use cached TOC for instant page selection
3. On-demand: Extract only needed content pages
"""
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TOCCache:
    """
    TOC Cache Manager for optimized page selection
    
    Cache Structure:
    {
        'book_id': {
            'pdf_path': str,
            'toc_pages': List[int],
            'toc_text': str,
            'page_offset': int,
            'parsed_sections': List[Dict],
            'first_30_pages': List[Dict],
            'cache_created': float,
            'extracted_pages': Dict[int, Dict]  # On-demand page cache
        }
    }
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_dir = Path("app/cache/toc_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_file = self._cache_dir / "toc_cache.json"
        self._load_cache_from_disk()
    
    def _load_cache_from_disk(self):
        """Load existing cache from disk"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded TOC cache with {len(self._cache)} books")
            else:
                logger.info("No existing TOC cache found, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load TOC cache: {e}")
            self._cache = {}
    
    def _save_cache_to_disk(self):
        """Save cache to disk"""
        try:
            # Don't save extracted_pages to disk (too large, regenerate on demand)
            disk_cache = {}
            for book_id, data in self._cache.items():
                disk_data = data.copy()
                if 'extracted_pages' in disk_data:
                    del disk_data['extracted_pages']
                disk_cache[book_id] = disk_data
            
            tmp_path = self._cache_file.with_suffix(self._cache_file.suffix + ".tmp")
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(disk_cache, f, ensure_ascii=False, indent=2)
            # Atomic replace to reduce chance of corrupted cache on interruption
            os.replace(tmp_path, self._cache_file)
            logger.debug(f"Saved TOC cache to {self._cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save TOC cache: {e}")
    
    def is_book_cached(self, book_id: str) -> bool:
        """Check if book TOC is already cached"""
        return book_id in self._cache and self._cache[book_id].get('success', False)
    
    def get_cached_toc_data(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get cached TOC data for a book"""
        if self.is_book_cached(book_id):
            return self._cache[book_id]
        return None
    
    def cache_book_toc(self, book_id: str, toc_data: Dict[str, Any]):
        """Cache TOC data for a book"""
        if toc_data.get('success', False):
            # Initialize extracted_pages cache
            toc_data['extracted_pages'] = {}
            self._cache[book_id] = toc_data
            self._save_cache_to_disk()
            logger.info(f"Cached TOC data for book {book_id}")
        else:
            logger.warning(f"Failed to cache TOC data for book {book_id}: {toc_data.get('error', 'Unknown error')}")
    
    def get_cached_page(self, book_id: str, page_number: int) -> Optional[Dict[str, Any]]:
        """Get a cached page if available"""
        if book_id in self._cache and 'extracted_pages' in self._cache[book_id]:
            return self._cache[book_id]['extracted_pages'].get(page_number)
        return None
    
    def cache_page(self, book_id: str, page_number: int, page_data: Dict[str, Any]):
        """Cache a single page"""
        if book_id in self._cache:
            if 'extracted_pages' not in self._cache[book_id]:
                self._cache[book_id]['extracted_pages'] = {}
            self._cache[book_id]['extracted_pages'][page_number] = page_data
            logger.debug(f"Cached page {page_number} for book {book_id}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_books = len(self._cache)
        total_cached_pages = sum(
            len(data.get('extracted_pages', {})) 
            for data in self._cache.values()
        )
        
        return {
            'total_books': total_books,
            'total_cached_pages': total_cached_pages,
            'cache_file_exists': self._cache_file.exists(),
            'books': list(self._cache.keys())
        }
    
    def clear_cache(self, book_id: Optional[str] = None):
        """Clear cache for specific book or all books"""
        if book_id:
            if book_id in self._cache:
                del self._cache[book_id]
                logger.info(f"Cleared cache for book {book_id}")
        else:
            self._cache.clear()
            logger.info("Cleared all TOC cache")
        
        self._save_cache_to_disk()

# Global cache instance
_toc_cache = None

def get_toc_cache() -> TOCCache:
    """Get global TOC cache instance"""
    global _toc_cache
    if _toc_cache is None:
        _toc_cache = TOCCache()
    return _toc_cache

class OptimizedPDFProcessor:
    """
    Optimized PDF Processor with TOC caching
    Implements the targeted page extraction strategy
    """
    
    def __init__(self, pdf_processor, toc_cache: Optional[TOCCache] = None):
        self.pdf_processor = pdf_processor
        self.toc_cache = toc_cache or get_toc_cache()
    
    async def initialize_book(self, pdf_path: Path, book_id: str) -> Dict[str, Any]:
        """
        Initialize book TOC cache (done once per book)
        
        Args:
            pdf_path: Path to PDF file
            book_id: Unique book identifier
            
        Returns:
            Dictionary with initialization result
        """
        # Check if already cached
        if self.toc_cache.is_book_cached(book_id):
            logger.info(f"Book {book_id} already cached, skipping initialization")
            return {'success': True, 'cached': True}
        
        logger.info(f"Initializing TOC cache for book {book_id}...")
        start_time = time.time()
        
        # Use the PDF processor's TOC cache initialization
        toc_data = self.pdf_processor.initialize_book_toc_cache(pdf_path, book_id)
        
        if toc_data.get('success', False):
            # Cache the data
            self.toc_cache.cache_book_toc(book_id, toc_data)
            
            init_time = time.time() - start_time
            logger.info(f"Book {book_id} initialized in {init_time:.1f}s")
            
            return {
                'success': True,
                'cached': False,
                'initialization_time': init_time,
                'toc_pages': toc_data['toc_pages'],
                'page_offset': toc_data['page_offset']
            }
        else:
            logger.error(f"Failed to initialize book {book_id}: {toc_data.get('error', 'Unknown error')}")
            return {
                'success': False,
                'error': toc_data.get('error', 'Unknown error')
            }
    
    async def get_pages_for_theme(self, book_id: str, theme: str, selected_page_numbers: List[int]) -> Dict[str, Any]:
        """
        Get pages for a specific theme using cached TOC and on-demand page extraction
        
        Args:
            book_id: Book identifier
            theme: Lecture theme
            selected_page_numbers: Page numbers selected by LLM
            
        Returns:
            Dictionary with extracted pages
        """
        start_time = time.time()
        
        # Get cached TOC data
        toc_data = self.toc_cache.get_cached_toc_data(book_id)
        if not toc_data:
            return {
                'success': False,
                'error': f'Book {book_id} not initialized. Call initialize_book() first.'
            }
        
        pdf_path = Path(toc_data['pdf_path'])
        
        # Check which pages are already cached
        cached_pages = []
        pages_to_extract = []
        
        for page_num in selected_page_numbers:
            cached_page = self.toc_cache.get_cached_page(book_id, page_num)
            if cached_page:
                cached_pages.append(cached_page)
            else:
                pages_to_extract.append(page_num)
        
        logger.info(f"Pages for {theme}: {len(cached_pages)} cached, {len(pages_to_extract)} to extract")
        
        # Extract missing pages
        extracted_pages = []
        if pages_to_extract:
            extraction_start = time.time()
            
            pages_data = self.pdf_processor.extract_specific_pages(pdf_path, pages_to_extract)
            
            if pages_data.get('success', False):
                extracted_pages = pages_data['pages']
                
                # Cache the newly extracted pages
                for page_data in extracted_pages:
                    self.toc_cache.cache_page(book_id, page_data['page_number'], page_data)
                
                extraction_time = time.time() - extraction_start
                logger.info(f"Extracted {len(extracted_pages)} pages in {extraction_time:.1f}s")
            else:
                logger.error(f"Failed to extract pages: {pages_data.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f"Failed to extract pages: {pages_data.get('error', 'Unknown error')}"
                }
        
        # Combine cached and extracted pages
        all_pages = cached_pages + extracted_pages
        
        # Sort by page number
        all_pages.sort(key=lambda x: x['page_number'])
        
        total_time = time.time() - start_time
        
        return {
            'success': True,
            'pages': all_pages,
            'total_pages': len(all_pages),
            'cached_pages': len(cached_pages),
            'extracted_pages': len(extracted_pages),
            'processing_time': total_time,
            'toc_data': {
                'toc_text': toc_data['toc_text'],
                'page_offset': toc_data['page_offset'],
                'toc_pages': toc_data['toc_pages']
            }
        }
    
    def get_toc_data(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get cached TOC data for LLM processing"""
        toc_data = self.toc_cache.get_cached_toc_data(book_id)
        if toc_data:
            return {
                'toc_text': toc_data['toc_text'],
                'page_offset': toc_data['page_offset'],
                'toc_pages': toc_data['toc_pages']
            }
        return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.toc_cache.get_cache_stats()

# Global optimized processor instance
_optimized_processor = None

async def get_optimized_pdf_processor(pdf_processor=None) -> OptimizedPDFProcessor:
    """Get global optimized PDF processor instance"""
    global _optimized_processor
    if _optimized_processor is None:
        if pdf_processor is None:
            from literature.processor import get_pdf_processor
            pdf_processor = get_pdf_processor()
        _optimized_processor = OptimizedPDFProcessor(pdf_processor)
    return _optimized_processor