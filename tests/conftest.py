"""
Pytest configuration and fixtures for KPFU LLM Generator tests
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient

# Set test environment
os.environ["USE_MOCK_SERVICES"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# Add app directory to Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import app
from core.model_manager import ModelManager
from core.cache import cache_manager
from core.mock_services import get_mock_services


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def mock_services():
    """Get mock services for testing"""
    return get_mock_services()


@pytest.fixture
async def model_manager():
    """Create a model manager with mock services for testing"""
    manager = ModelManager(use_mock_services=True)
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.fixture
async def cache_manager_fixture():
    """Create a cache manager for testing"""
    await cache_manager.initialize()
    yield cache_manager
    await cache_manager.cleanup()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Clear any existing cache if available
    try:
        cache_manager.memory_cache.clear()
    except:
        pass
    yield
    # Cleanup after test
    try:
        cache_manager.memory_cache.clear()
    except:
        pass


class AsyncTestCase:
    """Base class for async test cases"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup method for each test"""
        pass