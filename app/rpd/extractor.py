"""
LLM-based structured data extraction from RPD documents
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LectureTheme:
    """Lecture theme data structure"""
    title: str
    order: int
    hours: float
    description: Optional[str] = None


@dataclass
class LabExample:
    """Laboratory work example data structure"""
    title: str
    description: str
    theme_relation: Optional[str] = None
    estimated_hours: Optional[float] = None


@dataclass
class LiteratureReference:
    """Literature reference data structure"""
    authors: str
    title: str
    year: Optional[int] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    kpfu_available: bool = False
    kpfu_book_id: Optional[str] = None


@dataclass
class RPDData:
    """Complete RPD data structure"""
    # Basic information
    subject_title: str
    academic_degree: str  # bachelor, master, phd
    profession: str
    total_hours: int
    
    # Optional metadata
    department: Optional[str] = None
    faculty: Optional[str] = None
    year: Optional[int] = None
    semester: Optional[str] = None
    
    # Content
    lecture_themes: List[LectureTheme] = None
    lab_examples: List[LabExample] = None
    literature_references: List[LiteratureReference] = None
    
    # Processing metadata
    extraction_confidence: Optional[float] = None
    extraction_errors: List[str] = None
    
    def __post_init__(self):
        if self.lecture_themes is None:
            self.lecture_themes = []
        if self.lab_examples is None:
            self.lab_examples = []
        if self.literature_references is None:
            self.literature_references = []
        if self.extraction_errors is None:
            self.extraction_errors = []


class RPDDataExtractor:
    """Extracts structured data from RPD documents using LLM"""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager
        self.extraction_prompts = self._load_extraction_prompts()
    
    def _load_extraction_prompts(self) -> Dict[str, str]:
        """Load prompt templates for data extraction"""
        return {
            'basic_info': """
Извлеки основную информацию из РПД документа. Верни результат в JSON формате:

{
    "subject_title": "название дисциплины",
    "academic_degree": "bachelor/master/phd",
    "profession": "направление подготовки",
    "total_hours": число_часов,
    "department": "кафедра (если указана)",
    "faculty": "факультет (если указан)",
    "year": год_составления,
    "semester": "семестр (если указан)"
}

Текст РПД:
{text}

JSON:""",
            
            'lecture_themes': """
Извлеки темы лекций из РПД документа. Верни результат в JSON формате:

{
    "lecture_themes": [
        {
            "title": "название темы",
            "order": порядковый_номер,
            "hours": количество_часов,
            "description": "описание (если есть)"
        }
    ]
}

Текст РПД:
{text}

JSON:""",
            
            'lab_examples': """
Извлеки примеры лабораторных работ из РПД документа. Верни результат в JSON формате:

{
    "lab_examples": [
        {
            "title": "название лабораторной работы",
            "description": "описание работы",
            "theme_relation": "связанная тема лекции (если указана)",
            "estimated_hours": количество_часов
        }
    ]
}

Текст РПД:
{text}

JSON:""",
            
            'literature': """
Извлеки список литературы из РПД документа. Верни результат в JSON формате:

{
    "literature_references": [
        {
            "authors": "авторы",
            "title": "название книги/статьи",
            "year": год_издания,
            "pages": "страницы (если указаны)",
            "publisher": "издательство (если указано)",
            "isbn": "ISBN (если указан)"
        }
    ]
}

Текст РПД:
{text}

JSON:"""
        }
    
    async def extract_rpd_data(self, parsed_document: Dict[str, Any]) -> RPDData:
        """
        Extract structured RPD data from parsed document
        
        Args:
            parsed_document: Output from RPD parser
            
        Returns:
            RPDData object with extracted information
        """
        raw_text = parsed_document.get('raw_text', '')
        
        if not raw_text.strip():
            raise ValueError("No text content found in document")
        
        # Initialize result with defaults
        rpd_data = RPDData(
            subject_title="",
            academic_degree="bachelor",
            profession="",
            total_hours=0
        )
        
        try:
            # Extract basic information
            basic_info = await self._extract_basic_info(raw_text)
            if basic_info:
                rpd_data.subject_title = basic_info.get('subject_title', '')
                rpd_data.academic_degree = basic_info.get('academic_degree', 'bachelor')
                rpd_data.profession = basic_info.get('profession', '')
                rpd_data.total_hours = basic_info.get('total_hours', 0)
                rpd_data.department = basic_info.get('department')
                rpd_data.faculty = basic_info.get('faculty')
                rpd_data.year = basic_info.get('year')
                rpd_data.semester = basic_info.get('semester')
            
            # Extract lecture themes
            lecture_themes = await self._extract_lecture_themes(raw_text)
            if lecture_themes:
                rpd_data.lecture_themes = [
                    LectureTheme(**theme) for theme in lecture_themes
                ]
            
            # Extract lab examples
            lab_examples = await self._extract_lab_examples(raw_text)
            if lab_examples:
                rpd_data.lab_examples = [
                    LabExample(**lab) for lab in lab_examples
                ]
            
            # Extract literature references
            literature_refs = await self._extract_literature(raw_text)
            if literature_refs:
                rpd_data.literature_references = [
                    LiteratureReference(**ref) for ref in literature_refs
                ]
            
            # Validate extracted data
            rpd_data = self._validate_rpd_data(rpd_data)
            
        except Exception as e:
            logger.error(f"Error extracting RPD data: {e}")
            rpd_data.extraction_errors.append(str(e))
        
        return rpd_data
    
    async def _extract_basic_info(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract basic RPD information"""
        try:
            if self.model_manager:
                # Use LLM for extraction
                llm_model = await self.model_manager.get_llm_model()
                prompt = self.extraction_prompts['basic_info'].format(text=text[:3000])
                
                response = await llm_model.generate(
                    model="llama3.1:8b",
                    prompt=prompt,
                    options={
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                )
                
                json_text = response.get('response', '').strip()
                return self._parse_json_response(json_text)
            else:
                # Fallback to rule-based extraction
                return self._extract_basic_info_fallback(text)
                
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
            return self._extract_basic_info_fallback(text)
    
    async def _extract_lecture_themes(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract lecture themes"""
        try:
            if self.model_manager:
                # Use LLM for extraction
                llm_model = await self.model_manager.get_llm_model()
                prompt = self.extraction_prompts['lecture_themes'].format(text=text[:4000])
                
                response = await llm_model.generate(
                    model="llama3.1:8b",
                    prompt=prompt,
                    options={
                        "temperature": 0.1,
                        "num_predict": 1000
                    }
                )
                
                json_text = response.get('response', '').strip()
                result = self._parse_json_response(json_text)
                return result.get('lecture_themes', []) if result else []
            else:
                # Fallback to rule-based extraction
                return self._extract_lecture_themes_fallback(text)
                
        except Exception as e:
            logger.error(f"Error extracting lecture themes: {e}")
            return self._extract_lecture_themes_fallback(text)
    
    async def _extract_lab_examples(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract lab examples"""
        try:
            if self.model_manager:
                # Use LLM for extraction
                llm_model = await self.model_manager.get_llm_model()
                prompt = self.extraction_prompts['lab_examples'].format(text=text[:4000])
                
                response = await llm_model.generate(
                    model="llama3.1:8b",
                    prompt=prompt,
                    options={
                        "temperature": 0.1,
                        "num_predict": 1000
                    }
                )
                
                json_text = response.get('response', '').strip()
                result = self._parse_json_response(json_text)
                return result.get('lab_examples', []) if result else []
            else:
                # Fallback to rule-based extraction
                return self._extract_lab_examples_fallback(text)
                
        except Exception as e:
            logger.error(f"Error extracting lab examples: {e}")
            return self._extract_lab_examples_fallback(text)
    
    async def _extract_literature(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract literature references"""
        try:
            if self.model_manager:
                # Use LLM for extraction
                llm_model = await self.model_manager.get_llm_model()
                prompt = self.extraction_prompts['literature'].format(text=text[:4000])
                
                response = await llm_model.generate(
                    model="llama3.1:8b",
                    prompt=prompt,
                    options={
                        "temperature": 0.1,
                        "num_predict": 1500
                    }
                )
                
                json_text = response.get('response', '').strip()
                result = self._parse_json_response(json_text)
                return result.get('literature_references', []) if result else []
            else:
                # Fallback to rule-based extraction
                return self._extract_literature_fallback(text)
                
        except Exception as e:
            logger.error(f"Error extracting literature: {e}")
            return self._extract_literature_fallback(text)
    
    def _parse_json_response(self, json_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from LLM"""
        try:
            # Clean up the response
            json_text = json_text.strip()
            
            # Find JSON content between braces
            start_idx = json_text.find('{')
            end_idx = json_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_text = json_text[start_idx:end_idx + 1]
                return json.loads(json_text)
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
    
    def _extract_basic_info_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback rule-based extraction for basic info"""
        result = {
            'subject_title': '',
            'academic_degree': 'bachelor',
            'profession': '',
            'total_hours': 0
        }
        
        # Extract subject title (look for common patterns)
        title_patterns = [
            r'дисциплин[аы]?\s*[:\-]?\s*[«"]?([^«»"\n]+)[«"]?',
            r'предмет\s*[:\-]?\s*[«"]?([^«»"\n]+)[«"]?',
            r'курс\s*[:\-]?\s*[«"]?([^«»"\n]+)[«"]?'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['subject_title'] = match.group(1).strip()
                break
        
        # Extract academic degree
        if any(word in text.lower() for word in ['магистр', 'master']):
            result['academic_degree'] = 'master'
        elif any(word in text.lower() for word in ['аспирант', 'phd', 'докторант']):
            result['academic_degree'] = 'phd'
        
        # Extract profession/direction
        profession_patterns = [
            r'направлени[ею]\s+подготовки\s*[:\-]?\s*([^\n]+)',
            r'специальность\s*[:\-]?\s*([^\n]+)',
            r'профиль\s*[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in profession_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['profession'] = match.group(1).strip()
                break
        
        # Extract total hours
        hours_patterns = [
            r'общ[ая]я\s+трудоемкость\s*[:\-]?\s*(\d+)\s*час',
            r'всего\s+часов\s*[:\-]?\s*(\d+)',
            r'(\d+)\s*час[ао]в?\s+всего'
        ]
        
        for pattern in hours_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['total_hours'] = int(match.group(1))
                break
        
        return result
    
    def _extract_lecture_themes_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback rule-based extraction for lecture themes"""
        themes = []
        
        # Look for lecture sections
        lecture_patterns = [
            r'тема\s+(\d+)\.?\s*([^\n]+)',
            r'лекция\s+(\d+)\.?\s*([^\n]+)',
            r'(\d+)\.?\s*([^\n]+?)\s*\((\d+)\s*час'
        ]
        
        for pattern in lecture_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    order = int(match.group(1))
                    title = match.group(2).strip()
                    hours = 2.0  # Default hours
                    
                    if len(match.groups()) >= 3:
                        try:
                            hours = float(match.group(3))
                        except ValueError:
                            pass
                    
                    themes.append({
                        'title': title,
                        'order': order,
                        'hours': hours
                    })
        
        return themes
    
    def _extract_lab_examples_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback rule-based extraction for lab examples"""
        labs = []
        
        # Look for lab work sections
        lab_patterns = [
            r'лабораторн[ая]я\s+работа\s+(\d+)\.?\s*([^\n]+)',
            r'лр\s+(\d+)\.?\s*([^\n]+)',
            r'практическ[ая]я\s+работа\s+(\d+)\.?\s*([^\n]+)'
        ]
        
        for pattern in lab_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                title = match.group(2).strip()
                
                labs.append({
                    'title': title,
                    'description': title,  # Use title as description for now
                    'estimated_hours': 2.0  # Default hours
                })
        
        return labs
    
    def _extract_literature_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback rule-based extraction for literature"""
        references = []
        
        # Look for literature section
        lit_section_match = re.search(
            r'(список\s+литературы|библиография|литература)\s*:?\s*(.*?)(?=\n\s*\n|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if lit_section_match:
            lit_text = lit_section_match.group(2)
            
            # Split by lines and parse each reference
            lines = lit_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 20:  # Minimum length for a reference
                    # Try to extract author and title
                    ref_match = re.match(r'(\d+\.?\s*)?([^\.]+)\.?\s*([^/]+)', line)
                    if ref_match:
                        author_title = ref_match.group(2).strip()
                        rest = ref_match.group(3).strip() if ref_match.group(3) else ''
                        
                        # Try to separate author and title
                        if '.' in author_title:
                            parts = author_title.split('.', 1)
                            authors = parts[0].strip()
                            title = parts[1].strip() if len(parts) > 1 else author_title
                        else:
                            authors = author_title
                            title = rest
                        
                        # Extract year
                        year_match = re.search(r'(\d{4})', line)
                        year = int(year_match.group(1)) if year_match else None
                        
                        references.append({
                            'authors': authors,
                            'title': title,
                            'year': year
                        })
        
        return references
    
    def _validate_rpd_data(self, rpd_data: RPDData) -> RPDData:
        """Validate and clean extracted RPD data"""
        errors = []
        
        # Validate required fields
        if not rpd_data.subject_title.strip():
            errors.append("Subject title is required")
        
        if not rpd_data.profession.strip():
            errors.append("Profession/direction is required")
        
        if rpd_data.total_hours <= 0:
            errors.append("Total hours must be positive")
        
        # Validate academic degree
        valid_degrees = ['bachelor', 'master', 'phd']
        if rpd_data.academic_degree not in valid_degrees:
            rpd_data.academic_degree = 'bachelor'
            errors.append(f"Invalid academic degree, defaulted to 'bachelor'")
        
        # Validate lecture themes
        for i, theme in enumerate(rpd_data.lecture_themes):
            if not theme.title.strip():
                errors.append(f"Lecture theme {i+1} has empty title")
            if theme.hours <= 0:
                theme.hours = 2.0  # Default hours
                errors.append(f"Lecture theme {i+1} hours corrected to 2.0")
        
        # Calculate confidence score
        confidence = 1.0
        if errors:
            confidence = max(0.1, 1.0 - (len(errors) * 0.1))
        
        rpd_data.extraction_confidence = confidence
        rpd_data.extraction_errors.extend(errors)
        
        return rpd_data
    
    def to_dict(self, rpd_data: RPDData) -> Dict[str, Any]:
        """Convert RPDData to dictionary"""
        return asdict(rpd_data)