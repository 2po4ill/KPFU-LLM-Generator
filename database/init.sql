-- KPFU LLM Generator Database Initialization
-- Optimized indexes for performance

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create optimized indexes after table creation
-- These will be created automatically by SQLAlchemy, but we can add additional optimizations

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_rpd_subject_degree ON rpd_documents(subject_title, academic_degree);
CREATE INDEX IF NOT EXISTS idx_rpd_profession_degree ON rpd_documents(profession, academic_degree);

-- Full-text search indexes for literature
CREATE INDEX IF NOT EXISTS idx_literature_title_gin ON literature_references USING gin(to_tsvector('russian', title));
CREATE INDEX IF NOT EXISTS idx_literature_authors_gin ON literature_references USING gin(to_tsvector('russian', authors));

-- Partial indexes for performance
CREATE INDEX IF NOT EXISTS idx_literature_available ON literature_references(kpfu_available) WHERE kpfu_available = true;
CREATE INDEX IF NOT EXISTS idx_content_pending_review ON generated_content(requires_review) WHERE requires_review = true;
CREATE INDEX IF NOT EXISTS idx_content_approved ON generated_content(approved) WHERE approved = true;

-- Cache cleanup index
CREATE INDEX IF NOT EXISTS idx_cache_cleanup ON cache_entries(expires_date) WHERE expires_date < NOW();

-- Performance settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Restart required for some settings, but these can be set immediately
SET work_mem = '64MB';
SET maintenance_work_mem = '256MB';
SET effective_cache_size = '1GB';
SET random_page_cost = 1.1;