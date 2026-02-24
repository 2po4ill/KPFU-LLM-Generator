-- KPFU LLM Generator Database Initialization
-- Simplified schema: Only generated content + literature cache

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Generated content table
CREATE TABLE IF NOT EXISTS generated_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_fingerprint VARCHAR(16) NOT NULL,
    request_data JSONB NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    theme_title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB,
    sources_used JSONB,
    generation_time_seconds FLOAT,
    confidence_score FLOAT,
    created_date TIMESTAMP DEFAULT NOW()
);

-- Literature cache table
CREATE TABLE IF NOT EXISTS literature_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    authors VARCHAR(500) NOT NULL,
    title VARCHAR(1000) NOT NULL,
    kpfu_available BOOLEAN DEFAULT FALSE,
    kpfu_book_id VARCHAR(100),
    year INTEGER,
    publisher VARCHAR(500),
    pages_total INTEGER,
    table_of_contents JSONB,
    keyword_index JSONB,
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

-- Indexes for generated_content
CREATE INDEX IF NOT EXISTS idx_fingerprint ON generated_content(request_fingerprint);
CREATE INDEX IF NOT EXISTS idx_content_type ON generated_content(content_type);
CREATE INDEX IF NOT EXISTS idx_theme_title ON generated_content(theme_title);
CREATE INDEX IF NOT EXISTS idx_created_date ON generated_content(created_date);

-- Indexes for literature_cache
CREATE INDEX IF NOT EXISTS idx_lit_title ON literature_cache(title);
CREATE INDEX IF NOT EXISTS idx_lit_authors ON literature_cache(authors);
CREATE INDEX IF NOT EXISTS idx_lit_kpfu_id ON literature_cache(kpfu_book_id);
CREATE INDEX IF NOT EXISTS idx_lit_available ON literature_cache(kpfu_available) WHERE kpfu_available = true;

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_literature_title_gin ON literature_cache USING gin(to_tsvector('russian', title));
CREATE INDEX IF NOT EXISTS idx_literature_authors_gin ON literature_cache USING gin(to_tsvector('russian', authors));

-- Performance settings
SET work_mem = '64MB';
SET maintenance_work_mem = '256MB';
SET effective_cache_size = '1GB';
SET random_page_cost = 1.1;