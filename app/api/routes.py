"""
API routes for KPFU LLM Generator
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from core.model_manager import ModelManager
from core.cache import cache_manager
from .rpd_routes import router as rpd_router

router = APIRouter()

# Include RPD processing routes
router.include_router(rpd_router)


async def get_model_manager() -> ModelManager:
    """Dependency to get model manager"""
    from main import app
    return app.state.model_manager


@router.get("/status")
async def get_system_status(model_manager: ModelManager = Depends(get_model_manager)):
    """Get system status and resource usage"""
    try:
        memory_usage = model_manager.get_memory_usage()
        cache_stats = await cache_manager.get_cache_stats()
        
        return {
            "status": "operational",
            "memory_usage": memory_usage,
            "cache_stats": cache_stats,
            "models": {
                "llm_loaded": memory_usage["llm_loaded"],
                "embedding_loaded": memory_usage["embedding_loaded"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )


@router.post("/models/load")
async def load_models(model_manager: ModelManager = Depends(get_model_manager)):
    """Manually load models"""
    try:
        # Load LLM model
        await model_manager.get_llm_model()
        
        # Load embedding model (should already be loaded)
        await model_manager.get_embedding_model()
        
        return {"message": "Models loaded successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load models: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    try:
        await cache_manager.invalidate_pattern("")
        return {"message": "Cache cleared successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/health/detailed")
async def detailed_health_check(model_manager: ModelManager = Depends(get_model_manager)):
    """Detailed health check with component status"""
    health_status = {
        "overall": "healthy",
        "components": {}
    }
    
    # Check model manager
    try:
        memory_usage = model_manager.get_memory_usage()
        health_status["components"]["model_manager"] = {
            "status": "healthy",
            "memory_usage_mb": memory_usage["used_mb"],
            "memory_percent": memory_usage["percent"]
        }
    except Exception as e:
        health_status["components"]["model_manager"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall"] = "degraded"
    
    # Check cache
    try:
        cache_stats = await cache_manager.get_cache_stats()
        health_status["components"]["cache"] = {
            "status": "healthy",
            "redis_connected": cache_stats["redis_connected"],
            "memory_cache_size": cache_stats["memory_cache_size"]
        }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall"] = "degraded"
    
    return health_status