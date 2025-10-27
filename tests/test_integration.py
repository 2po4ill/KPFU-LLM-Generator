"""
Integration tests for KPFU LLM Generator
"""

import pytest
import asyncio
import os
import sys
from fastapi.testclient import TestClient

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app
from core.model_manager import ModelManager
from core.cache import cache_manager


class TestSystemIntegration:
    """Test system integration scenarios"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as test_client:
            yield test_client
    
    def test_full_system_startup(self, client):
        """Test that the full system starts up correctly"""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Test status endpoint
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
    
    def test_model_and_cache_integration(self, client):
        """Test integration between model manager and cache"""
        # Load models
        response = client.post("/api/v1/models/load")
        assert response.status_code == 200
        
        # Check status shows models loaded
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        
        models = data["models"]
        assert models["embedding_loaded"] is True
        
        # Clear cache
        response = client.post("/api/v1/cache/clear")
        assert response.status_code == 200
        
        # Cache stats should show cleared cache
        response = client.get("/api/v1/status")
        data = response.json()
        cache_stats = data["cache_stats"]
        assert cache_stats["memory_cache_size"] == 0
    
    def test_concurrent_api_requests(self, client):
        """Test handling of concurrent API requests"""
        import concurrent.futures
        
        def make_requests():
            responses = []
            endpoints = ["/health", "/api/v1/status", "/api/v1/health/detailed"]
            
            for endpoint in endpoints:
                response = client.get(endpoint)
                responses.append((endpoint, response.status_code))
            
            return responses
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_requests) for _ in range(5)]
            all_responses = [future.result() for future in futures]
        
        # All requests should succeed
        for responses in all_responses:
            for endpoint, status_code in responses:
                assert status_code == 200, f"Failed: {endpoint}"
    
    def test_error_recovery(self, client):
        """Test system error recovery"""
        # Make a request that might cause an error
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        # System should still be healthy after error
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_memory_monitoring_integration(self, client):
        """Test memory monitoring across components"""
        # Get initial memory stats
        response = client.get("/api/v1/status")
        data = response.json()
        initial_memory = data["memory_usage"]
        
        # Load models (should increase memory usage)
        response = client.post("/api/v1/models/load")
        assert response.status_code == 200
        
        # Check memory stats again
        response = client.get("/api/v1/status")
        data = response.json()
        current_memory = data["memory_usage"]
        
        # Memory stats should be consistent
        assert current_memory["total_mb"] == initial_memory["total_mb"]
        assert current_memory["used_mb"] >= 0
        assert current_memory["available_mb"] >= 0
        assert 0 <= current_memory["percent"] <= 100


class TestAsyncIntegration:
    """Test async integration scenarios"""
    
    async def test_model_manager_cache_integration(self):
        """Test integration between model manager and cache manager"""
        # Initialize both components
        await cache_manager.initialize()
        
        model_manager = ModelManager(use_mock_services=True)
        await model_manager.initialize()
        
        try:
            # Test that both work together
            embedding_model = await model_manager.get_embedding_model()
            assert embedding_model is not None
            
            # Test cache operations
            await cache_manager.set("test_type", {"data": "test"}, key="integration_test")
            cached_data = await cache_manager.get("test_type", key="integration_test")
            assert cached_data == {"data": "test"}
            
            # Test memory stats
            memory_stats = model_manager.get_memory_usage()
            cache_stats = await cache_manager.get_cache_stats()
            
            assert "embedding_loaded" in memory_stats
            assert "memory_cache_size" in cache_stats
            
        finally:
            await model_manager.cleanup()
            await cache_manager.cleanup()
    
    async def test_concurrent_model_operations(self):
        """Test concurrent model operations"""
        model_manager = ModelManager(use_mock_services=True)
        await model_manager.initialize()
        
        try:
            # Concurrent model access
            tasks = [
                model_manager.get_llm_model(),
                model_manager.get_embedding_model(),
                model_manager.get_llm_model(),
                model_manager.get_embedding_model()
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Should get consistent results
            llm_models = [r for i, r in enumerate(results) if i % 2 == 0]
            embedding_models = [r for i, r in enumerate(results) if i % 2 == 1]
            
            # All LLM models should be the same instance
            assert all(model is llm_models[0] for model in llm_models)
            # All embedding models should be the same instance
            assert all(model is embedding_models[0] for model in embedding_models)
            
        finally:
            await model_manager.cleanup()
    
    async def test_cache_performance_under_load(self):
        """Test cache performance under load"""
        await cache_manager.initialize()
        
        try:
            # Set many cache entries concurrently
            async def set_cache_entry(i):
                await cache_manager.set("load_test", f"data_{i}", key=f"test_{i}")
                return await cache_manager.get("load_test", key=f"test_{i}")
            
            tasks = [set_cache_entry(i) for i in range(50)]
            results = await asyncio.gather(*tasks)
            
            # All operations should succeed
            for i, result in enumerate(results):
                assert result == f"data_{i}"
            
            # Cache stats should reflect the operations
            stats = await cache_manager.get_cache_stats()
            assert stats["memory_cache_size"] > 0
            
        finally:
            await cache_manager.cleanup()


class TestSystemResilience:
    """Test system resilience and error handling"""
    
    def test_graceful_degradation(self, client):
        """Test graceful degradation when components fail"""
        # Even if some components have issues, basic endpoints should work
        response = client.get("/")
        assert response.status_code == 200
        
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_resource_cleanup(self, client):
        """Test that resources are properly cleaned up"""
        # Make several requests
        for _ in range(10):
            response = client.get("/api/v1/status")
            assert response.status_code == 200
        
        # Memory usage should be stable
        response = client.get("/api/v1/status")
        data = response.json()
        memory = data["memory_usage"]
        
        # Memory percent should be reasonable (not growing indefinitely)
        assert memory["percent"] < 90  # Should not be using >90% memory
    
    def test_configuration_validation(self, client):
        """Test that configuration is properly validated"""
        # System should start with valid configuration
        response = client.get("/health")
        assert response.status_code == 200
        
        # Status should show operational system
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"


class TestEndToEndScenarios:
    """Test end-to-end scenarios"""
    
    def test_typical_user_workflow(self, client):
        """Test a typical user workflow"""
        # 1. Check system health
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # 2. Check system status
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        
        # 3. Load models if needed
        if not data["models"]["embedding_loaded"]:
            response = client.post("/api/v1/models/load")
            assert response.status_code == 200
        
        # 4. Check detailed health
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["overall"] in ["healthy", "degraded"]
        
        # 5. Clear cache if needed
        response = client.post("/api/v1/cache/clear")
        assert response.status_code == 200
    
    def test_monitoring_workflow(self, client):
        """Test monitoring and observability workflow"""
        # Get baseline metrics
        response = client.get("/api/v1/status")
        baseline = response.json()
        
        # Perform some operations
        client.post("/api/v1/models/load")
        client.post("/api/v1/cache/clear")
        
        # Check metrics again
        response = client.get("/api/v1/status")
        current = response.json()
        
        # Metrics should be consistent and reasonable
        assert current["status"] == "operational"
        assert current["memory_usage"]["total_mb"] == baseline["memory_usage"]["total_mb"]
        
        # Detailed health should provide component status
        response = client.get("/api/v1/health/detailed")
        detailed = response.json()
        
        assert "components" in detailed
        assert len(detailed["components"]) > 0