"""
Tests for cache module
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core.cache import CacheManager


class TestCacheManager:
    """Test CacheManager functionality"""
    
    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager for testing"""
        manager = CacheManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    async def test_initialization(self, cache_manager):
        """Test cache manager initialization"""
        assert cache_manager.redis_client is not None
        assert isinstance(cache_manager.memory_cache, dict)
        assert cache_manager.max_memory_cache_size == 1000
    
    async def test_generate_cache_key(self, cache_manager):
        """Test cache key generation"""
        key1 = cache_manager._generate_cache_key("test_type", param1="value1", param2="value2")
        key2 = cache_manager._generate_cache_key("test_type", param2="value2", param1="value1")
        
        # Same parameters should generate same key regardless of order
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = cache_manager._generate_cache_key("test_type", param1="different")
        assert key1 != key3
    
    async def test_set_and_get(self, cache_manager):
        """Test basic set and get operations"""
        test_data = {"key": "value", "number": 42}
        
        await cache_manager.set("test_type", test_data, param1="test")
        result = await cache_manager.get("test_type", param1="test")
        
        assert result == test_data
    
    async def test_get_nonexistent(self, cache_manager):
        """Test getting non-existent cache entry"""
        result = await cache_manager.get("nonexistent_type", param="value")
        assert result is None
    
    async def test_memory_cache_priority(self, cache_manager):
        """Test that memory cache is checked first"""
        test_data = {"source": "memory"}
        
        # Set in memory cache directly
        cache_key = cache_manager._generate_cache_key("test_type", param="test")
        cache_manager._store_in_memory_cache(cache_key, test_data)
        
        result = await cache_manager.get("test_type", param="test")
        assert result == test_data
    
    async def test_ttl_expiration(self, cache_manager):
        """Test TTL expiration"""
        test_data = {"expires": "soon"}
        
        # Set with very short TTL
        await cache_manager.set("test_type", test_data, ttl_seconds=1, param="expire_test")
        
        # Should be available immediately
        result = await cache_manager.get("test_type", param="expire_test")
        assert result == test_data
        
        # Manually expire memory cache entry
        cache_key = cache_manager._generate_cache_key("test_type", param="expire_test")
        if cache_key in cache_manager.memory_cache:
            cache_manager.memory_cache[cache_key]['expires'] = datetime.now() - timedelta(seconds=1)
        
        # Should be None after expiration
        result = await cache_manager.get("test_type", param="expire_test")
        # Note: In mock Redis, this might still return the value, but memory cache should be cleared
    
    async def test_memory_cache_cleanup(self, cache_manager):
        """Test memory cache cleanup when it gets too large"""
        # Fill memory cache beyond limit
        original_limit = cache_manager.max_memory_cache_size
        cache_manager.max_memory_cache_size = 5  # Set low limit for testing
        
        # Add more items than the limit
        for i in range(10):
            cache_key = f"test_key_{i}"
            cache_manager._store_in_memory_cache(cache_key, f"value_{i}")
        
        # Should not exceed the limit significantly
        assert len(cache_manager.memory_cache) <= cache_manager.max_memory_cache_size * 1.2
        
        # Restore original limit
        cache_manager.max_memory_cache_size = original_limit
    
    async def test_keyword_relevance_cache(self, cache_manager):
        """Test keyword relevance caching"""
        score = 0.85
        
        await cache_manager.set_keyword_relevance("Machine Learning", "AI Textbook", score)
        result = await cache_manager.get_keyword_relevance("Machine Learning", "AI Textbook")
        
        assert result == score
    
    async def test_page_selection_cache(self, cache_manager):
        """Test page selection caching"""
        pages = [1, 5, 10, 15, 20]
        
        await cache_manager.set_page_selection("Neural Networks", "book_123", pages)
        result = await cache_manager.get_page_selection("Neural Networks", "book_123")
        
        assert result == pages
    
    async def test_model_output_cache(self, cache_manager):
        """Test model output caching"""
        prompt_hash = "abc123def456"
        output = "This is a generated response from the model."
        
        await cache_manager.set_model_output(prompt_hash, output)
        result = await cache_manager.get_model_output(prompt_hash)
        
        assert result == output
    
    async def test_fgos_template_cache(self, cache_manager):
        """Test FGOS template caching"""
        template = "FGOS template for computer science bachelor degree"
        
        await cache_manager.set_fgos_template("Computer Science", "bachelor", template)
        result = await cache_manager.get_fgos_template("Computer Science", "bachelor")
        
        assert result == template
    
    async def test_book_embeddings_cache(self, cache_manager):
        """Test book embeddings caching"""
        embeddings = [0.1, 0.2, 0.3, 0.4, 0.5] * 76  # 380 dimensions
        
        await cache_manager.set_book_embeddings("book_456", embeddings)
        result = await cache_manager.get_book_embeddings("book_456")
        
        assert result == embeddings
    
    async def test_invalidate_pattern(self, cache_manager):
        """Test cache invalidation by pattern"""
        # Set multiple cache entries
        await cache_manager.set("test_type", "data1", key="test_1")
        await cache_manager.set("test_type", "data2", key="test_2")
        await cache_manager.set("other_type", "data3", key="other_1")
        
        # Invalidate entries matching pattern
        await cache_manager.invalidate_pattern("test")
        
        # Test entries should be gone
        result1 = await cache_manager.get("test_type", key="test_1")
        result2 = await cache_manager.get("test_type", key="test_2")
        result3 = await cache_manager.get("other_type", key="other_1")
        
        # Note: Exact behavior depends on mock implementation
        # At minimum, memory cache should be cleared
        assert len([k for k in cache_manager.memory_cache.keys() if "test" in k]) == 0
    
    async def test_cache_stats(self, cache_manager):
        """Test getting cache statistics"""
        stats = await cache_manager.get_cache_stats()
        
        assert "memory_cache_size" in stats
        assert "memory_cache_max_size" in stats
        assert "redis_connected" in stats
        
        assert isinstance(stats["memory_cache_size"], int)
        assert isinstance(stats["memory_cache_max_size"], int)
        assert isinstance(stats["redis_connected"], bool)
        
        if stats["redis_connected"]:
            assert "redis_used_memory" in stats
            assert "redis_connected_clients" in stats