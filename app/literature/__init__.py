"""
Literature processing module
"""

from .processor import PDFProcessor, BookChunk, TableOfContents, get_pdf_processor

# Optional embeddings import (requires chromadb)
try:
    from .embeddings import EmbeddingService, get_embedding_service
    __all__ = [
        'PDFProcessor',
        'BookChunk',
        'TableOfContents',
        'get_pdf_processor',
        'EmbeddingService',
        'get_embedding_service'
    ]
except ImportError:
    __all__ = [
        'PDFProcessor',
        'BookChunk',
        'TableOfContents',
        'get_pdf_processor'
    ]
