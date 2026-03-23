"""
Database configuration and models for KPFU LLM Generator
Simplified schema: Only store generated content with request fingerprint
"""

import asyncio
from datetime import datetime
from typing import Optional, List
import hashlib
import json

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
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


def generate_request_fingerprint(rpd_data: dict) -> str:
    """
    Generate a unique fingerprint for RPD input request
    This allows tracking what content was generated from which input
    """
    # Create a stable string representation of the request
    fingerprint_data = {
        'subject': rpd_data.get('subject_title', ''),
        'degree': rpd_data.get('academic_degree', ''),
        'profession': rpd_data.get('profession', ''),
        'themes': [t.get('title', '') for t in rpd_data.get('lecture_themes', [])],
        'literature': [f"{r.get('authors', '')}:{r.get('title', '')}" 
                      for r in rpd_data.get('literature_references', [])]
    }
    
    # Create hash
    fingerprint_str = json.dumps(fingerprint_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()[:16]


class GeneratedContent(Base):
    """
    Simplified: Store only generated content with request fingerprint
    The fingerprint allows users to retrieve previously generated content
    """
    __tablename__ = "generated_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request fingerprint for retrieval
    request_fingerprint = Column(String(16), nullable=False, index=True)
    
    # Original request data (for including in download)
    request_data = Column(JSONB, nullable=False)
    
    # Generated content
    content_type = Column(String(50), nullable=False)  # lecture, lab
    theme_title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    citations = Column(JSONB)  # JSON array of citations
    sources_used = Column(JSONB)  # Books/pages used
    generation_time_seconds = Column(Float)
    confidence_score = Column(Float)
    
    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_fingerprint', 'request_fingerprint'),
        Index('idx_content_type', 'content_type'),
        Index('idx_theme_title', 'theme_title'),
        Index('idx_created_date', 'created_date'),
    )


class RPDRequest(Base):
    """
    Store submitted RPD input (structured JSON) by request fingerprint.

    This lets `/generate-content` use the exact same validated RPD input
    that was previously submitted via `/submit-data`.
    """
    __tablename__ = "rpd_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    request_fingerprint = Column(String(16), nullable=False, unique=True, index=True)
    request_data = Column(JSONB, nullable=False)

    created_date = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_rpd_request_fingerprint", "request_fingerprint"),
    )


class LiteratureCache(Base):
    """
    Cache for KPFU library lookups and book content
    Separate from Redis for persistent literature data
    """
    __tablename__ = "literature_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Literature identification
    authors = Column(String(500), nullable=False)
    title = Column(String(1000), nullable=False)
    
    # KPFU library data
    kpfu_available = Column(Boolean, default=False)
    kpfu_book_id = Column(String(100))
    
    # Cached metadata
    year = Column(Integer)
    publisher = Column(String(500))
    pages_total = Column(Integer)
    
    # Content cache (for frequently used books)
    table_of_contents = Column(JSONB)  # Pre-indexed TOC
    keyword_index = Column(JSONB)  # Pre-computed keyword mappings
    
    # Cache metadata
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    # Indexes
    __table_args__ = (
        Index('idx_lit_title', 'title'),
        Index('idx_lit_authors', 'authors'),
        Index('idx_lit_kpfu_id', 'kpfu_book_id'),
        Index('idx_lit_available', 'kpfu_available'),
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