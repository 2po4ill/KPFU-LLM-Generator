"""
Multi-layer caching system for KPFU LLM Generator
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import hashlib

import redis.asyncio as redis
from core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Multi-layer caching system for performance optimization"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_cache_size = 1000  # Maximum items in memory cache
        
    async def initialize(self):
        """Initialize cache connections"""
        try:
            # Check if using mock services
            import os
            if os.getenv("USE_MOCK_SERVICES", "false").lower() == "true":
                from core.mock_services import MockRedis
                self.redis_client = MockRedis()
                logger.info("Mock Redis cache initialized")
            else:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Running without Redis cache")
            self.redis_client = None
    
    async def cleanup(self):
        """Cleanup cache connections"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_cache_key(self, cache_type: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = f"{cache_type}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, cache_type: str, **kwargs) -> Optional[Any]:
        """Get item from cache"""
        cache_key = self._generate_cache_key(cache_type, **kwargs)
        
        # Try memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if datetime.now() < entry['expires']:
                logger.debug(f"Cache hit (memory): {cache_key}")
                return entry['data']
            else:
                # Expired, remove from memory cache
                del self.memory_cache[cache_key]
        
        # Try Redis cache
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit (Redis): {cache_key}")
                    data = json.loads(cached_data)
                    
                    # Store in memory cache for faster access
                    self._store_in_memory_cache(cache_key, data)
                    return data
                    
            except Exception as e:
                logger.error(f"Redis cache get error: {e}")
        
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    async def set(self, cache_type: str, data: Any, ttl_seconds: Optional[int] = None, **kwargs):
        """Set item in cache"""
        cache_key = self._generate_cache_key(cache_type, **kwargs)
        ttl = ttl_seconds or settings.cache_ttl_seconds
        
        # Store in memory cache
        self._store_in_memory_cache(cache_key, data, ttl)
        
        # Store in Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(data, default=str)
                )
                logger.debug(f"Cache set: {cache_key}")
                
            except Exception as e:
                logger.error(f"Redis cache set error: {e}")
    
    def _store_in_memory_cache(self, cache_key: str, data: Any, ttl_seconds: int = None):
        """Store item in memory cache"""
        ttl = ttl_seconds or settings.cache_ttl_seconds
        expires = datetime.now() + timedelta(seconds=ttl)
        
        # Clean up memory cache if too large
        if len(self.memory_cache) >= self.max_memory_cache_size:
            self._cleanup_memory_cache()
        
        self.memory_cache[cache_key] = {
            'data': data,
            'expires': expires
        }
    
    def _cleanup_memory_cache(self):
        """Remove expired items from memory cache"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if now >= entry['expires']
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        # If still too large, remove oldest items
        if len(self.memory_cache) >= self.max_memory_cache_size:
            # Remove 20% of items
            items_to_remove = int(self.max_memory_cache_size * 0.2)
            keys_to_remove = list(self.memory_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self.memory_cache[key]
    
    # Specific cache methods for different data types
    
    async def get_keyword_relevance(self, theme: str, book_title: str) -> Optional[float]:
        """Get cached keyword relevance score"""
        return await self.get("keyword_relevance", theme=theme, book_title=book_title)
    
    async def set_keyword_relevance(self, theme: str, book_title: str, score: float):
        """Cache keyword relevance score"""
        await self.set("keyword_relevance", score, theme=theme, book_title=book_title)
    
    async def get_page_selection(self, theme: str, book_id: str) -> Optional[List[int]]:
        """Get cached page selection"""
        return await self.get("page_selection", theme=theme, book_id=book_id)
    
    async def set_page_selection(self, theme: str, book_id: str, pages: List[int]):
        """Cache page selection"""
        await self.set("page_selection", pages, theme=theme, book_id=book_id)
    
    async def get_model_output(self, prompt_hash: str) -> Optional[str]:
        """Get cached model output"""
        return await self.get("model_output", prompt_hash=prompt_hash)
    
    async def set_model_output(self, prompt_hash: str, output: str):
        """Cache model output"""
        await self.set("model_output", output, prompt_hash=prompt_hash)
    
    async def get_fgos_template(self, profession: str, degree: str) -> Optional[str]:
        """Get cached FGOS template"""
        return await self.get("fgos_template", profession=profession, degree=degree)
    
    async def set_fgos_template(self, profession: str, degree: str, template: str):
        """Cache FGOS template"""
        # FGOS templates rarely change, cache for longer
        await self.set("fgos_template", template, ttl_seconds=86400, profession=profession, degree=degree)
    
    async def get_book_embeddings(self, book_id: str) -> Optional[List[float]]:
        """Get cached book embeddings"""
        return await self.get("book_embeddings", book_id=book_id)
    
    async def set_book_embeddings(self, book_id: str, embeddings: List[float]):
        """Cache book embeddings"""
        # Embeddings are expensive to compute, cache for longer
        await self.set("book_embeddings", embeddings, ttl_seconds=86400, book_id=book_id)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"*{pattern}*")
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries matching pattern: {pattern}")
            except Exception as e:
                logger.error(f"Cache invalidation error: {e}")
        
        # Also clean memory cache
        keys_to_remove = [key for key in self.memory_cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.memory_cache[key]
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "memory_cache_size": len(self.memory_cache),
            "memory_cache_max_size": self.max_memory_cache_size,
            "redis_connected": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    "redis_used_memory": info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_total_commands_processed": info.get("total_commands_processed", 0)
                })
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats


# Global cache manager instance
cache_manager = CacheManager()