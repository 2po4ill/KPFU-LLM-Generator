# Development Guide

## Quick Start

### Setup
```cmd
setup_local.bat    # Install dependencies
run_dev.bat        # Start development server
```

### Verify Installation
```cmd
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/status
```

## Environment Variables

Copy `.env.example` to `.env` and modify as needed:

```env
# Development mode (uses mock services)
USE_MOCK_SERVICES=true

# Database (optional in mock mode)
DATABASE_URL=postgresql://kpfu_user:kpfu_password@localhost:5432/kpfu_generator

# Services (optional in mock mode)
REDIS_URL=redis://localhost:6379
CHROMADB_URL=http://localhost:8000
OLLAMA_URL=http://localhost:11434
```

## Development vs Production

### Development Mode (Default)
- Uses mock services (no external dependencies)
- Fast startup (~200MB RAM)
- Perfect for coding and testing

### Production Mode
- Requires Docker Desktop
- Full services (PostgreSQL, Redis, ChromaDB, Ollama)
- Higher resource usage (~5GB RAM)

## Common Issues

### Python not found
```cmd
# Install Python 3.11+ from python.org
# Make sure to check "Add to PATH"
```

### Port already in use
```cmd
# Check what's using port 8080
netstat -an | findstr :8080
```

### Reset everything
```cmd
# Remove virtual environment and start fresh
rmdir /s /q venv
setup_local.bat
```

## Project Structure

```
app/
├── core/
│   ├── config.py          # Configuration settings
│   ├── database.py        # Database models
│   ├── model_manager.py   # LLM management
│   ├── cache.py          # Caching system
│   └── mock_services.py  # Development mocks
├── api/
│   └── routes.py         # API endpoints
└── main.py              # Application entry point
```

## Testing

### Run Tests
```cmd
run_all_tests.bat      # Comprehensive test suite
test.bat               # Interactive test menu
pytest tests/ -v       # Quick test run
```

### Test Structure
- **Unit Tests**: Individual component testing
- **Integration Tests**: System interaction testing
- **API Tests**: Endpoint functionality testing
- **Coverage Target**: 90%+

See `tests/README.md` for detailed testing documentation.

## Next Tasks

1. **Task 2**: RPD processing system
2. **Task 3**: Literature validation
3. **Task 4**: Content generation pipeline