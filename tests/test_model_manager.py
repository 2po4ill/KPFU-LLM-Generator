"""
Tests for model manager module
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core.model_manager import ModelManager


class TestModelManager:
    """Test ModelManager functionality"""
    
    @pytest.fixture
    async def model_manager_mock(self):
        """Create a model manager with mock services"""
        manager = ModelManager(use_mock_services=True)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    async def test_initialization_mock_mode(self, model_manager_mock):
        """Test model manager initialization in mock mode"""
        assert model_manager_mock.use_mock_services is True
        assert model_manager_mock.embedding_model is not None
        assert hasattr(model_manager_mock, 'mock_services')
        assert model_manager_mock.unload_timer_task is not None
    
    async def test_get_llm_model_mock(self, model_manager_mock):
        """Test getting LLM model in mock mode"""
        model = await model_manager_mock.get_llm_model()
        
        assert model is not None
        assert hasattr(model, 'generate')  # Mock Ollama should have generate method
        assert "llm" in model_manager_mock.model_last_used
    
    async def test_get_embedding_model_mock(self, model_manager_mock):
        """Test getting embedding model in mock mode"""
        model = await model_manager_mock.get_embedding_model()
        
        assert model is not None
        assert hasattr(model, 'encode')  # Mock SentenceTransformer should have encode method
        assert "embedding" in model_manager_mock.model_last_used
    
    async def test_llm_model_generation_mock(self, model_manager_mock):
        """Test LLM model generation in mock mode"""
        model = await model_manager_mock.get_llm_model()
        
        response = await model.generate(
            model="llama3.1:8b",
            prompt="Test prompt",
            options={"temperature": 0.1}
        )
        
        assert "response" in response
        assert "done" in response
        assert isinstance(response["response"], str)
        assert response["done"] is True
    
    async def test_embedding_model_encoding_mock(self, model_manager_mock):
        """Test embedding model encoding in mock mode"""
        model = await model_manager_mock.get_embedding_model()
        
        embedding = model.encode("Test sentence for embedding")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # Mock MiniLM dimension
        assert all(isinstance(x, float) for x in embedding)
    
    async def test_memory_usage_stats(self, model_manager_mock):
        """Test getting memory usage statistics"""
        stats = model_manager_mock.get_memory_usage()
        
        assert "total_mb" in stats
        assert "available_mb" in stats
        assert "used_mb" in stats
        assert "percent" in stats
        assert "llm_loaded" in stats
        assert "embedding_loaded" in stats
        assert "models_last_used" in stats
        
        assert isinstance(stats["total_mb"], int)
        assert isinstance(stats["available_mb"], int)
        assert isinstance(stats["used_mb"], int)
        assert isinstance(stats["percent"], float)
        assert isinstance(stats["llm_loaded"], bool)
        assert isinstance(stats["embedding_loaded"], bool)
        assert isinstance(stats["models_last_used"], dict)
    
    async def test_model_unloading(self, model_manager_mock):
        """Test model unloading functionality"""
        # Load models first
        await model_manager_mock.get_llm_model()
        await model_manager_mock.get_embedding_model()
        
        # Unload LLM model
        await model_manager_mock._unload_llm_model()
        
        # LLM should be unloaded but embedding should remain
        stats = model_manager_mock.get_memory_usage()
        assert stats["llm_loaded"] is False
        assert stats["embedding_loaded"] is True
    
    async def test_cleanup(self, model_manager_mock):
        """Test model manager cleanup"""
        # Load models first
        await model_manager_mock.get_llm_model()
        await model_manager_mock.get_embedding_model()
        
        # Cleanup should not raise errors
        await model_manager_mock.cleanup()
        
        # Timer task should be cancelled
        assert model_manager_mock.unload_timer_task.cancelled()


class TestModelManagerProduction:
    """Test ModelManager in production mode (without actual services)"""
    
    async def test_initialization_production_mode_fallback(self):
        """Test that production mode falls back gracefully when services unavailable"""
        # This should fall back to mock services when real services aren't available
        manager = ModelManager(use_mock_services=False)
        
        # Should not raise exception even if real services aren't available
        try:
            await manager.initialize()
            await manager.cleanup()
        except Exception as e:
            # If it fails, it should be due to missing services, not code errors
            assert "connect" in str(e).lower() or "available" in str(e).lower()
    
    def test_memory_calculation(self):
        """Test memory calculation methods"""
        manager = ModelManager(use_mock_services=True)
        
        # Should be able to get available memory
        available_mb = manager._get_available_memory_mb()
        assert isinstance(available_mb, int)
        assert available_mb > 0
    
    async def test_model_loading_lock(self):
        """Test that model loading uses proper locking"""
        manager = ModelManager(use_mock_services=True)
        await manager.initialize()
        
        # The lock should exist
        assert manager.model_load_lock is not None
        
        # Multiple concurrent loads should be handled properly
        tasks = [
            manager.get_llm_model(),
            manager.get_llm_model(),
            manager.get_llm_model()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should return the same model instance
        assert all(result is results[0] for result in results)
        
        await manager.cleanup()


class TestModelManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    async def test_double_initialization(self):
        """Test that double initialization doesn't cause issues"""
        manager = ModelManager(use_mock_services=True)
        
        await manager.initialize()
        await manager.initialize()  # Should not cause issues
        
        await manager.cleanup()
    
    async def test_cleanup_before_initialization(self):
        """Test cleanup before initialization"""
        manager = ModelManager(use_mock_services=True)
        
        # Should not raise exception
        await manager.cleanup()
    
    async def test_get_model_before_initialization(self):
        """Test getting models before initialization"""
        manager = ModelManager(use_mock_services=True)
        
        # Should raise exception or handle gracefully
        try:
            await manager.get_llm_model()
            # If it doesn't raise, the model should be None or properly initialized
        except Exception as e:
            # Should be a reasonable error message
            assert len(str(e)) > 0
        
        await manager.cleanup()
    
    async def test_multiple_cleanup_calls(self):
        """Test multiple cleanup calls"""
        manager = ModelManager(use_mock_services=True)
        await manager.initialize()
        
        # Multiple cleanups should not cause issues
        await manager.cleanup()
        await manager.cleanup()
        await manager.cleanup()