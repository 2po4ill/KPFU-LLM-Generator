"""
Tests for mock services
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core.mock_services import (
    MockRedis, MockOllama, MockChromaDB, MockCollection, 
    MockSentenceTransformer, get_mock_services
)


class TestMockRedis:
    """Test MockRedis functionality"""
    
    @pytest.fixture
    def redis_mock(self):
        return MockRedis()
    
    @pytest.mark.asyncio
    async def test_ping(self, redis_mock):
        """Test Redis ping"""
        result = await redis_mock.ping()
        assert result is True
    
    async def test_set_get(self, redis_mock):
        """Test Redis set and get operations"""
        await redis_mock.setex("test_key", 60, "test_value")
        result = await redis_mock.get("test_key")
        assert result == "test_value"
    
    async def test_get_nonexistent(self, redis_mock):
        """Test getting non-existent key"""
        result = await redis_mock.get("nonexistent")
        assert result is None
    
    async def test_expiration(self, redis_mock):
        """Test key expiration"""
        # Set key with very short TTL
        await redis_mock.setex("expire_key", 1, "expire_value")
        
        # Manually expire by setting past time
        redis_mock.expires["expire_key"] = datetime.now() - timedelta(seconds=1)
        
        result = await redis_mock.get("expire_key")
        assert result is None
        assert "expire_key" not in redis_mock.data
    
    async def test_delete(self, redis_mock):
        """Test key deletion"""
        await redis_mock.setex("delete_key", 60, "delete_value")
        await redis_mock.delete("delete_key")
        
        result = await redis_mock.get("delete_key")
        assert result is None
    
    async def test_keys_pattern(self, redis_mock):
        """Test keys pattern matching"""
        await redis_mock.setex("test:1", 60, "value1")
        await redis_mock.setex("test:2", 60, "value2")
        await redis_mock.setex("other", 60, "value3")
        
        keys = await redis_mock.keys("test")
        assert len(keys) == 2
        assert all("test" in key for key in keys)
    
    async def test_info(self, redis_mock):
        """Test Redis info command"""
        info = await redis_mock.info()
        
        assert "used_memory_human" in info
        assert "connected_clients" in info
        assert "total_commands_processed" in info
        assert info["connected_clients"] == 1


class TestMockOllama:
    """Test MockOllama functionality"""
    
    @pytest.fixture
    def ollama_mock(self):
        return MockOllama()
    
    async def test_list_models(self, ollama_mock):
        """Test listing available models"""
        result = await ollama_mock.list()
        
        assert "models" in result
        assert isinstance(result["models"], list)
        assert len(result["models"]) > 0
        assert result["models"][0]["name"] == "llama3.1:8b"
    
    async def test_pull_model(self, ollama_mock):
        """Test pulling a model"""
        result = await ollama_mock.pull("test-model")
        
        assert "status" in result
        assert result["status"] == "success"
    
    async def test_generate_response(self, ollama_mock):
        """Test generating a response"""
        result = await ollama_mock.generate(
            model="llama3.1:8b",
            prompt="Hello, how are you?",
            options={"temperature": 0.1}
        )
        
        assert "response" in result
        assert "done" in result
        assert "total_duration" in result
        assert result["done"] is True
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
    
    async def test_generate_russian_response(self, ollama_mock):
        """Test generating response to Russian prompt"""
        result = await ollama_mock.generate(
            model="llama3.1:8b",
            prompt="Привет! Как дела?",
            options={}
        )
        
        assert "response" in result
        assert "Привет" in result["response"] or "работаю" in result["response"]
    
    async def test_generate_lecture_response(self, ollama_mock):
        """Test generating lecture content"""
        result = await ollama_mock.generate(
            model="llama3.1:8b",
            prompt="Создай лекцию по программированию",
            options={}
        )
        
        assert "response" in result
        assert "лекция" in result["response"].lower()


class TestMockChromaDB:
    """Test MockChromaDB functionality"""
    
    @pytest.fixture
    def chromadb_mock(self):
        return MockChromaDB()
    
    def test_create_collection(self, chromadb_mock):
        """Test creating a collection"""
        collection = chromadb_mock.get_or_create_collection("test_collection")
        
        assert isinstance(collection, MockCollection)
        assert "test_collection" in chromadb_mock.collections
    
    def test_list_collections(self, chromadb_mock):
        """Test listing collections"""
        chromadb_mock.get_or_create_collection("collection1")
        chromadb_mock.get_or_create_collection("collection2")
        
        collections = chromadb_mock.list_collections()
        
        assert len(collections) == 2
        collection_names = [c["name"] for c in collections]
        assert "collection1" in collection_names
        assert "collection2" in collection_names


class TestMockCollection:
    """Test MockCollection functionality"""
    
    @pytest.fixture
    def collection(self):
        data = {"documents": [], "embeddings": [], "metadatas": [], "ids": []}
        return MockCollection(data)
    
    def test_add_documents(self, collection):
        """Test adding documents to collection"""
        documents = ["Document 1", "Document 2"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        metadatas = [{"source": "test1"}, {"source": "test2"}]
        ids = ["id1", "id2"]
        
        collection.add(documents, embeddings, metadatas, ids)
        
        assert len(collection.data["documents"]) == 2
        assert len(collection.data["embeddings"]) == 2
        assert len(collection.data["metadatas"]) == 2
        assert len(collection.data["ids"]) == 2
    
    def test_query_documents(self, collection):
        """Test querying documents"""
        # Add some documents first
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        metadatas = [{"id": 1}, {"id": 2}, {"id": 3}]
        ids = ["1", "2", "3"]
        
        collection.add(documents, embeddings, metadatas, ids)
        
        # Query
        result = collection.query([[0.1, 0.2]], n_results=2)
        
        assert "documents" in result
        assert "metadatas" in result
        assert "distances" in result
        assert "ids" in result
        assert len(result["documents"][0]) == 2  # n_results=2
    
    def test_count_documents(self, collection):
        """Test counting documents"""
        assert collection.count() == 0
        
        collection.add(["Doc 1"], [[0.1, 0.2]], [{"id": 1}], ["1"])
        assert collection.count() == 1


class TestMockSentenceTransformer:
    """Test MockSentenceTransformer functionality"""
    
    @pytest.fixture
    def transformer(self):
        return MockSentenceTransformer("test-model")
    
    def test_encode_single_sentence(self, transformer):
        """Test encoding a single sentence"""
        embedding = transformer.encode("This is a test sentence")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # MiniLM dimension
        assert all(isinstance(x, float) for x in embedding)
    
    def test_encode_multiple_sentences(self, transformer):
        """Test encoding multiple sentences"""
        sentences = ["Sentence 1", "Sentence 2", "Sentence 3"]
        embeddings = transformer.encode(sentences)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)


class TestGetMockServices:
    """Test get_mock_services function"""
    
    def test_get_all_services(self):
        """Test getting all mock services"""
        services = get_mock_services()
        
        assert "redis" in services
        assert "ollama" in services
        assert "chromadb" in services
        assert "sentence_transformer" in services
        
        assert isinstance(services["redis"], MockRedis)
        assert isinstance(services["ollama"], MockOllama)
        assert isinstance(services["chromadb"], MockChromaDB)
        assert callable(services["sentence_transformer"])  # It's a class