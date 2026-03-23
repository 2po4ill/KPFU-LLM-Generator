"""
API routes for RPD processing
"""

import os
import logging
from typing import List, Optional
from pathlib import Path
import tempfile
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from core.model_manager import ModelManager
from rpd.processor import get_rpd_processor, RPDProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpd", tags=["RPD Processing"])


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
                    description=theme.get('description')
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
        
        return RPDProcessingResponse(**result)
        
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
        from generation.generator_v3 import get_optimized_content_generator
        
        # Check if content already exists
        async for db in get_db():
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
            
            logger.info(f"Generating new content for fingerprint {fingerprint}, theme {theme_title}")
            
            if content_type != "lecture":
                return {
                    "success": False,
                    "message": f"Unsupported content_type: {content_type}. Only 'lecture' is implemented.",
                    "fingerprint": fingerprint,
                    "theme_title": theme_title,
                }

            # Load validated RPD request by fingerprint
            rpd_req_res = await db.execute(
                select(RPDRequest).where(RPDRequest.request_fingerprint == fingerprint)
            )
            rpd_req = rpd_req_res.scalar_one_or_none()
            if not rpd_req:
                return {
                    "success": False,
                    "message": "No RPD request found for this fingerprint. Submit RPD first via /submit-data.",
                    "fingerprint": fingerprint,
                    "theme_title": theme_title,
                }

            rpd_data = rpd_req.request_data
            
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
            
            # Get optimized generator v3 (TOC caching + targeted extraction)
            generator = await get_optimized_content_generator(
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
                "created_date": new_content.created_date.isoformat()
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