"""
Dynamic model loading/unloading system for memory optimization
"""

import asyncio
import logging
import psutil
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import ollama
except ImportError:
    ollama = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except ImportError:
    torch = None

from core.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages dynamic loading/unloading of models to minimize memory usage"""
    
    def __init__(self, use_mock_services: bool = False):
        self.use_mock_services = use_mock_services
        self.llm_model: Optional[Any] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.model_last_used: Dict[str, datetime] = {}
        self.model_load_lock = asyncio.Lock()
        self.unload_timer_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the model manager"""
        logger.info("Initializing Model Manager...")
        
        if self.use_mock_services:
            logger.info("Using mock services for development")
            from core.mock_services import get_mock_services
            self.mock_services = get_mock_services()
        else:
            # Check if Ollama is available
            try:
                await self._check_ollama_connection()
                logger.info("Ollama connection verified")
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                raise
        
        # Pre-load embedding model (lightweight, always loaded)
        await self._load_embedding_model()
        
        # Start unload timer
        self.unload_timer_task = asyncio.create_task(self._unload_timer())
        
        logger.info("Model Manager initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.unload_timer_task:
            self.unload_timer_task.cancel()
        
        await self._unload_llm_model()
        await self._unload_embedding_model()
        
        logger.info("Model Manager cleanup complete")
    
    async def get_llm_model(self) -> Any:
        """Get LLM model, loading if necessary"""
        async with self.model_load_lock:
            if self.llm_model is None:
                await self._load_llm_model()
            
            self.model_last_used["llm"] = datetime.now()
            return self.llm_model
    
    async def get_embedding_model(self) -> SentenceTransformer:
        """Get embedding model (always loaded)"""
        if self.embedding_model is None:
            await self._load_embedding_model()
        
        self.model_last_used["embedding"] = datetime.now()
        return self.embedding_model
    
    async def _load_llm_model(self):
        """Load LLM model"""
        logger.info(f"Loading LLM model: {settings.llm_model}")
        
        if self.use_mock_services:
            self.llm_model = self.mock_services["ollama"]
            logger.info("Mock LLM model loaded")
            return
        
        if ollama is None:
            logger.error("Ollama not available, falling back to mock")
            self.llm_model = self.mock_services["ollama"]
            return
        
        # Check memory availability
        available_memory_mb = self._get_available_memory_mb()
        if available_memory_mb < settings.max_llm_memory:
            logger.warning(
                f"Low memory: {available_memory_mb}MB available, "
                f"{settings.max_llm_memory}MB required for LLM"
            )
        
        try:
            # Pull model if not available
            await self._ensure_ollama_model_available()
            
            # Initialize Ollama client
            self.llm_model = ollama.AsyncClient(host=settings.ollama_url)
            
            # Test model with a simple query
            await self._test_llm_model()
            
            logger.info(f"LLM model {settings.llm_model} loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            self.llm_model = None
            raise
    
    async def _load_embedding_model(self):
        """Load embedding model (lightweight, always loaded)"""
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        
        if self.use_mock_services or SentenceTransformer is None:
            self.embedding_model = self.mock_services["sentence_transformer"](
                settings.embedding_model, device="cpu"
            )
            logger.info("Mock embedding model loaded")
            return
        
        try:
            # Set device to CPU to save GPU memory for LLM
            device = 'cpu'
            
            self.embedding_model = SentenceTransformer(
                settings.embedding_model,
                device=device
            )
            
            # Test model
            test_embedding = self.embedding_model.encode("test sentence")
            logger.info(
                f"Embedding model loaded successfully. "
                f"Embedding dimension: {len(test_embedding)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
            raise
    
    async def _unload_llm_model(self):
        """Unload LLM model to free memory"""
        if self.llm_model is not None:
            logger.info("Unloading LLM model to free memory")
            self.llm_model = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear CUDA cache if available
            if torch and torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    async def _unload_embedding_model(self):
        """Unload embedding model"""
        if self.embedding_model is not None:
            logger.info("Unloading embedding model")
            self.embedding_model = None
            
            import gc
            gc.collect()
    
    async def _unload_timer(self):
        """Timer to unload unused models"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                now = datetime.now()
                unload_threshold = timedelta(minutes=10)  # Unload after 10 minutes of inactivity
                
                # Check if LLM should be unloaded
                if (self.llm_model is not None and 
                    "llm" in self.model_last_used and
                    now - self.model_last_used["llm"] > unload_threshold):
                    
                    logger.info("Unloading LLM model due to inactivity")
                    await self._unload_llm_model()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in unload timer: {e}")
    
    async def _check_ollama_connection(self):
        """Check if Ollama service is available"""
        if ollama is None:
            raise ConnectionError("Ollama library not available")
            
        try:
            client = ollama.AsyncClient(host=settings.ollama_url)
            models = await client.list()
            logger.info(f"Ollama connected. Available models: {len(models.get('models', []))}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama at {settings.ollama_url}: {e}")
    
    async def _ensure_ollama_model_available(self):
        """Ensure the required model is available in Ollama"""
        if ollama is None:
            raise RuntimeError("Ollama library not available")
            
        try:
            client = ollama.AsyncClient(host=settings.ollama_url)
            models = await client.list()
            
            available_models = [model['name'] for model in models.get('models', [])]
            
            if settings.llm_model not in available_models:
                logger.info(f"Pulling model {settings.llm_model}...")
                await client.pull(settings.llm_model)
                logger.info(f"Model {settings.llm_model} pulled successfully")
            else:
                logger.info(f"Model {settings.llm_model} already available")
                
        except Exception as e:
            raise RuntimeError(f"Failed to ensure model availability: {e}")
    
    async def _test_llm_model(self):
        """Test LLM model with a simple query"""
        try:
            response = await self.llm_model.generate(
                model=settings.llm_model,
                prompt="Привет! Ответь одним словом: работаю",
                options={
                    'num_predict': 10,
                    'temperature': 0.1
                }
            )
            
            if response and 'response' in response:
                logger.info("LLM model test successful")
            else:
                raise RuntimeError("LLM model test failed - no response")
                
        except Exception as e:
            raise RuntimeError(f"LLM model test failed: {e}")
    
    def _get_available_memory_mb(self) -> int:
        """Get available system memory in MB"""
        memory = psutil.virtual_memory()
        return int(memory.available / (1024 * 1024))
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        memory = psutil.virtual_memory()
        
        return {
            "total_mb": int(memory.total / (1024 * 1024)),
            "available_mb": int(memory.available / (1024 * 1024)),
            "used_mb": int(memory.used / (1024 * 1024)),
            "percent": memory.percent,
            "llm_loaded": self.llm_model is not None,
            "embedding_loaded": self.embedding_model is not None,
            "models_last_used": self.model_last_used
        }