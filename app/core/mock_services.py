"""
Mock services for local development without Docker
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MockRedis:
    """Mock Redis client for local development"""
    
    def __init__(self):
        self.data: Dict[str, str] = {}
        self.expires: Dict[str, datetime] = {}
    
    async def ping(self):
        return True
    
    async def get(self, key: str) -> Optional[str]:
        if key in self.data:
            if key in self.expires and datetime.now() > self.expires[key]:
                del self.data[key]
                del self.expires[key]
                return None
            return self.data[key]
        return None
    
    async def setex(self, key: str, ttl: int, value: str):
        from datetime import timedelta
        self.data[key] = value
        self.expires[key] = datetime.now() + timedelta(seconds=ttl)
    
    async def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
            self.expires.pop(key, None)
    
    async def keys(self, pattern: str) -> List[str]:
        if pattern == "*":
            return list(self.data.keys())
        # Simple pattern matching
        pattern = pattern.replace("*", "")
        return [key for key in self.data.keys() if pattern in key]
    
    async def info(self) -> Dict[str, Any]:
        return {
            "used_memory_human": f"{len(str(self.data))}B",
            "connected_clients": 1,
            "total_commands_processed": 100
        }
    
    async def close(self):
        pass


class MockOllama:
    """Mock Ollama client for local development"""
    
    def __init__(self, host: str = None):
        self.host = host
    
    async def list(self) -> Dict[str, List[Dict]]:
        return {
            "models": [
                {"name": "llama3.1:8b", "size": 4700000000}
            ]
        }
    
    async def pull(self, model: str):
        logger.info(f"Mock: Pulling model {model}")
        await asyncio.sleep(1)  # Simulate download time
        return {"status": "success"}
    
    async def generate(self, model: str, prompt: str, options: Dict = None) -> Dict[str, str]:
        logger.info(f"Mock: Generating response for prompt: {prompt[:50]}...")
        await asyncio.sleep(2)  # Simulate generation time
        
        # Simple mock responses based on prompt content
        if "привет" in prompt.lower() or "hello" in prompt.lower():
            response = "Привет! Я работаю в тестовом режиме."
        elif "лекция" in prompt.lower() or "lecture" in prompt.lower():
            response = """# Тестовая лекция

## Введение
Это тестовая лекция, сгенерированная в режиме разработки.

## Основная часть
Здесь будет содержание лекции на основе литературы из библиотеки КПФУ.

## Заключение
Материал подготовлен с использованием проверенных источников."""
        else:
            response = "Это тестовый ответ от mock-сервиса Ollama."
        
        return {
            "response": response,
            "done": True,
            "total_duration": 2000000000,  # 2 seconds in nanoseconds
            "load_duration": 100000000,    # 0.1 seconds
            "prompt_eval_count": len(prompt.split()),
            "eval_count": len(response.split())
        }


class MockChromaDB:
    """Mock ChromaDB client for local development"""
    
    def __init__(self, host: str = None):
        self.host = host
        self.collections: Dict[str, Dict] = {}
    
    def get_or_create_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = {
                "documents": [],
                "embeddings": [],
                "metadatas": [],
                "ids": []
            }
        return MockCollection(self.collections[name])
    
    def list_collections(self):
        return [{"name": name} for name in self.collections.keys()]


class MockCollection:
    """Mock ChromaDB collection"""
    
    def __init__(self, data: Dict):
        self.data = data
    
    def add(self, documents: List[str], embeddings: List[List[float]], 
            metadatas: List[Dict], ids: List[str]):
        self.data["documents"].extend(documents)
        self.data["embeddings"].extend(embeddings)
        self.data["metadatas"].extend(metadatas)
        self.data["ids"].extend(ids)
    
    def query(self, query_embeddings: List[List[float]], n_results: int = 10):
        # Simple mock query - return first n_results
        n = min(n_results, len(self.data["documents"]))
        return {
            "documents": [self.data["documents"][:n]],
            "metadatas": [self.data["metadatas"][:n]],
            "distances": [[0.1] * n],  # Mock distances
            "ids": [self.data["ids"][:n]]
        }
    
    def count(self):
        return len(self.data["documents"])


class MockSentenceTransformer:
    """Mock SentenceTransformer for local development"""
    
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        logger.info(f"Mock: Loading SentenceTransformer {model_name} on {device}")
    
    def encode(self, sentences, **kwargs) -> List[float]:
        """Return mock embeddings"""
        if isinstance(sentences, str):
            # Return a fixed-size embedding (384 dimensions for MiniLM)
            return [0.1] * 384
        else:
            # Return embeddings for multiple sentences
            return [[0.1] * 384 for _ in sentences]


def get_mock_services():
    """Get all mock services for local development"""
    return {
        "redis": MockRedis(),
        "ollama": MockOllama(),
        "chromadb": MockChromaDB(),
        "sentence_transformer": MockSentenceTransformer
    }