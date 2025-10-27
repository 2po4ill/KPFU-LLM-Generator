"""
Tests for RPD data extractor
"""

import pytest
import os
import sys
from unittest.mock import Mock, AsyncMock

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from rpd.extractor import (
    LectureTheme, LabExample, LiteratureReference, RPDData, 
    RPDDataExtractor
)


class TestDataStructures:
    """Test RPD data structures"""
    
    def test_lecture_theme_creation(self):
        """Test LectureTheme creation"""
        theme = LectureTheme(
            title="Введение в программирование",
            order=1,
            hours=2.0,
            description="Основы программирования"
        )
        
        assert theme.title == "Введение в программирование"
        assert theme.order == 1
        assert theme.hours == 2.0
        assert theme.description == "Основы программирования"
    
    def test_lab_example_creation(self):
        """Test LabExample creation"""
        lab = LabExample(
            title="Лабораторная работа 1",
            description="Создание простой программы",
            theme_relation="Введение в программирование",
            estimated_hours=4.0
        )
        
        assert lab.title == "Лабораторная работа 1"
        assert lab.description == "Создание простой программы"
        assert lab.theme_relation == "Введение в программирование"
        assert lab.estimated_hours == 4.0
    
    def test_literature_reference_creation(self):
        """Test LiteratureReference creation"""
        ref = LiteratureReference(
            authors="Иванов И.И., Петров П.П.",
            title="Основы программирования",
            year=2023,
            pages="1-300",
            publisher="Издательство КПФУ",
            kpfu_available=True
        )
        
        assert ref.authors == "Иванов И.И., Петров П.П."
        assert ref.title == "Основы программирования"
        assert ref.year == 2023
        assert ref.pages == "1-300"
        assert ref.publisher == "Издательство КПФУ"
        assert ref.kpfu_available is True
    
    def test_rpd_data_creation(self):
        """Test RPDData creation"""
        rpd = RPDData(
            subject_title="Программирование",
            academic_degree="bachelor",
            profession="Программная инженерия",
            total_hours=144
        )
        
        assert rpd.subject_title == "Программирование"
        assert rpd.academic_degree == "bachelor"
        assert rpd.profession == "Программная инженерия"
        assert rpd.total_hours == 144
        assert rpd.lecture_themes == []
        assert rpd.lab_examples == []
        assert rpd.literature_references == []
        assert rpd.extraction_errors == []
    
    def test_rpd_data_with_content(self):
        """Test RPDData with content"""
        theme = LectureTheme(title="Тема 1", order=1, hours=2.0)
        lab = LabExample(title="Лаб 1", description="Описание")
        ref = LiteratureReference(authors="Автор", title="Книга")
        
        rpd = RPDData(
            subject_title="Тест",
            academic_degree="master",
            profession="Тест",
            total_hours=100,
            lecture_themes=[theme],
            lab_examples=[lab],
            literature_references=[ref]
        )
        
        assert len(rpd.lecture_themes) == 1
        assert len(rpd.lab_examples) == 1
        assert len(rpd.literature_references) == 1


class TestRPDDataExtractor:
    """Test RPD data extractor"""
    
    def test_extractor_initialization(self):
        """Test extractor initialization"""
        extractor = RPDDataExtractor()
        
        assert extractor.model_manager is None
        assert isinstance(extractor.extraction_prompts, dict)
        assert 'basic_info' in extractor.extraction_prompts
        assert 'lecture_themes' in extractor.extraction_prompts
        assert 'lab_examples' in extractor.extraction_prompts
        assert 'literature' in extractor.extraction_prompts
    
    def test_extractor_with_model_manager(self):
        """Test extractor with model manager"""
        mock_model_manager = Mock()
        extractor = RPDDataExtractor(mock_model_manager)
        
        assert extractor.model_manager == mock_model_manager
    
    @pytest.mark.asyncio
    async def test_extract_rpd_data_no_text(self):
        """Test extraction with no text content"""
        extractor = RPDDataExtractor()
        
        parsed_document = {'raw_text': ''}
        
        with pytest.raises(ValueError, match="No text content found"):
            await extractor.extract_rpd_data(parsed_document)
    
    @pytest.mark.asyncio
    async def test_extract_rpd_data_fallback(self):
        """Test extraction using fallback methods"""
        extractor = RPDDataExtractor()
        
        parsed_document = {
            'raw_text': '''
            Рабочая программа дисциплины: "Программирование на Python"
            Направление подготовки: Программная инженерия
            Общая трудоемкость: 144 часа
            Степень: бакалавриат
            
            Тема 1. Введение в Python (2 часа)
            Тема 2. Основы синтаксиса (4 часа)
            
            Лабораторная работа 1. Первая программа
            Лабораторная работа 2. Работа с переменными
            
            Список литературы:
            1. Иванов И.И. Программирование на Python. 2023.
            2. Петров П.П. Основы Python. 2022.
            '''
        }
        
        result = await extractor.extract_rpd_data(parsed_document)
        
        assert isinstance(result, RPDData)
        assert "Программирование на Python" in result.subject_title
        assert result.academic_degree == "bachelor"
        assert "Программная инженерия" in result.profession
        assert result.total_hours == 144
    
    @pytest.mark.asyncio
    async def test_extract_rpd_data_with_mock_llm(self):
        """Test extraction with mock LLM"""
        # Mock model manager and LLM
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = {
            'response': '''
            {
                "subject_title": "Программирование на Python",
                "academic_degree": "bachelor",
                "profession": "Программная инженерия",
                "total_hours": 144,
                "department": "Кафедра ИТ",
                "year": 2023
            }
            '''
        }
        
        mock_model_manager = AsyncMock()
        mock_model_manager.get_llm_model.return_value = mock_llm
        
        extractor = RPDDataExtractor(mock_model_manager)
        
        parsed_document = {
            'raw_text': 'Test RPD content with sufficient text for LLM processing'
        }
        
        result = await extractor.extract_rpd_data(parsed_document)
        
        assert isinstance(result, RPDData)
        assert result.subject_title == "Программирование на Python"
        assert result.academic_degree == "bachelor"
        assert result.profession == "Программная инженерия"
        assert result.total_hours == 144
    
    def test_parse_json_response_valid(self):
        """Test JSON response parsing with valid JSON"""
        extractor = RPDDataExtractor()
        
        json_text = '{"subject_title": "Test", "total_hours": 100}'
        result = extractor._parse_json_response(json_text)
        
        assert result == {"subject_title": "Test", "total_hours": 100}
    
    def test_parse_json_response_with_extra_text(self):
        """Test JSON response parsing with extra text"""
        extractor = RPDDataExtractor()
        
        json_text = 'Here is the result: {"subject_title": "Test", "total_hours": 100} End of response.'
        result = extractor._parse_json_response(json_text)
        
        assert result == {"subject_title": "Test", "total_hours": 100}
    
    def test_parse_json_response_invalid(self):
        """Test JSON response parsing with invalid JSON"""
        extractor = RPDDataExtractor()
        
        json_text = 'This is not JSON'
        result = extractor._parse_json_response(json_text)
        
        assert result is None
    
    def test_extract_basic_info_fallback(self):
        """Test fallback basic info extraction"""
        extractor = RPDDataExtractor()
        
        text = '''
        Рабочая программа дисциплины: "Основы программирования"
        Направление подготовки: Информатика и вычислительная техника
        Общая трудоемкость: 108 часов
        Магистратура
        '''
        
        result = extractor._extract_basic_info_fallback(text)
        
        assert "Основы программирования" in result['subject_title']
        assert result['academic_degree'] == 'master'
        assert "Информатика и вычислительная техника" in result['profession']
        assert result['total_hours'] == 108
    
    def test_extract_lecture_themes_fallback(self):
        """Test fallback lecture themes extraction"""
        extractor = RPDDataExtractor()
        
        text = '''
        Тема 1. Введение в программирование (2 часа)
        Тема 2. Основы синтаксиса Python (4 часа)
        Лекция 3. Структуры данных (3 часа)
        '''
        
        result = extractor._extract_lecture_themes_fallback(text)
        
        assert len(result) >= 2
        assert any("Введение в программирование" in theme['title'] for theme in result)
        assert any("Основы синтаксиса Python" in theme['title'] for theme in result)
    
    def test_extract_lab_examples_fallback(self):
        """Test fallback lab examples extraction"""
        extractor = RPDDataExtractor()
        
        text = '''
        Лабораторная работа 1. Первая программа на Python
        ЛР 2. Работа с переменными и типами данных
        Практическая работа 3. Условные операторы
        '''
        
        result = extractor._extract_lab_examples_fallback(text)
        
        assert len(result) >= 2
        assert any("Первая программа на Python" in lab['title'] for lab in result)
        assert any("Работа с переменными" in lab['title'] for lab in result)
    
    def test_extract_literature_fallback(self):
        """Test fallback literature extraction"""
        extractor = RPDDataExtractor()
        
        text = '''
        Список литературы:
        1. Иванов И.И. Программирование на Python. М.: Издательство, 2023. 300 с.
        2. Петров П.П. Основы алгоритмов. СПб.: Питер, 2022. 250 с.
        3. Сидоров С.С. Структуры данных и алгоритмы. 2021.
        '''
        
        result = extractor._extract_literature_fallback(text)
        
        assert len(result) >= 2
        assert any("Иванов И.И" in ref['authors'] for ref in result)
        assert any("Программирование на Python" in ref['title'] for ref in result)
        assert any(ref.get('year') == 2023 for ref in result)
    
    def test_validate_rpd_data(self):
        """Test RPD data validation"""
        extractor = RPDDataExtractor()
        
        # Create RPD data with some issues
        rpd_data = RPDData(
            subject_title="",  # Empty title
            academic_degree="invalid",  # Invalid degree
            profession="Test Profession",
            total_hours=-10,  # Invalid hours
            lecture_themes=[
                LectureTheme(title="", order=1, hours=0),  # Empty title, zero hours
                LectureTheme(title="Valid Theme", order=2, hours=2.0)
            ]
        )
        
        validated = extractor._validate_rpd_data(rpd_data)
        
        # Check that validation corrected issues
        assert validated.academic_degree == "bachelor"  # Corrected to default
        assert validated.lecture_themes[0].hours == 2.0  # Corrected hours
        assert len(validated.extraction_errors) > 0  # Errors recorded
        assert validated.extraction_confidence < 1.0  # Confidence reduced
    
    def test_to_dict(self):
        """Test converting RPDData to dictionary"""
        extractor = RPDDataExtractor()
        
        theme = LectureTheme(title="Test Theme", order=1, hours=2.0)
        rpd_data = RPDData(
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100,
            lecture_themes=[theme]
        )
        
        result_dict = extractor.to_dict(rpd_data)
        
        assert isinstance(result_dict, dict)
        assert result_dict['subject_title'] == "Test Subject"
        assert result_dict['academic_degree'] == "bachelor"
        assert len(result_dict['lecture_themes']) == 1
        assert result_dict['lecture_themes'][0]['title'] == "Test Theme"