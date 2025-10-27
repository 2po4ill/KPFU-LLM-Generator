#!/bin/bash

# KPFU LLM Generator Setup Script
# Sets up the complete hybrid infrastructure

set -e

echo "🚀 Setting up KPFU LLM Generator..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p app/models
mkdir -p app/cache
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/chromadb
mkdir -p data/ollama

# Set permissions
chmod -R 755 app/
chmod -R 755 data/

# Start infrastructure services first
echo "🐳 Starting infrastructure services..."
docker-compose up -d postgres redis chromadb

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check PostgreSQL
echo "🔍 Checking PostgreSQL connection..."
until docker-compose exec -T postgres pg_isready -U kpfu_user -d kpfu_generator; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Check Redis
echo "🔍 Checking Redis connection..."
until docker-compose exec -T redis redis-cli ping; do
    echo "Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Start Ollama and pull model
echo "🤖 Starting Ollama and pulling Llama 3.1 8B model..."
docker-compose up -d ollama

# Wait for Ollama to be ready
sleep 15

# Pull the required model
echo "📥 Pulling Llama 3.1 8B model (this may take a while)..."
docker-compose exec ollama ollama pull llama3.1:8b

echo "✅ Llama 3.1 8B model ready"

# Build and start the main application
echo "🏗️ Building and starting the main application..."
docker-compose up -d app

# Wait for application to be ready
echo "⏳ Waiting for application to start..."
sleep 20

# Check application health
echo "🔍 Checking application health..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Application is healthy"
else
    echo "⚠️ Application may still be starting up..."
fi

echo ""
echo "🎉 KPFU LLM Generator setup complete!"
echo ""
echo "📊 System Status:"
echo "  - Application: http://localhost:8080"
echo "  - Health Check: http://localhost:8080/health"
echo "  - API Status: http://localhost:8080/api/v1/status"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - ChromaDB: localhost:8000"
echo "  - Ollama: localhost:11434"
echo ""
echo "🔧 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
echo "🔄 To restart: docker-compose restart"
echo ""
echo "📚 Next steps:"
echo "  1. Check system status: curl http://localhost:8080/api/v1/status"
echo "  2. Load models manually: curl -X POST http://localhost:8080/api/v1/models/load"
echo "  3. Start implementing RPD processing (Task 2)"