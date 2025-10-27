"""
Main RPD processing system that combines parsing and extraction
"""

import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from .parsers import parse_rpd_document, RPDParsingError
from .extractor import RPDDataExtractor, RPDData

logger = logging.getLogger(__name__)


class RPDProcessingError(Exception):
    """Custom exception for RPD processing errors"""
    pass


class RPDProcessor:
    """Main RPD processing system"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.extractor = RPDDataExtractor(model_manager)
    
    async def process_rpd_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process RPD file from parsing to structured data extraction
        
        Args:
            file_path: Path to the RPD document
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        processing_start = datetime.now()
        
        result = {
            'file_path': str(file_path),
            'processing_start': processing_start.isoformat(),
            'success': False,
            'errors': [],
            'warnings': [],
            'parsed_data': None,
            'extracted_data': None,
            'processing_time_seconds': 0
        }
        
        try:
            # Step 1: Parse the document
            logger.info(f"Parsing RPD document: {file_path}")
            parsed_data = parse_rpd_document(file_path)
            result['parsed_data'] = parsed_data
            
            # Step 2: Extract structured data
            logger.info("Extracting structured data from RPD")
            rpd_data = await self.extractor.extract_rpd_data(parsed_data)
            result['extracted_data'] = self.extractor.to_dict(rpd_data)
            
            # Step 3: Validate completeness
            validation_result = self._validate_completeness(rpd_data)
            result['warnings'].extend(validation_result['warnings'])
            
            # Calculate processing time
            processing_end = datetime.now()
            result['processing_time_seconds'] = (processing_end - processing_start).total_seconds()
            result['processing_end'] = processing_end.isoformat()
            
            result['success'] = True
            logger.info(f"RPD processing completed successfully in {result['processing_time_seconds']:.2f} seconds")
            
        except RPDParsingError as e:
            error_msg = f"RPD parsing failed: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            
        except Exception as e:
            error_msg = f"RPD processing failed: {e}"
            logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)
        
        finally:
            # Always calculate processing time
            if 'processing_end' not in result:
                processing_end = datetime.now()
                result['processing_time_seconds'] = (processing_end - processing_start).total_seconds()
                result['processing_end'] = processing_end.isoformat()
        
        return result
    
    def _validate_completeness(self, rpd_data: RPDData) -> Dict[str, Any]:
        """
        Validate completeness of extracted RPD data
        
        Args:
            rpd_data: Extracted RPD data
            
        Returns:
            Validation result with warnings
        """
        warnings = []
        
        # Check basic information completeness
        if not rpd_data.subject_title:
            warnings.append("Subject title not found")
        
        if not rpd_data.profession:
            warnings.append("Profession/direction not found")
        
        if rpd_data.total_hours <= 0:
            warnings.append("Total hours not found or invalid")
        
        # Check content completeness
        if not rpd_data.lecture_themes:
            warnings.append("No lecture themes found")
        elif len(rpd_data.lecture_themes) < 3:
            warnings.append(f"Only {len(rpd_data.lecture_themes)} lecture themes found (expected 3+)")
        
        if not rpd_data.literature_references:
            warnings.append("No literature references found")
        elif len(rpd_data.literature_references) < 3:
            warnings.append(f"Only {len(rpd_data.literature_references)} literature references found (expected 3+)")
        
        # Check data quality
        if rpd_data.extraction_confidence and rpd_data.extraction_confidence < 0.7:
            warnings.append(f"Low extraction confidence: {rpd_data.extraction_confidence:.2f}")
        
        if rpd_data.extraction_errors:
            warnings.extend([f"Extraction error: {error}" for error in rpd_data.extraction_errors])
        
        return {
            'warnings': warnings,
            'completeness_score': self._calculate_completeness_score(rpd_data)
        }
    
    def _calculate_completeness_score(self, rpd_data: RPDData) -> float:
        """
        Calculate completeness score (0.0 to 1.0)
        
        Args:
            rpd_data: Extracted RPD data
            
        Returns:
            Completeness score
        """
        score = 0.0
        max_score = 10.0
        
        # Basic information (4 points)
        if rpd_data.subject_title:
            score += 1.0
        if rpd_data.profession:
            score += 1.0
        if rpd_data.total_hours > 0:
            score += 1.0
        if rpd_data.academic_degree in ['bachelor', 'master', 'phd']:
            score += 1.0
        
        # Lecture themes (3 points)
        if rpd_data.lecture_themes:
            score += min(3.0, len(rpd_data.lecture_themes) / 5.0 * 3.0)
        
        # Literature references (2 points)
        if rpd_data.literature_references:
            score += min(2.0, len(rpd_data.literature_references) / 5.0 * 2.0)
        
        # Lab examples (1 point)
        if rpd_data.lab_examples:
            score += min(1.0, len(rpd_data.lab_examples) / 3.0 * 1.0)
        
        return min(1.0, score / max_score)
    
    async def process_multiple_rpd_files(self, file_paths: List[Union[str, Path]]) -> List[Dict[str, Any]]:
        """
        Process multiple RPD files
        
        Args:
            file_paths: List of paths to RPD documents
            
        Returns:
            List of processing results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = await self.process_rpd_file(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results.append({
                    'file_path': str(file_path),
                    'success': False,
                    'errors': [str(e)],
                    'processing_time_seconds': 0
                })
        
        return results
    
    def get_processing_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary of processing results
        
        Args:
            results: List of processing results
            
        Returns:
            Processing summary
        """
        total_files = len(results)
        successful_files = sum(1 for r in results if r['success'])
        failed_files = total_files - successful_files
        
        total_time = sum(r.get('processing_time_seconds', 0) for r in results)
        avg_time = total_time / total_files if total_files > 0 else 0
        
        return {
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'success_rate': successful_files / total_files if total_files > 0 else 0,
            'total_processing_time_seconds': total_time,
            'average_processing_time_seconds': avg_time,
            'errors': [error for r in results for error in r.get('errors', [])],
            'warnings': [warning for r in results for warning in r.get('warnings', [])]
        }


# Global processor instance
rpd_processor = None


def get_rpd_processor(model_manager=None) -> RPDProcessor:
    """Get global RPD processor instance"""
    global rpd_processor
    if rpd_processor is None:
        rpd_processor = RPDProcessor(model_manager)
    return rpd_processor