"""
API routes for literature management (book uploads)
"""

import os
import logging
from typing import List, Optional
from pathlib import Path
import tempfile
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/literature", tags=["Literature Management"])


class BookUploadResponse(BaseModel):
    """Response model for book upload"""
    success: bool
    book_id: str
    filename: str
    title: Optional[str] = None
    authors: Optional[str] = None
    pages_extracted: int
    chunks_created: int
    processing_time_seconds: float
    errors: List[str] = []
    warnings: List[str] = []


class BookMetadata(BaseModel):
    """Book metadata"""
    book_id: str
    filename: str
    title: str
    authors: str
    year: Optional[int] = None
    pages_total: int
    chunks_count: int
    upload_date: str
    file_size_mb: float


@router.post("/upload-book", response_model=BookUploadResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    authors: str = Form(...),
    year: Optional[int] = Form(None),
    fingerprint: Optional[str] = Form(None)
):
    """
    Upload a PDF book for literature reference
    
    Args:
        file: PDF file
        title: Book title
        authors: Book authors
        year: Publication year (optional)
        fingerprint: Request fingerprint to link this book to (optional)
        
    Returns:
        Upload and processing result
    """
    import time
    from literature.processor import get_pdf_processor
    from literature.embeddings import get_embedding_service
    
    start_time = time.time()
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Create books directory
    books_dir = Path("app/cache/books")
    books_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate book ID
    import hashlib
    
    book_id = hashlib.md5(f"{title}:{authors}".encode()).hexdigest()[:12]
    book_path = books_dir / f"{book_id}.pdf"
    
    try:
        # Save uploaded file
        with open(book_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size_mb = book_path.stat().st_size / (1024 * 1024)
        
        logger.info(f"Processing uploaded book: {title} by {authors}")
        
        # Process PDF
        pdf_processor = get_pdf_processor()
        processing_result = pdf_processor.process_book(book_path, book_id)
        
        if not processing_result['success']:
            raise Exception(processing_result.get('error', 'PDF processing failed'))
        
        # Generate embeddings and store in ChromaDB
        embedding_service = await get_embedding_service(use_mock=True)  # TODO: Get from app state
        
        book_metadata = {
            'title': title,
            'authors': authors,
            'year': year,
            'fingerprint': fingerprint
        }
        
        embedding_result = embedding_service.add_chunks_to_vector_store(
            processing_result['chunks'],
            book_metadata
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"Book processed successfully in {processing_time:.2f}s")
        
        return BookUploadResponse(
            success=True,
            book_id=book_id,
            filename=file.filename,
            title=title,
            authors=authors,
            pages_extracted=processing_result['total_pages'],
            chunks_created=processing_result['chunks_count'],
            processing_time_seconds=processing_time,
            warnings=[] if not embedding_result.get('mock') else ["Using mock embeddings for development"]
        )
        
    except Exception as e:
        logger.error(f"Error uploading book {title}: {e}")
        
        # Clean up file if it exists
        if book_path.exists():
            book_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload book: {str(e)}"
        )


@router.post("/upload-multiple-books")
async def upload_multiple_books(
    files: List[UploadFile] = File(...),
    fingerprint: Optional[str] = Form(None)
):
    """
    Upload multiple PDF books at once
    
    Args:
        files: List of PDF files
        fingerprint: Request fingerprint to link books to (optional)
        
    Returns:
        List of upload results
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 books allowed per request"
        )
    
    results = []
    
    for file in files:
        try:
            # Extract metadata from filename (basic approach)
            # Expected format: "Author - Title.pdf" or just "Title.pdf"
            filename_parts = Path(file.filename).stem.split(' - ')
            
            if len(filename_parts) >= 2:
                authors = filename_parts[0].strip()
                title = filename_parts[1].strip()
            else:
                title = filename_parts[0].strip()
                authors = "Unknown"
            
            # Upload individual book
            result = await upload_book(
                file=file,
                title=title,
                authors=authors,
                fingerprint=fingerprint
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {e}")
            results.append(BookUploadResponse(
                success=False,
                book_id="",
                filename=file.filename,
                pages_extracted=0,
                chunks_created=0,
                processing_time_seconds=0.0,
                errors=[str(e)]
            ))
    
    return results


@router.get("/list-books")
async def list_books(fingerprint: Optional[str] = None):
    """
    List all uploaded books, optionally filtered by fingerprint
    
    Args:
        fingerprint: Filter by request fingerprint (optional)
        
    Returns:
        List of book metadata
    """
    books_dir = Path("app/cache/books")
    
    if not books_dir.exists():
        return {
            "success": True,
            "books": [],
            "total_count": 0
        }
    
    # TODO: Implement proper book listing from database
    # For now, just list files
    
    pdf_files = list(books_dir.glob("*.pdf"))
    
    return {
        "success": True,
        "books": [
            {
                "book_id": f.stem,
                "filename": f.name,
                "file_size_mb": f.stat().st_size / (1024 * 1024)
            }
            for f in pdf_files
        ],
        "total_count": len(pdf_files)
    }


@router.delete("/delete-book/{book_id}")
async def delete_book(book_id: str):
    """
    Delete an uploaded book
    
    Args:
        book_id: Book ID to delete
        
    Returns:
        Deletion result
    """
    books_dir = Path("app/cache/books")
    book_path = books_dir / f"{book_id}.pdf"
    
    if not book_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book not found: {book_id}"
        )
    
    try:
        book_path.unlink()
        logger.info(f"Deleted book: {book_id}")
        
        return {
            "success": True,
            "message": f"Book {book_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}"
        )


@router.get("/book-info/{book_id}")
async def get_book_info(book_id: str):
    """
    Get detailed information about a book
    
    Args:
        book_id: Book ID
        
    Returns:
        Book metadata and statistics
    """
    books_dir = Path("app/cache/books")
    book_path = books_dir / f"{book_id}.pdf"
    
    if not book_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book not found: {book_id}"
        )
    
    # TODO: Get metadata from database
    # For now, return basic file info
    
    return {
        "success": True,
        "book_id": book_id,
        "filename": book_path.name,
        "file_size_mb": book_path.stat().st_size / (1024 * 1024),
        "upload_date": book_path.stat().st_mtime,
        "status": "uploaded",
        "processed": False
    }
