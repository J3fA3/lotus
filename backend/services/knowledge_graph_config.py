"""
Knowledge Graph Advanced Features - Configuration

This module contains configuration for advanced knowledge graph features:
- Confidence decay parameters
- Embedding model settings
- GraphQL settings
"""

from typing import Dict, Any
import os


class KnowledgeGraphConfig:
    """Configuration for knowledge graph advanced features."""

    # ========================================================================
    # CONFIDENCE DECAY SETTINGS
    # ========================================================================

    # Decay enabled by default
    DECAY_ENABLED = os.getenv("KG_DECAY_ENABLED", "true").lower() == "true"

    # Half-life in days (relationship strength halves after this many days)
    # Default: 90 days (3 months)
    DECAY_HALF_LIFE_DAYS = float(os.getenv("KG_DECAY_HALF_LIFE", "90"))

    # Minimum strength threshold (relationships below this are marked as stale)
    # Default: 0.1 (10%)
    DECAY_MIN_STRENGTH = float(os.getenv("KG_DECAY_MIN_STRENGTH", "0.1"))

    # How often to run decay update task (in hours)
    # Default: 24 hours (daily)
    DECAY_UPDATE_INTERVAL_HOURS = int(os.getenv("KG_DECAY_UPDATE_INTERVAL", "24"))

    # Apply decay to nodes as well (mention count decay)
    # Default: False (only edges decay)
    DECAY_NODES_ENABLED = os.getenv("KG_DECAY_NODES", "false").lower() == "true"

    # Node mention count half-life (separate from edge strength)
    # Default: 180 days (6 months)
    DECAY_NODE_HALF_LIFE_DAYS = float(os.getenv("KG_DECAY_NODE_HALF_LIFE", "180"))

    # ========================================================================
    # SEMANTIC SIMILARITY SETTINGS
    # ========================================================================

    # Embedding model to use
    # Options:
    # - "all-MiniLM-L6-v2" (fast, 384 dims, 80MB)
    # - "all-mpnet-base-v2" (better quality, 768 dims, 420MB)
    # - "paraphrase-multilingual-MiniLM-L12-v2" (multilingual, 384 dims)
    EMBEDDING_MODEL = os.getenv("KG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Semantic similarity threshold for entity matching
    # Default: 0.70 (70% similarity)
    SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("KG_SEMANTIC_THRESHOLD", "0.70"))

    # Enable semantic similarity (requires sentence-transformers)
    SEMANTIC_ENABLED = os.getenv("KG_SEMANTIC_ENABLED", "true").lower() == "true"

    # Cache embeddings in memory
    EMBEDDING_CACHE_ENABLED = True
    EMBEDDING_CACHE_SIZE = 1000  # Max cached embeddings

    # ========================================================================
    # GRAPHQL SETTINGS
    # ========================================================================

    # Enable GraphQL API
    GRAPHQL_ENABLED = os.getenv("KG_GRAPHQL_ENABLED", "true").lower() == "true"

    # GraphQL endpoint path
    GRAPHQL_PATH = "/graphql"

    # Enable GraphQL playground/IDE
    GRAPHQL_PLAYGROUND_ENABLED = os.getenv("KG_GRAPHQL_PLAYGROUND", "true").lower() == "true"

    # Max query depth (prevent deep nested queries)
    GRAPHQL_MAX_DEPTH = int(os.getenv("KG_GRAPHQL_MAX_DEPTH", "10"))

    # Max query complexity
    GRAPHQL_MAX_COMPLEXITY = int(os.getenv("KG_GRAPHQL_MAX_COMPLEXITY", "1000"))

    # ========================================================================
    # GENERAL SETTINGS
    # ========================================================================

    @classmethod
    def get_decay_config(cls) -> Dict[str, Any]:
        """Get all decay-related configuration."""
        return {
            "enabled": cls.DECAY_ENABLED,
            "half_life_days": cls.DECAY_HALF_LIFE_DAYS,
            "min_strength": cls.DECAY_MIN_STRENGTH,
            "update_interval_hours": cls.DECAY_UPDATE_INTERVAL_HOURS,
            "nodes_enabled": cls.DECAY_NODES_ENABLED,
            "node_half_life_days": cls.DECAY_NODE_HALF_LIFE_DAYS,
        }

    @classmethod
    def get_semantic_config(cls) -> Dict[str, Any]:
        """Get all semantic similarity configuration."""
        return {
            "enabled": cls.SEMANTIC_ENABLED,
            "model": cls.EMBEDDING_MODEL,
            "threshold": cls.SEMANTIC_SIMILARITY_THRESHOLD,
            "cache_enabled": cls.EMBEDDING_CACHE_ENABLED,
            "cache_size": cls.EMBEDDING_CACHE_SIZE,
        }

    @classmethod
    def get_graphql_config(cls) -> Dict[str, Any]:
        """Get all GraphQL configuration."""
        return {
            "enabled": cls.GRAPHQL_ENABLED,
            "path": cls.GRAPHQL_PATH,
            "playground_enabled": cls.GRAPHQL_PLAYGROUND_ENABLED,
            "max_depth": cls.GRAPHQL_MAX_DEPTH,
            "max_complexity": cls.GRAPHQL_MAX_COMPLEXITY,
        }


# Singleton config instance
config = KnowledgeGraphConfig()
