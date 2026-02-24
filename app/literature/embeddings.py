"""
Embedding generation and vector storage using SentenceTransformers and FAISS
"""

import logging
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings and manage vector storage with FAISS"""
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.model = None
        self.index = None
        self.chunk_metadata = []  # Store metadata for each vector
        
        # Model will be loaded from ModelManager
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        self.embedding_dim = 384  # Dimension for MiniLM model
        
        # Storage paths
        self.cache_dir = Path("app/cache/faiss")
        self.index_path = self.cache_dir / "book_chunks.index"
        self.metadata_path = self.cache_dir / "chunk_metadata.pkl"
    
    async def initialize(self, model_manager=None):
        """Initialize embedding model and FAISS index"""
        try:
            if self.use_mock:
                logger.info("Using mock embedding service")
                return
            
            # Create cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Get embedding model from ModelManager
            if model_manager:
                self.model = await model_manager.get_embedding_model()
                logger.info(f"Loaded embedding model: {self.model_name}")
            
            # Initialize or load FAISS index
            if self.index_path.exists():
                # Load existing index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load metadata
                if self.metadata_path.exists():
                    with open(self.metadata_path, 'rb') as f:
                        self.chunk_metadata = pickle.load(f)
                
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index (using L2 distance)
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                logger.info("Created new FAISS index")
            
        except Exception as e:
            logger.error(f"Error initializing embedding service: {e}")
            logger.info("Falling back to mock mode")
            self.use_mock = True
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embedding vectors
        """
        if self.use_mock:
            # Return mock embeddings
            import random
            return np.array([[random.random() for _ in range(self.embedding_dim)] for _ in texts], dtype=np.float32)
        
        try:
            embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])
    
    def add_chunks_to_vector_store(
        self,
        chunks: List[Any],
        book_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add book chunks to FAISS vector store
        
        Args:
            chunks: List of BookChunk objects
            book_metadata: Book metadata (title, authors, etc.)
            
        Returns:
            Result dictionary
        """
        try:
            if self.use_mock:
                logger.info(f"Mock: Would add {len(chunks)} chunks to vector store")
                return {
                    'success': True,
                    'chunks_added': len(chunks),
                    'mock': True
                }
            
            # Prepare chunk texts
            chunk_texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embeddings = self.generate_embeddings(chunk_texts)
            
            if len(embeddings) == 0:
                raise Exception("Failed to generate embeddings")
            
            # Add to FAISS index
            logger.info(f"Adding {len(chunks)} chunks to FAISS index...")
            self.index.add(embeddings)
            
            # Store metadata for each chunk
            for chunk in chunks:
                self.chunk_metadata.append({
                    'chunk_id': chunk.chunk_id,
                    'book_id': chunk.book_id,
                    'page_number': chunk.page_number,
                    'char_count': chunk.char_count,
                    'content': chunk.content,
                    'book_title': book_metadata.get('title', ''),
                    'book_authors': book_metadata.get('authors', '')
                })
            
            # Save index and metadata to disk
            self._save_index()
            
            logger.info(f"Successfully added {len(chunks)} chunks to vector store")
            
            return {
                'success': True,
                'chunks_added': len(chunks),
                'total_chunks_in_store': self.index.ntotal
            }
            
        except Exception as e:
            logger.error(f"Error adding chunks to vector store: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_similar_chunks(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using semantic search
        
        Args:
            query: Search query
            book_id: Optional filter by book ID
            top_k: Number of results to return
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            if self.use_mock:
                logger.info(f"Mock: Would search for '{query}'")
                return []
            
            if self.index.ntotal == 0:
                logger.warning("FAISS index is empty")
                return []
            
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])
            
            # Search in FAISS
            distances, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))
            
            # Format results and apply book_id filter if needed
            similar_chunks = []
            for i, idx in enumerate(indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                metadata = self.chunk_metadata[idx]
                
                # Apply book_id filter
                if book_id and metadata['book_id'] != book_id:
                    continue
                
                similar_chunks.append({
                    'chunk_id': metadata['chunk_id'],
                    'content': metadata['content'],
                    'metadata': {
                        'book_id': metadata['book_id'],
                        'page_number': metadata['page_number'],
                        'char_count': metadata['char_count'],
                        'book_title': metadata['book_title'],
                        'book_authors': metadata['book_authors']
                    },
                    'distance': float(distances[0][i])
                })
                
                if len(similar_chunks) >= top_k:
                    break
            
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def get_book_chunks(self, book_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific book
        
        Args:
            book_id: Book identifier
            
        Returns:
            List of chunks
        """
        try:
            if self.use_mock:
                return []
            
            chunks = []
            for metadata in self.chunk_metadata:
                if metadata['book_id'] == book_id:
                    chunks.append({
                        'chunk_id': metadata['chunk_id'],
                        'content': metadata['content'],
                        'metadata': {
                            'book_id': metadata['book_id'],
                            'page_number': metadata['page_number'],
                            'char_count': metadata['char_count'],
                            'book_title': metadata['book_title'],
                            'book_authors': metadata['book_authors']
                        }
                    })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting book chunks: {e}")
            return []
    
    def delete_book_chunks(self, book_id: str) -> Dict[str, Any]:
        """
        Delete all chunks for a specific book
        Note: FAISS doesn't support deletion, so we rebuild the index
        
        Args:
            book_id: Book identifier
            
        Returns:
            Result dictionary
        """
        try:
            if self.use_mock:
                return {'success': True, 'mock': True}
            
            # Filter out chunks for this book
            old_count = len(self.chunk_metadata)
            remaining_metadata = [m for m in self.chunk_metadata if m['book_id'] != book_id]
            deleted_count = old_count - len(remaining_metadata)
            
            if deleted_count == 0:
                return {
                    'success': True,
                    'chunks_deleted': 0,
                    'message': 'No chunks found for this book'
                }
            
            # Rebuild index with remaining chunks
            logger.info(f"Rebuilding FAISS index after deleting {deleted_count} chunks...")
            
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.chunk_metadata = []
            
            if remaining_metadata:
                # Re-generate embeddings for remaining chunks
                remaining_texts = [m['content'] for m in remaining_metadata]
                embeddings = self.generate_embeddings(remaining_texts)
                self.index.add(embeddings)
                self.chunk_metadata = remaining_metadata
            
            # Save updated index
            self._save_index()
            
            logger.info(f"Deleted {deleted_count} chunks for book {book_id}")
            
            return {
                'success': True,
                'chunks_deleted': deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error deleting book chunks: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            faiss.write_index(self.index, str(self.index_path))
            
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.chunk_metadata, f)
            
            logger.debug("Saved FAISS index and metadata")
            
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up embedding service")
        if not self.use_mock and self.index is not None:
            self._save_index()


# Global embedding service instance
embedding_service = None


async def get_embedding_service(model_manager=None, use_mock: bool = False) -> EmbeddingService:
    """Get global embedding service instance"""
    global embedding_service
    
    if embedding_service is None:
        embedding_service = EmbeddingService(use_mock=use_mock)
        await embedding_service.initialize(model_manager)
    
    return embedding_service
