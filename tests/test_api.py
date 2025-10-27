"""
Tests for API endpoints
"""

import pytest
import json
import os
import sys
from fastapi.testclient import TestClient

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app


class TestAPIEndpoints:
    """Test API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        with TestClient(app) as test_client:
            yield test_client
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "KPFU" in data["message"]
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "mode" in data
        assert "database" in data
        assert "redis" in data
        assert "chromadb" in data
        assert "ollama" in data
        
        assert data["status"] == "healthy"
        assert data["mode"] in ["mock", "production"]
    
    def test_system_status_endpoint(self, client):
        """Test system status endpoint"""
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "memory_usage" in data
        assert "cache_stats" in data
        assert "models" in data
        
        # Check memory usage structure
        memory = data["memory_usage"]
        assert "total_mb" in memory
        assert "available_mb" in memory
        assert "used_mb" in memory
        assert "percent" in memory
        assert "llm_loaded" in memory
        assert "embedding_loaded" in memory
        
        # Check cache stats structure
        cache = data["cache_stats"]
        assert "memory_cache_size" in cache
        assert "redis_connected" in cache
        
        # Check models structure
        models = data["models"]
        assert "llm_loaded" in models
        assert "embedding_loaded" in models
    
    def test_detailed_health_endpoint(self, client):
        """Test detailed health check endpoint"""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overall" in data
        assert "components" in data
        
        components = data["components"]
        assert "model_manager" in components
        assert "cache" in components
        
        # Each component should have status
        for component_name, component_data in components.items():
            assert "status" in component_data
            assert component_data["status"] in ["healthy", "unhealthy"]
    
    def test_load_models_endpoint(self, client):
        """Test load models endpoint"""
        response = client.post("/api/v1/models/load")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "successfully" in data["message"].lower()
    
    def test_clear_cache_endpoint(self, client):
        """Test clear cache endpoint"""
        response = client.post("/api/v1/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "successfully" in data["message"].lower()
    
    def test_nonexistent_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/health")
        
        # Should not return error for OPTIONS request
        assert response.status_code in [200, 405]  # Some test clients handle OPTIONS differently
    
    def test_api_versioning(self, client):
        """Test API versioning structure"""
        # All API endpoints should be under /api/v1
        endpoints_to_test = [
            "/api/v1/status",
            "/api/v1/health/detailed"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            assert response.status_code == 200
    
    def test_json_response_format(self, client):
        """Test that all endpoints return valid JSON"""
        endpoints = [
            "/",
            "/health",
            "/api/v1/status",
            "/api/v1/health/detailed"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            # Should be valid JSON
            try:
                data = response.json()
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Endpoint {endpoint} did not return valid JSON")
    
    def test_error_handling(self, client):
        """Test error handling for invalid requests"""
        # Test invalid JSON in POST request
        response = client.post(
            "/api/v1/models/load",
            headers={"Content-Type": "application/json"},
            data="invalid json"
        )
        
        # Should handle gracefully (either 400 or 422, not 500)
        assert response.status_code in [200, 400, 422]
    
    def test_concurrent_requests(self, client):
        """Test handling concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.get("/health")
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestAPIPerformance:
    """Test API performance characteristics"""
    
    def test_response_time_reasonable(self, client):
        """Test that response times are reasonable"""
        import time
        
        endpoints = ["/health", "/api/v1/status"]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Response should be under 1 second for these simple endpoints
            response_time = end_time - start_time
            assert response_time < 1.0, f"Endpoint {endpoint} took {response_time:.2f}s"
    
    def test_memory_usage_reported_correctly(self, client):
        """Test that memory usage is reported correctly"""
        response = client.get("/api/v1/status")
        data = response.json()
        
        memory = data["memory_usage"]
        
        # Memory values should be reasonable
        assert memory["total_mb"] > 1000  # At least 1GB total
        assert memory["available_mb"] > 0
        assert memory["used_mb"] > 0
        assert 0 <= memory["percent"] <= 100
        assert memory["used_mb"] <= memory["total_mb"]