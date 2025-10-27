"""
API routes for RPD processing
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

from core.model_manager import ModelManager
from rpd.processor import get_rpd_processor, RPDProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rpd", tags=["RPD Processing"])


class RPDProcessingResponse(BaseModel):
    """Response model for RPD processing"""
    success: bool
    file_path: str
    processing_time_seconds: float
    extracted_data: Optional[dict] = None
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