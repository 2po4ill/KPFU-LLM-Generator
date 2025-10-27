"""
KPFU LLM Educational Content Generator - Main Application
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.model_manager import ModelManager
from core.cache import cache_manager
from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global model manager instance
model_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global model_manager
    
    logger.info("Starting KPFU LLM Generator...")
    
    # Check if running in development mode (without Docker)
    use_mock_services = os.getenv("USE_MOCK_SERVICES", "false").lower() == "true"
    
    if use_mock_services:
        logger.info("Running in development mode with mock services")
    
    try:
        # Initialize database (skip if using mock services)
        if not use_mock_services:
            from core.database import init_db
            await init_db()
        
        # Initialize cache manager
        await cache_manager.initialize()
        
        # Initialize model manager
        model_manager = ModelManager(use_mock_services=use_mock_services)
        await model_manager.initialize()
        
        # Store model manager in app state
        app.state.model_manager = model_manager
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        logger.info("Falling back to mock services for development")
        
        # Fallback to mock services
        await cache_manager.initialize()
        model_manager = ModelManager(use_mock_services=True)
        await model_manager.initialize()
        app.state.model_manager = model_manager
        
        logger.info("Application startup complete (mock mode)")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    if model_manager:
        await model_manager.cleanup()
    await cache_manager.cleanup()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="KPFU LLM Educational Content Generator",
    description="Hybrid literature-grounded content generation system for KPFU",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KPFU LLM Educational Content Generator",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    use_mock = os.getenv("USE_MOCK_SERVICES", "false").lower() == "true"
    mode = "mock" if use_mock else "production"
    
    return {
        "status": "healthy",
        "mode": mode,
        "database": "mock" if use_mock else "connected",
        "redis": "mock" if use_mock else "connected", 
        "chromadb": "mock" if use_mock else "connected",
        "ollama": "mock" if use_mock else "connected"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )