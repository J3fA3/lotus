"""
Knowledge Graph Embeddings Service

Provides semantic similarity matching using sentence transformers.
Generates and caches embeddings for entities to enable better matching.
"""

from typing import List, Optional, Dict, Tuple
import numpy as np
from functools import lru_cache
import logging

from services.knowledge_graph_config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy import sentence transformers (only if enabled)
if config.SEMANTIC_ENABLED:
    try:
        from sentence_transformers import SentenceTransformer
        SENTENCE_TRANSFORMERS_AVAILABLE = True
    except ImportError:
        logger.warning(
            "sentence-transformers not installed. "
            "Semantic similarity will be disabled. "
            "Install with: pip install sentence-transformers"
        )
        SENTENCE_TRANSFORMERS_AVAILABLE = False
else:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingService:
    """Service for generating and matching embeddings."""

    def __init__(self):
        self.model = None
        self.cache = {}  # In-memory cache for embeddings
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        if not config.SEMANTIC_ENABLED:
            logger.info("Semantic similarity disabled in config")
            return

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available")
            return

        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            self.model = None

    def is_available(self) -> bool:
        """Check if embedding service is available."""
        return self.model is not None

    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for a text string.

        Args:
            text: Input text

        Returns:
            Numpy array of embedding vector, or None if not available
        """
        if not self.is_available():
            return None

        # Check cache
        if config.EMBEDDING_CACHE_ENABLED and text in self.cache:
            return self.cache[text]

        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)

            # Cache if enabled
            if config.EMBEDDING_CACHE_ENABLED:
                if len(self.cache) >= config.EMBEDDING_CACHE_SIZE:
                    # Remove oldest entry (FIFO)
                    self.cache.pop(next(iter(self.cache)))
                self.cache[text] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None

    def calculate_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Ensure result is in [0, 1] range
        # (cosine similarity is in [-1, 1], but we expect positive embeddings)
        return float(max(0.0, min(1.0, similarity)))

    def calculate_text_similarity(
        self,
        text1: str,
        text2: str
    ) -> Optional[float]:
        """Calculate semantic similarity between two text strings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0), or None if not available
        """
        if not self.is_available():
            return None

        emb1 = self.generate_embedding(text1)
        emb2 = self.generate_embedding(text2)

        if emb1 is None or emb2 is None:
            return None

        return self.calculate_similarity(emb1, emb2)

    def find_similar_texts(
        self,
        query_text: str,
        candidate_texts: List[str],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """Find most similar texts from a list of candidates.

        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            top_k: Return top K most similar
            threshold: Minimum similarity threshold

        Returns:
            List of (text, similarity) tuples, sorted by similarity descending
        """
        if not self.is_available():
            return []

        if threshold is None:
            threshold = config.SEMANTIC_SIMILARITY_THRESHOLD

        # Generate query embedding
        query_emb = self.generate_embedding(query_text)
        if query_emb is None:
            return []

        # Calculate similarities
        similarities = []
        for candidate in candidate_texts:
            candidate_emb = self.generate_embedding(candidate)
            if candidate_emb is None:
                continue

            similarity = self.calculate_similarity(query_emb, candidate_emb)

            if similarity >= threshold:
                similarities.append((candidate, similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        return similarities[:top_k]

    def embedding_to_bytes(self, embedding: np.ndarray) -> bytes:
        """Convert embedding numpy array to bytes for storage.

        Args:
            embedding: Numpy array

        Returns:
            Bytes representation
        """
        return embedding.tobytes()

    def bytes_to_embedding(
        self,
        embedding_bytes: bytes,
        dtype=np.float32
    ) -> np.ndarray:
        """Convert bytes back to embedding numpy array.

        Args:
            embedding_bytes: Bytes representation
            dtype: Numpy data type

        Returns:
            Numpy array
        """
        return np.frombuffer(embedding_bytes, dtype=dtype)

    def get_embedding_dimension(self) -> Optional[int]:
        """Get the dimension of embeddings from this model.

        Returns:
            Embedding dimension, or None if not available
        """
        if not self.is_available():
            return None

        return self.model.get_sentence_embedding_dimension()

    def clear_cache(self):
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dict with cache size and other stats
        """
        return {
            "cache_size": len(self.cache),
            "cache_enabled": config.EMBEDDING_CACHE_ENABLED,
            "max_cache_size": config.EMBEDDING_CACHE_SIZE,
            "model": config.EMBEDDING_MODEL,
            "embedding_dim": self.get_embedding_dimension(),
            "is_available": self.is_available()
        }


# Singleton embedding service instance
embedding_service = EmbeddingService()
