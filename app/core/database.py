"""
Database configuration and models for KPFU LLM Generator
"""

import asyncio
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    ForeignKey, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from core.config import settings

# Database engine and session (initialized later)
engine = None
AsyncSessionLocal = None

def init_database_engine():
    """Initialize database engine and session factory"""
    global engine, AsyncSessionLocal
    
    if engine is None:
        engine = create_async_engine(
            settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

Base = declarative_base()


class RPDDocument(Base):
    """RPD document metadata"""
    __tablename__ = "rpd_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    subject_title = Column(String(500), nullable=False)
    academic_degree = Column(String(50), nullable=False)  # bachelor, master, phd
    profession = Column(String(200), nullable=False)
    total_hours = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    
    # Relationships
    lecture_themes = relationship("LectureTheme", back_populates="rpd_document")
    lab_examples = relationship("LabExample", back_populates="rpd_document")
    literature_refs = relationship("LiteratureReference", back_populates="rpd_document")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_rpd_subject', 'subject_title'),
        Index('idx_rpd_degree', 'academic_degree'),
        Index('idx_rpd_profession', 'profession'),
    )


class LectureTheme(Base):
    """Lecture themes from RPD"""
    __tablename__ = "lecture_themes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rpd_document_id = Column(UUID(as_uuid=True), ForeignKey("rpd_documents.id"))
    theme_title = Column(String(500), nullable=False)
    theme_order = Column(Integer, nullable=False)
    allocated_hours = Column(Float, nullable=False)
    
    # Relationships
    rpd_document = relationship("RPDDocument", back_populates="lecture_themes")
    generated_content = relationship("GeneratedContent", back_populates="lecture_theme")


class LabExample(Base):
    """Lab work examples from RPD"""
    __tablename__ = "lab_examples"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rpd_document_id = Column(UUID(as_uuid=True), ForeignKey("rpd_documents.id"))
    example_text = Column(Text, nullable=False)
    theme_relation = Column(String(500))  # Related lecture theme
    
    # Relationships
    rpd_document = relationship("RPDDocument", back_populates="lab_examples")


class LiteratureReference(Base):
    """Literature references from RPD"""
    __tablename__ = "literature_references"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rpd_document_id = Column(UUID(as_uuid=True), ForeignKey("rpd_documents.id"))
    authors = Column(String(500), nullable=False)
    title = Column(String(1000), nullable=False)
    year = Column(Integer)
    pages = Column(String(50))
    kpfu_available = Column(Boolean, default=False)
    kpfu_book_id = Column(String(100))  # ID in KPFU library system
    
    # Relationships
    rpd_document = relationship("RPDDocument", back_populates="literature_refs")
    
    # Indexes
    __table_args__ = (
        Index('idx_lit_title', 'title'),
        Index('idx_lit_authors', 'authors'),
        Index('idx_lit_kpfu_available', 'kpfu_available'),
    )


class GeneratedContent(Base):
    """Generated lecture and lab content"""
    __tablename__ = "generated_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lecture_theme_id = Column(UUID(as_uuid=True), ForeignKey("lecture_themes.id"))
    content_type = Column(String(50), nullable=False)  # lecture, lab
    content = Column(Text, nullable=False)
    citations = Column(JSONB)  # JSON array of citations
    generation_time_seconds = Column(Float)
    confidence_score = Column(Float)
    requires_review = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lecture_theme = relationship("LectureTheme", back_populates="generated_content")
    
    # Indexes
    __table_args__ = (
        Index('idx_content_type', 'content_type'),
        Index('idx_content_approved', 'approved'),
        Index('idx_content_review', 'requires_review'),
    )


class CacheEntry(Base):
    """Cache entries for performance optimization"""
    __tablename__ = "cache_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(255), unique=True, nullable=False)
    cache_type = Column(String(50), nullable=False)  # keyword, page_selection, model_output, fgos_template
    data = Column(JSONB, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    expires_date = Column(DateTime, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_cache_type', 'cache_type'),
        Index('idx_cache_expires', 'expires_date'),
    )


async def init_db():
    """Initialize database tables"""
    init_database_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get database session"""
    if AsyncSessionLocal is None:
        init_database_engine()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()