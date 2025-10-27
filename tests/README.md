# KPFU LLM Generator - Test Suite

## Overview

Comprehensive test suite covering all components of the KPFU LLM Generator system.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_config.py           # Configuration module tests
├── test_mock_services.py    # Mock services tests
├── test_cache.py            # Cache system tests
├── test_model_manager.py    # Model manager tests
├── test_database.py         # Database models tests
├── test_api.py              # API endpoints tests
└── test_integration.py      # Integration tests
```

## Running Tests

### Quick Test Run
```cmd
run_tests.bat
```

### Manual Test Commands
```cmd
# Activate environment
venv\Scripts\activate.bat

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only unit tests
pytest tests/ -m "not integration" -v

# Run only integration tests
pytest tests/ -m integration -v
```

## Test Categories

### Unit Tests
- **Configuration**: Settings validation and environment handling
- **Mock Services**: Redis, Ollama, ChromaDB, SentenceTransformer mocks
- **Cache Manager**: Multi-layer caching functionality
- **Model Manager**: Dynamic model loading/unloading
- **Database Models**: SQLAlchemy model definitions and relationships

### Integration Tests
- **API Endpoints**: FastAPI route testing
- **System Integration**: Component interaction testing
- **Async Operations**: Concurrent operation testing
- **Error Handling**: Resilience and recovery testing

### Performance Tests
- **Response Times**: API endpoint performance
- **Memory Usage**: Memory consumption validation
- **Concurrent Load**: Multi-user scenario testing

## Test Coverage

Target coverage: **90%+**

### Covered Components
- ✅ Configuration system
- ✅ Mock services (development mode)
- ✅ Cache management (Redis + memory)
- ✅ Model management (dynamic loading)
- ✅ Database models and relationships
- ✅ API endpoints and error handling
- ✅ System integration scenarios

### Coverage Reports
- **Terminal**: Shows missing lines
- **HTML**: Detailed coverage report in `htmlcov/index.html`

## Test Environment

### Automatic Setup
- Uses mock services by default
- In-memory SQLite for database tests
- Isolated test environment
- Automatic cleanup after tests

### Environment Variables
```env
USE_MOCK_SERVICES=true
DATABASE_URL=sqlite:///./test.db
PYTHONPATH=%CD%
```

## Test Fixtures

### Global Fixtures (conftest.py)
- `client`: FastAPI test client
- `mock_services`: Mock service instances
- `model_manager`: Model manager with mocks
- `cache_manager_fixture`: Cache manager instance
- `setup_test_environment`: Test environment setup

### Database Fixtures
- `engine`: In-memory SQLite engine
- `session`: Database session for testing

## Writing New Tests

### Test File Naming
- `test_*.py` for test files
- `Test*` for test classes
- `test_*` for test functions

### Example Test Structure
```python
class TestNewComponent:
    """Test new component functionality"""
    
    @pytest.fixture
    def component(self):
        """Create component for testing"""
        return NewComponent()
    
    def test_basic_functionality(self, component):
        """Test basic functionality"""
        result = component.do_something()
        assert result is not None
    
    async def test_async_functionality(self, component):
        """Test async functionality"""
        result = await component.do_async_something()
        assert result == expected_value
```

### Test Markers
```python
@pytest.mark.unit
def test_unit_functionality():
    """Unit test"""
    pass

@pytest.mark.integration
def test_integration_scenario():
    """Integration test"""
    pass

@pytest.mark.slow
def test_performance_scenario():
    """Slow/performance test"""
    pass
```

## Continuous Integration

### Pre-commit Checks
```cmd
# Run tests before committing
run_tests.bat

# Check coverage
pytest tests/ --cov=app --cov-fail-under=90
```

### Test Automation
- All tests run in mock mode (no external dependencies)
- Fast execution (< 30 seconds for full suite)
- Comprehensive coverage of critical paths
- Automatic cleanup and isolation

## Troubleshooting

### Common Issues

**Import Errors**:
```cmd
set PYTHONPATH=%CD%
```

**Database Errors**:
- Tests use in-memory SQLite
- Automatic cleanup after each test

**Async Test Issues**:
- Use `pytest-asyncio` plugin
- Mark async tests with `async def`

**Mock Service Issues**:
- Ensure `USE_MOCK_SERVICES=true`
- Check mock service implementations

### Debug Mode
```cmd
# Run with verbose output
pytest tests/ -v -s

# Run single test with debugging
pytest tests/test_api.py::TestAPIEndpoints::test_health_endpoint -v -s

# Run with pdb on failure
pytest tests/ --pdb
```

## Test Quality Standards

### Requirements
- **Coverage**: Minimum 90% line coverage
- **Performance**: All tests complete in < 30 seconds
- **Isolation**: No test dependencies on external services
- **Reliability**: Tests pass consistently
- **Documentation**: Clear test descriptions and assertions

### Best Practices
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Use appropriate fixtures
- Clean up resources after tests
- Test edge cases and error conditions