"""
API routes for RPD processing
"""

import asyncio
import base64
import json
import os
import logging
from typing import Any, Callable, Dict, List, Literal, Optional
from pathlib import Path
import tempfile
from datetime import datetime
import shutil
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator

from core.model_manager import ModelManager
from rpd.processor import get_rpd_processor, RPDProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpd", tags=["RPD Processing"])
_RPD_SESSION_CACHE: dict[str, dict] = {}
_PACKAGE_DRAFTS: dict[str, dict] = {}


def _draft_key(fingerprint: str, theme_title: str) -> str:
    return f"{fingerprint}::{theme_title}"


def _user_sources_store_key(fingerprint: str, theme_title: str) -> str:
    return f"{fingerprint}::{theme_title}"


def _get_user_sources_for_theme(rpd_data: Dict[str, Any], theme_title: str) -> List[Dict[str, Any]]:
    by_theme = rpd_data.get("user_sources_by_theme") or {}
    if isinstance(by_theme, dict):
        items = by_theme.get(theme_title) or []
        if isinstance(items, list):
            return list(items)
    return []


def _set_user_sources_for_theme(
    rpd_data: Dict[str, Any], theme_title: str, sources: List[Dict[str, Any]]
) -> None:
    by_theme = dict(rpd_data.get("user_sources_by_theme") or {})
    by_theme[theme_title] = sources
    rpd_data["user_sources_by_theme"] = by_theme


def _book_catalog_from_rpd(rpd_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """book_id -> {title, url} from resolved PDF sources and literature."""
    catalog: Dict[str, Dict[str, str]] = {}
    for src in rpd_data.get("discovered_sources") or []:
        bid = src.get("book_id")
        if not bid:
            continue
        catalog[str(bid)] = {
            "title": (src.get("title_hint") or src.get("title") or bid).strip(),
            "url": (src.get("normalized_url") or src.get("url") or "").strip(),
        }
    for ref in rpd_data.get("literature_references") or []:
        if not isinstance(ref, dict):
            continue
        url = (ref.get("url") or "").strip()
        if not url:
            continue
        title = (ref.get("title") or ref.get("authors") or "").strip()
        for bid, meta in list(catalog.items()):
            if meta.get("url") == url and title:
                meta["title"] = title
    return catalog


def _book_catalog_with_user_sources(
    rpd_data: Dict[str, Any], theme_title: str, extra: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Dict[str, str]]:
    catalog = _book_catalog_from_rpd(rpd_data)
    from sources.user_attachments import normalize_user_sources

    for src in normalize_user_sources(extra or _get_user_sources_for_theme(rpd_data, theme_title)):
        catalog[src["id"]] = {"title": src["title"], "url": ""}
    return catalog


def _attachment_disposition(filename: str) -> str:
    """Content-Disposition header value (latin-1 safe + UTF-8 filename*)."""
    name = (filename or "download").strip()
    ascii_fallback = "".join(
        c if ord(c) < 128 and (c.isalnum() or c in "._-") else "_"
        for c in name
    ).strip("._") or "download"
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quote(name, safe="")}'


async def require_api_key(request: Request = None):
    """Optional API-key auth (enabled only when settings.api_key is set)."""
    from core.config import settings

    if request is None:
        return

    if not settings.api_key:
        return

    provided = request.headers.get("X-API-Key")
    if provided != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


async def require_rate_limit(request: Request = None, route_key: str = ""):
    """Optional in-process rate limiting for heavy endpoints."""
    from core.config import settings
    from core.rate_limiter import rate_limiter

    if request is None:
        return

    if not settings.enable_rate_limit:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{route_key}"
    allowed = await rate_limiter.allow(
        key=key,
        limit=settings.rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )


class RPDProcessingResponse(BaseModel):
    """Response model for RPD processing"""
    success: bool
    file_path: str
    processing_time_seconds: float
    extracted_data: Optional[dict] = None
    errors: List[str] = []
    warnings: List[str] = []
    rpd_id: Optional[str] = None


class RPDInputData(BaseModel):
    """Input model for RPD data from external sources (e.g., Telegram bot)"""
    subject_title: str = Field(..., description="Название дисциплины")
    academic_degree: str = Field(..., description="Уровень образования: bachelor, master, phd")
    profession: str = Field(..., description="Направление подготовки")
    total_hours: int = Field(..., gt=0, description="Общая трудоемкость в часах")
    
    # Optional metadata
    department: Optional[str] = Field(None, description="Кафедра")
    faculty: Optional[str] = Field(None, description="Факультет")
    year: Optional[int] = Field(None, description="Год составления")
    semester: Optional[str] = Field(None, description="Семестр")
    
    # Content
    lecture_themes: Optional[List[dict]] = Field(None, description="Темы лекций")
    lab_examples: Optional[List[dict]] = Field(None, description="Примеры лабораторных работ")
    literature_references: Optional[List[dict]] = Field(None, description="Список литературы")
    
    @validator('academic_degree')
    def validate_degree(cls, v):
        valid_degrees = ['bachelor', 'master', 'phd']
        if v.lower() not in valid_degrees:
            raise ValueError(f"academic_degree must be one of: {', '.join(valid_degrees)}")
        return v.lower()


class RPDDataResponse(BaseModel):
    """Response model for RPD data submission"""
    success: bool
    rpd_id: Optional[str] = None
    message: str
    data: Optional[dict] = None
    errors: List[str] = []
    warnings: List[str] = []


class RPDSummaryResponse(BaseModel):
    """Response model for RPD processing summary"""
    total_files: int
    successful_files: int
    failed_files: int
    success_rate: float
    total_processing_time_seconds: float
    average_processing_time_seconds: float


async def get_model_manager() -> ModelManager:
    """Dependency to get model manager"""
    from main import app
    return app.state.model_manager


async def get_rpd_processor_instance(model_manager: ModelManager = Depends(get_model_manager)) -> RPDProcessor:
    """Dependency to get RPD processor"""
    return get_rpd_processor(model_manager)


@router.post("/submit-data", response_model=RPDDataResponse)
async def submit_rpd_data(
    rpd_data: RPDInputData,
    processor: RPDProcessor = Depends(get_rpd_processor_instance),
    request: Request = None,
):
    """
    Submit RPD data directly (e.g., from Telegram bot or web form)
    
    Args:
        rpd_data: RPD data as JSON
        processor: RPD processor instance
        
    Returns:
        Submission result with validation and request fingerprint
    """
    try:
        await require_api_key(request)
        await require_rate_limit(request, "rpd_submit_data")

        logger.info(f"Received RPD data submission for: {rpd_data.subject_title}")
        
        # Generate request fingerprint
        from core.database import generate_request_fingerprint
        request_dict = rpd_data.dict()
        fingerprint = generate_request_fingerprint(request_dict)
        
        logger.info(f"Generated request fingerprint: {fingerprint}")
        
        # Convert input data to RPD format
        from rpd.extractor import RPDData, LectureTheme, LabExample, LiteratureReference
        
        # Create RPDData object
        rpd_obj = RPDData(
            subject_title=rpd_data.subject_title,
            academic_degree=rpd_data.academic_degree,
            profession=rpd_data.profession,
            total_hours=rpd_data.total_hours,
            department=rpd_data.department,
            faculty=rpd_data.faculty,
            year=rpd_data.year,
            semester=rpd_data.semester
        )
        
        # Add lecture themes if provided
        if rpd_data.lecture_themes:
            rpd_obj.lecture_themes = [
                LectureTheme(
                    title=theme.get('title', ''),
                    order=theme.get('order', idx + 1),
                    hours=theme.get('hours', 2.0),
                    description=theme.get('description'),
                    subtopics=theme.get('subtopics'),
                )
                for idx, theme in enumerate(rpd_data.lecture_themes)
            ]
        
        # Add lab examples if provided
        if rpd_data.lab_examples:
            rpd_obj.lab_examples = [
                LabExample(
                    title=lab.get('title', ''),
                    description=lab.get('description', ''),
                    theme_relation=lab.get('theme_relation'),
                    estimated_hours=lab.get('estimated_hours', 2.0)
                )
                for lab in rpd_data.lab_examples
            ]
        
        # Add literature references if provided
        if rpd_data.literature_references:
            rpd_obj.literature_references = [
                LiteratureReference(
                    authors=ref.get('authors', ''),
                    title=ref.get('title', ''),
                    year=ref.get('year'),
                    pages=ref.get('pages'),
                    publisher=ref.get('publisher'),
                    isbn=ref.get('isbn')
                )
                for ref in rpd_data.literature_references
            ]
        
        # Validate completeness
        validation_result = processor._validate_completeness(rpd_obj)
        
        # Persist validated request by fingerprint so generation can reuse it
        rpd_dict = processor.extractor.to_dict(rpd_obj)
        from core.database import get_db, RPDRequest
        from sqlalchemy import select

        async for db in get_db():
            existing_res = await db.execute(
                select(RPDRequest).where(RPDRequest.request_fingerprint == fingerprint)
            )
            existing = existing_res.scalar_one_or_none()

            if existing:
                existing.request_data = rpd_dict
            else:
                db.add(RPDRequest(request_fingerprint=fingerprint, request_data=rpd_dict))

            await db.commit()
            break

        return RPDDataResponse(
            success=True,
            rpd_id=fingerprint,  # Use fingerprint as ID
            message=f"RPD data validated. Fingerprint: {fingerprint}. Completeness: {validation_result['completeness_score']:.2%}",
            data=rpd_dict,
            warnings=validation_result['warnings']
        )
        
    except Exception as e:
        logger.error(f"Error processing RPD data submission: {e}")
        return RPDDataResponse(
            success=False,
            message="Failed to process RPD data",
            errors=[str(e)]
        )


@router.post("/upload", response_model=RPDProcessingResponse)
async def upload_and_process_rpd(
    file: UploadFile = File(...),
    processor: RPDProcessor = Depends(get_rpd_processor_instance)
):
    """
    Upload and process a single RPD document
    
    Args:
        file: Uploaded RPD file (PDF, DOCX, XLSX)
        processor: RPD processor instance
        
    Returns:
        Processing result
    """
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.xlsx', '.xls'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create temporary file
    temp_dir = Path(tempfile.gettempdir()) / "kpfu_rpd_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file_path = temp_dir / f"{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Processing uploaded RPD file: {file.filename}")
        
        # Process the file
        result = await processor.process_rpd_file(temp_file_path)
        
        # Clean up file path in response
        result['file_path'] = file.filename

        rpd_id = None
        if result.get("success") and result.get("extracted_data"):
            try:
                from core.database import get_db, RPDRequest, generate_request_fingerprint
                from sqlalchemy import select

                ed = result["extracted_data"]
                rpd_id = generate_request_fingerprint(ed)
                payload = dict(ed)
                payload.pop("source_resolution", None)
                _RPD_SESSION_CACHE[rpd_id] = payload
                async for db in get_db():
                    existing_res = await db.execute(
                        select(RPDRequest).where(RPDRequest.request_fingerprint == rpd_id)
                    )
                    existing = existing_res.scalar_one_or_none()
                    if existing:
                        existing.request_data = payload
                    else:
                        db.add(RPDRequest(request_fingerprint=rpd_id, request_data=payload))
                    await db.commit()
                    break
            except Exception as ex:
                logger.warning("Could not persist RPD session to DB: %s", ex)

        return RPDProcessingResponse(
            success=result.get("success", False),
            file_path=file.filename,
            processing_time_seconds=result.get("processing_time_seconds", 0),
            extracted_data=result.get("extracted_data"),
            errors=result.get("errors") or [],
            warnings=result.get("warnings") or [],
            rpd_id=rpd_id,
        )
        
    except Exception as e:
        logger.error(f"Error processing RPD file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process RPD file: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")


@router.post("/upload-multiple", response_model=List[RPDProcessingResponse])
async def upload_and_process_multiple_rpd(
    files: List[UploadFile] = File(...),
    processor: RPDProcessor = Depends(get_rpd_processor_instance)
):
    """
    Upload and process multiple RPD documents
    
    Args:
        files: List of uploaded RPD files
        processor: RPD processor instance
        
    Returns:
        List of processing results
    """
    if len(files) > 10:  # Limit number of files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per request"
        )
    
    results = []
    temp_files = []
    
    try:
        # Create temporary directory
        temp_dir = Path(tempfile.gettempdir()) / "kpfu_rpd_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        # Save all files first
        for file in files:
            # Validate file type
            allowed_extensions = {'.pdf', '.docx', '.doc', '.xlsx', '.xls'}
            file_extension = Path(file.filename).suffix.lower()
            
            if file_extension not in allowed_extensions:
                results.append(RPDProcessingResponse(
                    success=False,
                    file_path=file.filename,
                    processing_time_seconds=0,
                    errors=[f"Unsupported file type: {file_extension}"]
                ))
                continue
            
            # Save file
            temp_file_path = temp_dir / f"{file.filename}"
            temp_files.append(temp_file_path)
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        
        # Process all valid files
        valid_files = [f for f in temp_files if f.exists()]
        if valid_files:
            processing_results = await processor.process_multiple_rpd_files(valid_files)
            
            # Convert results and clean up file paths
            for result in processing_results:
                result['file_path'] = Path(result['file_path']).name
                results.append(RPDProcessingResponse(**result))
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing multiple RPD files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process RPD files: {str(e)}"
        )
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")


@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported RPD file formats
    
    Returns:
        List of supported file extensions
    """
    return {
        "supported_formats": [".pdf", ".docx", ".doc", ".xlsx", ".xls"],
        "descriptions": {
            ".pdf": "PDF documents",
            ".docx": "Microsoft Word documents (2007+)",
            ".doc": "Microsoft Word documents (legacy)",
            ".xlsx": "Microsoft Excel spreadsheets (2007+)",
            ".xls": "Microsoft Excel spreadsheets (legacy)"
        }
    }


@router.post("/validate-structure")
async def validate_rpd_structure(
    file: UploadFile = File(...),
    processor: RPDProcessor = Depends(get_rpd_processor_instance)
):
    """
    Validate RPD document structure without full processing
    
    Args:
        file: Uploaded RPD file
        processor: RPD processor instance
        
    Returns:
        Structure validation result
    """
    # Create temporary file
    temp_dir = Path(tempfile.gettempdir()) / "kpfu_rpd_validation"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file_path = temp_dir / f"{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse the file (without LLM extraction)
        from rpd.parsers import parse_rpd_document
        parsed_data = parse_rpd_document(temp_file_path)
        
        # Basic validation
        validation_result = {
            "file_name": file.filename,
            "file_type": parsed_data.get("file_type"),
            "parseable": True,
            "content_length": len(parsed_data.get("raw_text", "")),
            "has_content": bool(parsed_data.get("raw_text", "").strip()),
            "structure": {}
        }
        
        # Add format-specific structure info
        if parsed_data.get("file_type") == "pdf":
            validation_result["structure"] = {
                "pages": parsed_data.get("pages", 0),
                "has_metadata": bool(parsed_data.get("metadata", {}))
            }
        elif parsed_data.get("file_type") == "docx":
            validation_result["structure"] = {
                "paragraphs": len(parsed_data.get("paragraphs", [])),
                "tables": len(parsed_data.get("tables", [])),
                "has_metadata": bool(parsed_data.get("metadata", {}))
            }
        elif parsed_data.get("file_type") in ["xlsx", "xls"]:
            validation_result["structure"] = {
                "sheets": len(parsed_data.get("sheets", {})),
                "sheet_names": parsed_data.get("sheet_names", [])
            }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating RPD structure for {file.filename}: {e}")
        return {
            "file_name": file.filename,
            "parseable": False,
            "error": str(e)
        }
    
    finally:
        # Clean up temporary file
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")


@router.get("/processing-stats")
async def get_processing_stats():
    """
    Get RPD processing statistics
    
    Returns:
        Processing statistics and performance metrics
    """
    # This would typically come from a database or metrics store
    # For now, return mock statistics
    return {
        "total_processed": 0,
        "success_rate": 0.0,
        "average_processing_time": 0.0,
        "supported_formats": [".pdf", ".docx", ".doc", ".xlsx", ".xls"],
        "performance_targets": {
            "parsing_time_seconds": 5.0,
            "extraction_time_seconds": 15.0,
            "total_time_seconds": 20.0
        }
    }


@router.post("/generate-content")
async def generate_content(
    fingerprint: str,
    theme_title: str,
    content_type: str = "lecture",
    book_ids: Optional[List[str]] = None,
    processor: RPDProcessor = Depends(get_rpd_processor_instance),
    model_manager: ModelManager = Depends(get_model_manager),
    request: Request = None,
):
    """
    Generate content (lecture or lab) for a specific theme
    Uses request fingerprint to retrieve RPD data
    
    Args:
        fingerprint: Request fingerprint from /submit-data
        theme_title: Title of the lecture theme to generate
        content_type: Type of content (lecture or lab)
        book_ids: List of book IDs to use (optional, uses all if not specified)
        
    Returns:
        Generated content with citations and metadata
    """
    try:
        await require_api_key(request)
        await require_rate_limit(request, "generate_content")

        from core.database import get_db, GeneratedContent, RPDRequest
        from sqlalchemy import select
        from literature.processor import get_pdf_processor
        from generation.generator_v4 import get_production_content_generator
        
        logger.info(f"Generating content for fingerprint {fingerprint}, theme {theme_title}")
        if content_type != "lecture":
            return {
                "success": False,
                "message": f"Unsupported content_type: {content_type}. Only 'lecture' is implemented.",
                "fingerprint": fingerprint,
                "theme_title": theme_title,
            }

        db = None
        db_available = False
        existing_content = None
        rpd_data = None
        try:
            async for _db in get_db():
                db = _db
                db_available = True
                result = await db.execute(
                    select(GeneratedContent).where(
                        GeneratedContent.request_fingerprint == fingerprint,
                        GeneratedContent.theme_title == theme_title,
                        GeneratedContent.content_type == content_type
                    )
                )
                existing_content = result.scalar_one_or_none()

                if existing_content:
                    logger.info(f"Returning cached content for fingerprint {fingerprint}, theme {theme_title}")
                    return {
                        "success": True,
                        "fingerprint": fingerprint,
                        "theme_title": theme_title,
                        "content_type": content_type,
                        "content": existing_content.content,
                        "citations": existing_content.citations,
                        "sources_used": existing_content.sources_used,
                        "generation_time_seconds": existing_content.generation_time_seconds,
                        "confidence_score": existing_content.confidence_score,
                        "cached": True,
                        "created_date": existing_content.created_date.isoformat()
                    }

                rpd_req_res = await db.execute(
                    select(RPDRequest).where(RPDRequest.request_fingerprint == fingerprint)
                )
                rpd_req = rpd_req_res.scalar_one_or_none()
                if rpd_req:
                    rpd_data = rpd_req.request_data
                break
        except Exception as db_ex:
            logger.warning("generate_content db unavailable, using in-memory cache: %s", db_ex)
            db_available = False

        if rpd_data is None:
            cached = _RPD_SESSION_CACHE.get(fingerprint)
            if cached:
                rpd_data = cached
        if rpd_data is None:
            return {
                "success": False,
                "message": "No RPD request found for this fingerprint. Upload RPD first.",
                "fingerprint": fingerprint,
                "theme_title": theme_title,
            }

        # Get book IDs if not provided
        if not book_ids:
            # Get all available books
            from pathlib import Path
            books_dir = Path("app/cache/books")
            if books_dir.exists():
                book_ids = [f.stem for f in books_dir.glob("*.pdf")]

        if not book_ids:
            return {
                "success": False,
                "message": "No books available. Please upload books first.",
                "fingerprint": fingerprint,
                "theme_title": theme_title
            }

        pdf_processor = get_pdf_processor()

        # Get production generator v4 (canonical prod entrypoint)
        generator = await get_production_content_generator(
            model_manager=model_manager,
            pdf_processor=pdf_processor,
            use_mock=getattr(model_manager, "use_mock_services", False),
        )

        # Ensure TOC cache is initialized for all books we will use
        books_dir = Path("app/cache/books")
        valid_book_ids = []
        for bid in book_ids:
            book_path = books_dir / f"{bid}.pdf"
            if not book_path.exists():
                logger.warning(f"Skipping missing book file for book_id={bid}: {book_path}")
                continue
            await generator.initialize_book(str(book_path), bid)
            valid_book_ids.append(bid)

        if not valid_book_ids:
            return {
                "success": False,
                "message": "No valid books found (files are missing). Please upload books first.",
                "fingerprint": fingerprint,
                "theme_title": theme_title,
            }

        # Generate content
        generation_result = await generator.generate_lecture_optimized(
            theme=theme_title,
            rpd_data=rpd_data,
            book_ids=valid_book_ids,
        )

        if not generation_result.success:
            return {
                "success": False,
                "message": "Content generation failed",
                "errors": generation_result.errors,
                "warnings": generation_result.warnings
            }

        if db_available and db is not None:
            try:
                # Store generated content
                new_content = GeneratedContent(
                    request_fingerprint=fingerprint,
                    request_data=rpd_data,
                    content_type=content_type,
                    theme_title=theme_title,
                    content=generation_result.content,
                    citations=generation_result.citations,
                    sources_used=generation_result.sources_used,
                    generation_time_seconds=generation_result.generation_time_seconds,
                    confidence_score=generation_result.confidence_score
                )
                db.add(new_content)
                await db.commit()
                await db.refresh(new_content)
                created_date = new_content.created_date.isoformat()
            except Exception as store_ex:
                logger.warning("Could not persist generated content to DB: %s", store_ex)
                created_date = datetime.utcnow().isoformat() + "Z"
        else:
            created_date = datetime.utcnow().isoformat() + "Z"

        return {
            "success": True,
            "fingerprint": fingerprint,
            "theme_title": theme_title,
            "content_type": content_type,
            "content": generation_result.content,
            "citations": generation_result.citations,
            "sources_used": generation_result.sources_used,
            "generation_time_seconds": generation_result.generation_time_seconds,
            "confidence_score": generation_result.confidence_score,
            "step_times": generation_result.step_times,
            "warnings": generation_result.warnings,
            "cached": False,
            "created_date": created_date
        }
            
    except Exception as e:
        logger.error(f"Error generating content: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/retrieve-content/{fingerprint}")
async def retrieve_content_by_fingerprint(fingerprint: str):
    """
    Retrieve all generated content for a specific request fingerprint
    
    Args:
        fingerprint: Request fingerprint from /submit-data
        
    Returns:
        All generated content associated with this fingerprint
    """
    try:
        from core.database import get_db, GeneratedContent
        from sqlalchemy import select
        
        async for db in get_db():
            result = await db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.request_fingerprint == fingerprint
                ).order_by(GeneratedContent.created_date.desc())
            )
            content_items = result.scalars().all()
            
            if not content_items:
                return {
                    "success": False,
                    "message": f"No content found for fingerprint: {fingerprint}",
                    "fingerprint": fingerprint
                }
            
            return {
                "success": True,
                "fingerprint": fingerprint,
                "request_data": content_items[0].request_data,
                "content_count": len(content_items),
                "content_items": [
                    {
                        "id": str(item.id),
                        "theme_title": item.theme_title,
                        "content_type": item.content_type,
                        "content": item.content,
                        "citations": item.citations,
                        "sources_used": item.sources_used,
                        "generation_time_seconds": item.generation_time_seconds,
                        "confidence_score": item.confidence_score,
                        "created_date": item.created_date.isoformat()
                    }
                    for item in content_items
                ]
            }
            
    except Exception as e:
        logger.error(f"Error retrieving content: {e}")
        return {
            "success": False,
            "error": str(e)
        }


class SourceResolveRequest(BaseModel):
    """Resolve discovered direct PDF sources for a persisted RPD fingerprint."""
    fingerprint: str = Field(..., description="rpd_id from upload or submit-data")
    source_ids: Optional[List[str]] = Field(
        None, description="If set, only these source ids; else all direct_pdf pending"
    )


def _source_counts(sources: List[dict]) -> dict:
    counts_by_status = {}
    counts_by_kind = {}
    for s in sources:
        st = s.get("status") or "unknown"
        kd = s.get("kind") or "unknown"
        counts_by_status[st] = counts_by_status.get(st, 0) + 1
        counts_by_kind[kd] = counts_by_kind.get(kd, 0) + 1
    return {
        "counts_by_status": counts_by_status,
        "counts_by_kind": counts_by_kind,
        "total_sources": len(sources),
    }


@router.get("/session/{fingerprint}")
async def get_rpd_session(fingerprint: str, request: Request = None):
    """Return persisted RPD request_data (themes, literature, discovered_sources)."""
    try:
        await require_api_key(request)
        from core.database import get_db, RPDRequest
        from sqlalchemy import select

        data = None
        try:
            async for db in get_db():
                res = await db.execute(
                    select(RPDRequest).where(RPDRequest.request_fingerprint == fingerprint)
                )
                row = res.scalar_one_or_none()
                if row:
                    data = row.request_data or {}
                break
        except Exception as db_ex:
            logger.warning("get_rpd_session db unavailable, using cache: %s", db_ex)

        if data is None:
            data = _RPD_SESSION_CACHE.get(fingerprint)
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown fingerprint")

        sources = list(data.get("discovered_sources") or [])
        return {
            "success": True,
            "fingerprint": fingerprint,
            "request_data": data,
            **_source_counts(sources),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_rpd_session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-sources")
async def resolve_rpd_sources(
    body: SourceResolveRequest,
    model_manager: ModelManager = Depends(get_model_manager),
    request: Request = None,
):
    """
    Download direct PDF links from discovered_sources and register books (embeddings + TOC).
    http_page (EBS) sources are skipped until a browser resolver exists.
    """
    await require_api_key(request)
    await require_rate_limit(request, "rpd_resolve_sources")

    from core.database import get_db, RPDRequest
    from sqlalchemy import select
    from sources.direct_pdf import download_and_register_direct_pdf

    async for db in get_db():
        row = None
        data = None
        try:
            res = await db.execute(
                select(RPDRequest).where(RPDRequest.request_fingerprint == body.fingerprint)
            )
            row = res.scalar_one_or_none()
            if row:
                data = dict(row.request_data)
        except Exception as db_ex:
            logger.warning("resolve_rpd_sources db unavailable, using cache: %s", db_ex)

        if data is None:
            cached = _RPD_SESSION_CACHE.get(body.fingerprint)
            if cached:
                data = dict(cached)
        if data is None:
            raise HTTPException(status_code=404, detail="Unknown fingerprint")

        sources = list(data.get("discovered_sources") or [])
        want = set(body.source_ids) if body.source_ids else None
        results = []

        for src in sources:
            sid = src.get("id")
            if want is not None and sid not in want:
                continue
            kind = src.get("kind")
            if kind == "http_page":
                src["status"] = "skipped"
                src["error"] = "ebs_or_portal_link_not_automated"
                results.append(
                    {
                        "id": sid,
                        "status": src["status"],
                        "book_id": src.get("book_id"),
                        "sha256": src.get("sha256"),
                        "error": src["error"],
                    }
                )
                continue
            if kind != "direct_pdf":
                src["status"] = "skipped"
                src["error"] = "unsupported_kind"
                results.append(
                    {
                        "id": sid,
                        "status": src["status"],
                        "book_id": src.get("book_id"),
                        "sha256": src.get("sha256"),
                        "error": src["error"],
                    }
                )
                continue
            if src.get("status") in ("ok", "duplicate_ok") and src.get("book_id"):
                src["status"] = "duplicate_ok"
                results.append(
                    {
                        "id": sid,
                        "status": src.get("status"),
                        "book_id": src.get("book_id"),
                        "sha256": src.get("sha256"),
                        "error": None,
                    }
                )
                continue

            url = src.get("normalized_url") or src.get("url")
            title_hint = src.get("title_hint")
            out = await download_and_register_direct_pdf(
                url,
                model_manager=model_manager,
                fingerprint=body.fingerprint,
                title=title_hint,
                authors=None,
            )
            if out.get("success"):
                src["sha256"] = out.get("sha256")
                src["storage_relpath"] = out.get("storage_relpath")
                src["book_id"] = out.get("book_id")
                src["error"] = None
                if out.get("duplicate"):
                    src["status"] = "duplicate_ok"
                else:
                    src["status"] = "ok"
            else:
                src["status"] = "failed"
                src["error"] = out.get("error")

            results.append(
                {
                    "id": sid,
                    "status": src.get("status"),
                    "book_id": src.get("book_id"),
                    "sha256": src.get("sha256"),
                    "error": src.get("error"),
                }
            )

        data["discovered_sources"] = sources
        data["source_resolution"] = {
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "results": results,
        }
        _RPD_SESSION_CACHE[body.fingerprint] = data
        if row is not None:
            row.request_data = data
            await db.commit()
        return {
            "success": True,
            "fingerprint": body.fingerprint,
            "results": results,
            "discovered_sources": sources,
            **_source_counts(sources),
        }

    cached = _RPD_SESSION_CACHE.get(body.fingerprint)
    if not cached:
        raise HTTPException(status_code=404, detail="Unknown fingerprint")
    sources = list(cached.get("discovered_sources") or [])
    return {
        "success": True,
        "fingerprint": body.fingerprint,
        "results": [],
        "discovered_sources": sources,
        **_source_counts(sources),
    }


class PackageGenerateOptions(BaseModel):
    generate_presentation: bool = Field(True, description="PPTX slides")
    generate_lab: bool = Field(True, description="Lab worksheet markdown")
    generate_selfcheck: bool = Field(True, description="Self-check markdown")
    pipeline_mode: Optional[str] = Field(
        None, description="claims | chunk_rag | facet_rag (default from server env)"
    )


class UserSourceItem(BaseModel):
    id: Optional[str] = None
    title: str = "Дополнительный источник"
    text: str = Field(..., min_length=1, description="Markdown или plain text")


class UserSourcesBody(BaseModel):
    fingerprint: str
    theme_title: str
    sources: List[UserSourceItem] = Field(default_factory=list)


class PackageGenerateRequest(BaseModel):
    fingerprint: str
    theme_title: str
    book_ids: Optional[List[str]] = None
    user_sources: Optional[List[UserSourceItem]] = None
    options: PackageGenerateOptions = Field(default_factory=PackageGenerateOptions)


class PackageExportRequest(BaseModel):
    fingerprint: str = ""
    theme_title: str
    lecture_md: str
    lab_md: str = ""
    selfcheck_md: str = ""
    moodle_questions_xml: str = ""
    presentation_pptx_base64: str = ""
    presentation_slides_json: str = ""
    export_format: Literal["scorm", "pdf_all", "pptx", "presentation_pdf"] = "scorm"


class PackageDraftBody(BaseModel):
    fingerprint: str
    theme_title: str
    lecture_md: str
    lab_md: str = ""
    selfcheck_md: str = ""
    moodle_questions_xml: str = ""
    presentation_pptx_base64: str = ""
    presentation_slides_json: str = ""
    approved: bool = False


def _load_rpd_data_for_fingerprint(fingerprint: str) -> dict:
    cached = _RPD_SESSION_CACHE.get(fingerprint)
    if cached:
        return cached
    raise HTTPException(status_code=404, detail="Unknown fingerprint. Upload RPD first.")


async def _resolve_book_ids(book_ids: Optional[List[str]]) -> List[str]:
    if book_ids:
        return book_ids
    books_dir = Path("app/cache/books")
    if books_dir.exists():
        return [f.stem for f in books_dir.glob("*.pdf")]
    return []


async def _execute_generate_package(
    body: PackageGenerateRequest,
    model_manager: ModelManager,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    from api.presentation_preview import store_presentation_preview
    from core.package_settings import package_settings_override
    from generation.generator_v4 import get_production_content_generator
    from generation.provenance_md import lecture_with_visible_provenance
    from literature.processor import get_pdf_processor

    rpd_data = _load_rpd_data_for_fingerprint(body.fingerprint)
    from sources.user_attachments import normalize_user_sources

    user_sources = normalize_user_sources(
        [s.model_dump() for s in (body.user_sources or [])]
        or _get_user_sources_for_theme(rpd_data, body.theme_title)
    )
    if body.user_sources is not None:
        _set_user_sources_for_theme(rpd_data, body.theme_title, user_sources)
        _RPD_SESSION_CACHE[body.fingerprint] = rpd_data

    book_ids = await _resolve_book_ids(body.book_ids)
    if not book_ids and not user_sources:
        return {
            "success": False,
            "message": "No books or user attachments. Add PDF sources or attach your own texts.",
            "fingerprint": body.fingerprint,
        }

    opts = body.options
    pdf_processor = get_pdf_processor()
    generator = await get_production_content_generator(
        model_manager=model_manager,
        pdf_processor=pdf_processor,
        use_mock=getattr(model_manager, "use_mock_services", False),
    )
    if hasattr(generator, "set_book_catalog"):
        generator.set_book_catalog(_book_catalog_with_user_sources(rpd_data, body.theme_title, user_sources))

    books_dir = Path("app/cache/books")
    valid_book_ids = []
    for bid in book_ids or []:
        book_path = books_dir / f"{bid}.pdf"
        if not book_path.exists():
            logger.warning("Skipping missing book: %s", book_path)
            continue
        await generator.initialize_book(str(book_path), bid)
        valid_book_ids.append(bid)

    if not valid_book_ids and not user_sources:
        return {
            "success": False,
            "message": "No valid book files on disk and no user attachments.",
            "fingerprint": body.fingerprint,
        }

    with package_settings_override(
        lab_enabled=opts.generate_lab,
        selfcheck_enabled=opts.generate_selfcheck,
        pptx_enabled=opts.generate_presentation,
        moodle_enabled=opts.generate_selfcheck,
        pipeline_mode=opts.pipeline_mode,
    ):
        result = await generator.generate_package_optimized(
            theme=body.theme_title,
            rpd_data=rpd_data,
            book_ids=valid_book_ids,
            user_sources=user_sources,
            on_progress=on_progress,
        )

    if not result.success:
        return {
            "success": False,
            "message": "Package generation failed",
            "errors": result.errors,
            "warnings": result.warnings,
            "fingerprint": body.fingerprint,
        }

    pptx_b64 = ""
    if result.presentation_pptx:
        pptx_b64 = base64.standard_b64encode(result.presentation_pptx).decode("ascii")

    prov_raw = getattr(generator, "_last_lecture_with_provenance", None) or ""
    lecture_prov = (
        lecture_with_visible_provenance(prov_raw) if prov_raw else result.lecture_content
    )

    presentation_preview = None
    prev_data = getattr(generator, "_last_presentation_preview", None) or {}
    if prev_data.get("slides"):
        pres_manifest = []
        assets_dir = Path(str(prev_data.get("assets_dir") or ""))
        man_path = assets_dir / "presentation_manifest.json"
        if man_path.is_file():
            try:
                pres_manifest = json.loads(man_path.read_text(encoding="utf-8")).get("slides") or []
            except Exception:
                pres_manifest = []
        presentation_preview = store_presentation_preview(
            body.fingerprint,
            body.theme_title,
            slides=list(prev_data.get("slides") or []),
            resolved_paths=list(prev_data.get("resolved_paths") or []),
            manifest_entries=pres_manifest,
        )

    return {
        "success": True,
        "fingerprint": body.fingerprint,
        "theme_title": body.theme_title,
        "lecture_content": result.lecture_content,
        "lecture_content_provenance": lecture_prov,
        "lab_content": result.lab_content or "",
        "selfcheck_content": result.selfcheck_content or "",
        "moodle_questions_xml": result.moodle_questions_xml or "",
        "presentation_slides_json": result.presentation_slides_json or "",
        "presentation_pptx_base64": pptx_b64,
        "presentation_preview": presentation_preview,
        "review_report": result.review_report_content or "",
        "generation_time_seconds": result.generation_time_seconds,
        "confidence_score": result.confidence_score,
        "step_times": result.step_times,
        "warnings": result.warnings,
        "options_used": opts.model_dump(),
    }


@router.get("/user-sources")
async def get_user_sources(
    fingerprint: str,
    theme_title: str,
    request: Request = None,
):
    """List user-attached priority sources for a theme."""
    await require_api_key(request)
    rpd_data = _load_rpd_data_for_fingerprint(fingerprint)
    from sources.user_attachments import normalize_user_sources

    sources = normalize_user_sources(_get_user_sources_for_theme(rpd_data, theme_title))
    return {
        "success": True,
        "fingerprint": fingerprint,
        "theme_title": theme_title,
        "sources": sources,
    }


@router.put("/user-sources")
async def put_user_sources(body: UserSourcesBody, request: Request = None):
    """Save user-attached priority sources for a theme (session cache)."""
    await require_api_key(request)
    from sources.user_attachments import normalize_user_sources

    rpd_data = _load_rpd_data_for_fingerprint(body.fingerprint)
    sources = normalize_user_sources([s.model_dump() for s in body.sources])
    _set_user_sources_for_theme(rpd_data, body.theme_title, sources)
    _RPD_SESSION_CACHE[body.fingerprint] = rpd_data
    try:
        from core.database import get_db, RPDRequest
        from sqlalchemy import select

        async for db in get_db():
            res = await db.execute(
                select(RPDRequest).where(RPDRequest.request_fingerprint == body.fingerprint)
            )
            row = res.scalar_one_or_none()
            if row:
                row.request_data = rpd_data
                await db.commit()
            break
    except Exception as ex:
        logger.warning("user-sources db persist skipped: %s", ex)
    return {
        "success": True,
        "fingerprint": body.fingerprint,
        "theme_title": body.theme_title,
        "sources": sources,
        "count": len(sources),
    }


@router.post("/generate-package")
async def generate_package(
    body: PackageGenerateRequest,
    model_manager: ModelManager = Depends(get_model_manager),
    request: Request = None,
):
    """Full course package: lecture + optional lab, self-check, PPTX."""
    await require_api_key(request)
    await require_rate_limit(request, "generate_package")
    return await _execute_generate_package(body, model_manager)


@router.post("/generate-package/stream")
async def generate_package_stream(
    body: PackageGenerateRequest,
    model_manager: ModelManager = Depends(get_model_manager),
    request: Request = None,
):
    """SSE stream of generation progress + final JSON result."""
    await require_api_key(request)
    await require_rate_limit(request, "generate_package")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(ev: Dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", **ev})

    async def worker() -> None:
        try:
            result = await _execute_generate_package(body, model_manager, on_progress=on_progress)
            await queue.put({"type": "done", "result": result})
        except Exception as e:
            logger.exception("generate-package stream failed")
            await queue.put({"type": "error", "message": str(e)})
        await queue.put(None)

    asyncio.create_task(worker())

    async def event_generator():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/presentation-preview")
async def get_presentation_preview(
    fingerprint: str,
    theme_title: str,
    request: Request = None,
):
    await require_api_key(request)
    from api.presentation_preview import get_preview_manifest

    manifest = get_preview_manifest(fingerprint, theme_title)
    if not manifest:
        raise HTTPException(status_code=404, detail="Preview not found. Generate package first.")
    return {"success": True, **manifest}


@router.post("/presentation-preview/slide-image")
async def upload_presentation_slide_image(
    fingerprint: str = Query(...),
    theme_title: str = Query(...),
    slide_index: int = Query(...),
    file: UploadFile = File(...),
    request: Request = None,
):
    """Expert upload: one image per slide (multipart field ``file``)."""
    await require_api_key(request)
    from api.presentation_preview import save_user_slide_image
    import tempfile

    suffix = Path(file.filename or "image.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = save_user_slide_image(fingerprint, theme_title, slide_index, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"success": True, **result}


@router.delete("/presentation-preview/slide-image")
async def delete_presentation_slide_image(
    fingerprint: str,
    theme_title: str,
    slide_index: int,
    request: Request = None,
):
    await require_api_key(request)
    from api.presentation_preview import clear_slide_image

    try:
        result = clear_slide_image(fingerprint, theme_title, slide_index)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"success": True, **result}


@router.get("/presentation-preview/image")
async def get_presentation_preview_image(
    fingerprint: str,
    theme_title: str,
    file: str,
    request: Request = None,
):
    await require_api_key(request)
    from api.presentation_preview import resolve_preview_image

    path = resolve_preview_image(fingerprint, theme_title, file)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    media = "image/png" if path.suffix.lower() == ".png" else "application/octet-stream"
    return FileResponse(path, media_type=media)


@router.put("/package-draft")
async def save_package_draft(body: PackageDraftBody, request: Request = None):
    """Persist expert-edited package in server memory (per fingerprint + theme)."""
    await require_api_key(request)
    key = _draft_key(body.fingerprint, body.theme_title)
    payload = {
        "fingerprint": body.fingerprint,
        "theme_title": body.theme_title,
        "lecture_md": body.lecture_md,
        "lab_md": body.lab_md,
        "selfcheck_md": body.selfcheck_md,
        "moodle_questions_xml": body.moodle_questions_xml,
        "presentation_pptx_base64": body.presentation_pptx_base64,
        "presentation_slides_json": body.presentation_slides_json,
        "approved": body.approved,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    _PACKAGE_DRAFTS[key] = payload
    return {"success": True, **payload}


@router.get("/package-draft")
async def get_package_draft(
    fingerprint: str,
    theme_title: str,
    request: Request = None,
):
    await require_api_key(request)
    key = _draft_key(fingerprint, theme_title)
    draft = _PACKAGE_DRAFTS.get(key)
    if not draft:
        return {"success": False, "message": "Draft not found"}
    return {"success": True, **draft}


@router.post("/export-package")
async def export_package(body: PackageExportRequest, request: Request = None):
    """Export edited package artifacts (SCORM zip, PDF, PPTX, presentation PDF)."""
    await require_api_key(request)

    from export.package_export import (
        build_native_pdf_zip_bytes,
        build_presentation_pdf_bytes,
        build_scorm_zip_bytes,
    )
    title = body.theme_title or "Course"

    if body.export_format == "presentation_pdf":
        pdf = build_presentation_pdf_bytes(
            theme_title=title,
            slides_json=body.presentation_slides_json,
            fingerprint=body.fingerprint or "",
        )
        if not pdf:
            raise HTTPException(
                status_code=400,
                detail="Presentation PDF failed (no slides or install xhtml2pdf).",
            )
        return StreamingResponse(
            iter([pdf]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": _attachment_disposition(f"{title}_slides.pdf"),
            },
        )

    if body.export_format == "pptx":
        from presentation.slides_export import slides_to_pptx_bytes

        data = b""
        if (body.presentation_slides_json or "").strip():
            try:
                data = slides_to_pptx_bytes(
                    body.presentation_slides_json,
                    theme_title=title,
                    fingerprint=body.fingerprint or "",
                )
            except Exception as e:
                logger.warning("pptx rebuild from slides_json failed: %s", e)
        if not data and body.presentation_pptx_base64:
            try:
                data = base64.standard_b64decode(body.presentation_pptx_base64)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid pptx base64: {e}") from e
        if not data:
            raise HTTPException(
                status_code=400,
                detail="PPTX export failed: no slides_json and no pptx base64.",
            )
        return StreamingResponse(
            iter([data]),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": _attachment_disposition(f"{title}.pptx")},
        )

    if body.export_format == "scorm":
        data = build_scorm_zip_bytes(
            course_title=title,
            lecture_md=body.lecture_md,
            lab_md=body.lab_md,
            selfcheck_md=body.selfcheck_md,
            questions_xml=body.moodle_questions_xml,
        )
        return StreamingResponse(
            iter([data]),
            media_type="application/zip",
            headers={"Content-Disposition": _attachment_disposition(f"{title}_scorm.zip")},
        )

    data, native = build_native_pdf_zip_bytes(
        course_title=title,
        lecture_md=body.lecture_md,
        lab_md=body.lab_md,
        selfcheck_md=body.selfcheck_md,
    )
    zip_label = "pdf" if native else "pdf_bundle"
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={
            "Content-Disposition": _attachment_disposition(f"{title}_{zip_label}.zip"),
            "X-Pdf-Native": "1" if native else "0",
        },
    )
