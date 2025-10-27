"""
Configuration settings for KPFU LLM Generator
"""

import os
from typing import Optional, List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://kpfu_user:kpfu_password@localhost:5432/kpfu_generator"
    )
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # ChromaDB
    chromadb_url: str = os.getenv("CHROMADB_URL", "http://localhost:8000")
    
    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    # Model settings
    llm_model: str = "llama3.1:8b"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    
    # Memory limits (in MB)
    max_llm_memory: int = 4700  # 4.7GB for Llama 3.1 8B
    max_embedding_memory: int = 118  # 118MB for sentence transformer
    max_context_tokens: int = 5000
    
    # Cache settings
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size_mb: int = 500
    
    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 300  # 5 minutes
    
    # File upload settings
    max_file_size_mb: int = 50
    allowed_file_types: str = ".pdf,.docx,.xlsx"
    
    # Development settings
    debug: bool = False
    log_level: str = "INFO"
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]
    
    model_config = {"env_file": ".env"}


# Global settings instance
settings = Settings()