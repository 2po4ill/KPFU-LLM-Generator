# KPFU LLM Educational Content Generator

A hybrid literature-grounded content generation system that creates verified educational materials (lectures and lab works) for KPFU professors using RPD curriculum files and the university's library database.

## 🚀 Quick Start

### Local Development (Recommended)
```cmd
setup_local.bat
run_dev.bat
```
**Requirements:** Python 3.11+, 4GB+ RAM

### Docker Setup (Production)
```cmd
scripts\setup.bat
```
**Requirements:** Docker Desktop, 8GB+ RAM

## 🏗️ Architecture

### Components
- **PostgreSQL**: Metadata and citations
- **Redis**: Multi-layer caching
- **ChromaDB**: Vector database for embeddings
- **Ollama**: LLM service (Llama 3.1 8B)
- **SentenceTransformer**: Semantic validation (118MB)

### Performance
- **Processing Time**: 1.5-2 minutes per lecture
- **Memory Usage**: 5GB peak, 200MB idle
- **Concurrent Users**: 10+ supported

## 🌐 API Endpoints

- **Health**: `GET /health`
- **Status**: `GET /api/v1/status`
- **Load Models**: `POST /api/v1/models/load`
- **Clear Cache**: `POST /api/v1/cache/clear`
- **Detailed Health**: `GET /api/v1/health/detailed`

## 📁 Project Structure

```
kpfu-llm-generator/
├── app/                    # Main application
│   ├── core/              # Core components
│   ├── api/               # API routes
│   └── main.py           # Application entry point
├── database/              # Database initialization
├── scripts/              # Setup scripts
├── docker-compose.yml    # Container orchestration
└── requirements.txt      # Python dependencies
```

## 🔧 Development

### Local Development
```cmd
setup_local.bat
run_dev.bat
```

### Docker Development
```cmd
docker-compose up -d
```

### Check Status
```cmd
curl http://localhost:8080/health
```

### Run Tests
```cmd
run_all_tests.bat    # Comprehensive test suite
test.bat             # Interactive test menu
```

## 📄 License

This project is developed for Kazan Federal University (KPFU) educational purposes.
