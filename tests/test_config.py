"""
Tests for configuration module
"""

import pytest
import os
import sys

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core.config import Settings


class TestConfig:
    """Test configuration settings"""
    
    def test_default_settings(self):
        """Test default configuration values"""
        settings = Settings()
        
        assert settings.llm_model == "llama3.1:8b"
        assert settings.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"
        assert settings.max_llm_memory == 4700
        assert settings.max_embedding_memory == 118
        assert settings.cache_ttl_seconds == 3600
        assert settings.max_concurrent_requests == 10
    
    def test_environment_override(self):
        """Test that environment variables override defaults"""
        # Set environment variable
        os.environ["LLM_MODEL"] = "test-model"
        os.environ["MAX_LLM_MEMORY"] = "2000"
        
        settings = Settings()
        
        assert settings.llm_model == "test-model"
        assert settings.max_llm_memory == 2000
        
        # Cleanup
        del os.environ["LLM_MODEL"]
        del os.environ["MAX_LLM_MEMORY"]
    
    def test_allowed_file_types_list(self):
        """Test allowed file types property"""
        settings = Settings()
        
        file_types = settings.allowed_file_types_list
        assert isinstance(file_types, list)
        assert ".pdf" in file_types
        assert ".docx" in file_types
        assert ".xlsx" in file_types
    
    def test_database_url_format(self):
        """Test database URL format"""
        settings = Settings()
        
        # In test environment, we use SQLite
        if "test.db" in settings.database_url:
            assert "sqlite://" in settings.database_url
        else:
            assert "postgresql://" in settings.database_url
            assert "kpfu_generator" in settings.database_url
    
    def test_redis_url_format(self):
        """Test Redis URL format"""
        settings = Settings()
        
        assert "redis://" in settings.redis_url
    
    def test_memory_limits_positive(self):
        """Test that memory limits are positive values"""
        settings = Settings()
        
        assert settings.max_llm_memory > 0
        assert settings.max_embedding_memory > 0
        assert settings.max_cache_size_mb > 0
    
    def test_performance_settings_reasonable(self):
        """Test that performance settings are reasonable"""
        settings = Settings()
        
        assert 1 <= settings.max_concurrent_requests <= 100
        assert 60 <= settings.request_timeout_seconds <= 3600  # 1 min to 1 hour
        assert settings.max_context_tokens > 0