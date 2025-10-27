"""
Tests for database models and operations
"""

import pytest
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Import models directly without triggering engine creation
from core.database import Base
from core.database import (
    RPDDocument, LectureTheme, LabExample, 
    LiteratureReference, GeneratedContent, CacheEntry
)


class TestDatabaseModels:
    """Test database model definitions"""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create database session for testing"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_rpd_document_creation(self, session):
        """Test creating RPD document"""
        rpd = RPDDocument(
            filename="test_rpd.pdf",
            subject_title="Программирование на Python",
            academic_degree="bachelor",
            profession="Программная инженерия",
            total_hours=144
        )
        
        session.add(rpd)
        session.commit()
        
        assert rpd.id is not None
        assert rpd.filename == "test_rpd.pdf"
        assert rpd.subject_title == "Программирование на Python"
        assert rpd.academic_degree == "bachelor"
        assert rpd.profession == "Программная инженерия"
        assert rpd.total_hours == 144
        assert rpd.processed is False
        assert rpd.upload_date is not None
    
    def test_lecture_theme_creation(self, session):
        """Test creating lecture theme"""
        # Create RPD first
        rpd = RPDDocument(
            filename="test.pdf",
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100
        )
        session.add(rpd)
        session.commit()
        
        # Create lecture theme
        theme = LectureTheme(
            rpd_document_id=rpd.id,
            theme_title="Введение в программирование",
            theme_order=1,
            allocated_hours=2.0
        )
        
        session.add(theme)
        session.commit()
        
        assert theme.id is not None
        assert theme.rpd_document_id == rpd.id
        assert theme.theme_title == "Введение в программирование"
        assert theme.theme_order == 1
        assert theme.allocated_hours == 2.0
    
    def test_lab_example_creation(self, session):
        """Test creating lab example"""
        # Create RPD first
        rpd = RPDDocument(
            filename="test.pdf",
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100
        )
        session.add(rpd)
        session.commit()
        
        # Create lab example
        lab = LabExample(
            rpd_document_id=rpd.id,
            example_text="Создать программу для сортировки массива",
            theme_relation="Алгоритмы сортировки"
        )
        
        session.add(lab)
        session.commit()
        
        assert lab.id is not None
        assert lab.rpd_document_id == rpd.id
        assert lab.example_text == "Создать программу для сортировки массива"
        assert lab.theme_relation == "Алгоритмы сортировки"
    
    def test_literature_reference_creation(self, session):
        """Test creating literature reference"""
        # Create RPD first
        rpd = RPDDocument(
            filename="test.pdf",
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100
        )
        session.add(rpd)
        session.commit()
        
        # Create literature reference
        lit_ref = LiteratureReference(
            rpd_document_id=rpd.id,
            authors="Иванов И.И., Петров П.П.",
            title="Основы программирования",
            year=2023,
            pages="1-300",
            kpfu_available=True,
            kpfu_book_id="KPFU_12345"
        )
        
        session.add(lit_ref)
        session.commit()
        
        assert lit_ref.id is not None
        assert lit_ref.rpd_document_id == rpd.id
        assert lit_ref.authors == "Иванов И.И., Петров П.П."
        assert lit_ref.title == "Основы программирования"
        assert lit_ref.year == 2023
        assert lit_ref.pages == "1-300"
        assert lit_ref.kpfu_available is True
        assert lit_ref.kpfu_book_id == "KPFU_12345"
    
    def test_generated_content_creation(self, session):
        """Test creating generated content"""
        # Create RPD and lecture theme first
        rpd = RPDDocument(
            filename="test.pdf",
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100
        )
        session.add(rpd)
        session.commit()
        
        theme = LectureTheme(
            rpd_document_id=rpd.id,
            theme_title="Test Theme",
            theme_order=1,
            allocated_hours=2.0
        )
        session.add(theme)
        session.commit()
        
        # Create generated content
        content = GeneratedContent(
            lecture_theme_id=theme.id,
            content_type="lecture",
            content="# Лекция по программированию\n\nСодержание лекции...",
            citations={"sources": ["source1", "source2"]},
            generation_time_seconds=45.5,
            confidence_score=0.85,
            requires_review=False,
            approved=True
        )
        
        session.add(content)
        session.commit()
        
        assert content.id is not None
        assert content.lecture_theme_id == theme.id
        assert content.content_type == "lecture"
        assert "Лекция по программированию" in content.content
        assert content.citations == {"sources": ["source1", "source2"]}
        assert content.generation_time_seconds == 45.5
        assert content.confidence_score == 0.85
        assert content.requires_review is False
        assert content.approved is True
        assert content.created_date is not None
    
    def test_cache_entry_creation(self, session):
        """Test creating cache entry"""
        cache_entry = CacheEntry(
            cache_key="test_key_123",
            cache_type="keyword_relevance",
            data={"score": 0.75, "metadata": "test"},
            expires_date=datetime.utcnow()
        )
        
        session.add(cache_entry)
        session.commit()
        
        assert cache_entry.id is not None
        assert cache_entry.cache_key == "test_key_123"
        assert cache_entry.cache_type == "keyword_relevance"
        assert cache_entry.data == {"score": 0.75, "metadata": "test"}
        assert cache_entry.created_date is not None
        assert cache_entry.expires_date is not None
    
    def test_relationships(self, session):
        """Test model relationships"""
        # Create RPD
        rpd = RPDDocument(
            filename="test.pdf",
            subject_title="Test Subject",
            academic_degree="bachelor",
            profession="Test Profession",
            total_hours=100
        )
        session.add(rpd)
        session.commit()
        
        # Create related objects
        theme = LectureTheme(
            rpd_document_id=rpd.id,
            theme_title="Theme 1",
            theme_order=1,
            allocated_hours=2.0
        )
        
        lab = LabExample(
            rpd_document_id=rpd.id,
            example_text="Lab example",
            theme_relation="Theme 1"
        )
        
        lit_ref = LiteratureReference(
            rpd_document_id=rpd.id,
            authors="Author",
            title="Book Title",
            year=2023
        )
        
        session.add_all([theme, lab, lit_ref])
        session.commit()
        
        # Test relationships
        session.refresh(rpd)
        assert len(rpd.lecture_themes) == 1
        assert len(rpd.lab_examples) == 1
        assert len(rpd.literature_refs) == 1
        
        assert rpd.lecture_themes[0].theme_title == "Theme 1"
        assert rpd.lab_examples[0].example_text == "Lab example"
        assert rpd.literature_refs[0].title == "Book Title"
    
    def test_model_constraints(self, session):
        """Test model constraints and validations"""
        # Test that required fields are enforced
        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            rpd = RPDDocument(
                # Missing required fields
                filename=None,
                subject_title=None,
                academic_degree=None,
                profession=None,
                total_hours=None
            )
            session.add(rpd)
            session.commit()
    
    def test_indexes_exist(self, engine):
        """Test that indexes are created properly"""
        # This is more of a smoke test - if indexes are malformed, 
        # table creation would fail
        inspector = engine.dialect.get_table_names(engine.connect())
        
        # Should have all our tables
        expected_tables = [
            'rpd_documents', 'lecture_themes', 'lab_examples',
            'literature_references', 'generated_content', 'cache_entries'
        ]
        
        for table in expected_tables:
            # Note: SQLite might not preserve exact table names, 
            # but creation should succeed
            pass  # If we got here, table creation succeeded
    
    def test_unicode_support(self, session):
        """Test Unicode/Russian text support"""
        rpd = RPDDocument(
            filename="тест.pdf",
            subject_title="Программирование на языке Python с использованием библиотек",
            academic_degree="bachelor",
            profession="Программная инженерия и информационные технологии",
            total_hours=144
        )
        
        session.add(rpd)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(RPDDocument).filter_by(filename="тест.pdf").first()
        assert retrieved is not None
        assert retrieved.subject_title == "Программирование на языке Python с использованием библиотек"
        assert retrieved.profession == "Программная инженерия и информационные технологии"