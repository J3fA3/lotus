"""
Semantic RAG Service — Intelligence Flywheel

Local vector search over completed task case studies using
sentence-transformers (all-MiniLM-L6-v2) for embeddings and
numpy cosine similarity for search.

Index is stored as JSON at backend/.vector_index.json for simplicity.
No external vector database required.

Usage:
    from services.semantic_rag import get_rag_service
    rag = get_rag_service()
    results = rag.search("deployment pipeline issue", top_k=5)
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

CASE_STUDIES_DIR = Path(__file__).parent.parent / "case_studies"
INDEX_PATH = Path(__file__).parent.parent / ".vector_index.json"
MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticRAG:
    """Local semantic search over case study metadata."""

    def __init__(self):
        self._model = None
        self._index: List[dict] = []  # [{text, embedding, metadata}]
        self._load_index()

    def _load_model(self):
        """Lazy-load the sentence-transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(MODEL_NAME)
                logger.info(f"Loaded embedding model: {MODEL_NAME}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model

    def _load_index(self):
        """Load the vector index from disk."""
        if INDEX_PATH.exists():
            try:
                data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
                self._index = data.get("entries", [])
                logger.info(f"Loaded {len(self._index)} entries from vector index")
            except Exception as e:
                logger.warning(f"Failed to load vector index: {e}")
                self._index = []
        else:
            self._index = []

    def _save_index(self):
        """Save the vector index to disk."""
        data = {"entries": self._index}
        INDEX_PATH.write_text(json.dumps(data), encoding="utf-8")
        logger.info(f"Saved {len(self._index)} entries to vector index")

    def build_index(self) -> int:
        """Rebuild the entire index from all case studies on disk.

        Returns:
            Number of case studies indexed
        """
        self._index = []

        if not CASE_STUDIES_DIR.exists():
            logger.info("No case_studies directory found — index empty")
            self._save_index()
            return 0

        model = self._load_model()
        count = 0

        for metadata_path in sorted(CASE_STUDIES_DIR.glob("*/metadata.json")):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                text = metadata.get("indexed_text", "")
                if not text.strip():
                    continue

                embedding = model.encode(text).tolist()
                self._index.append({
                    "text": text,
                    "embedding": embedding,
                    "metadata": {
                        "slug": metadata.get("slug"),
                        "title": metadata.get("title"),
                        "description": metadata.get("description", ""),
                        "notes": metadata.get("notes", ""),
                        "assignee": metadata.get("assignee"),
                        "value_stream": metadata.get("value_stream"),
                        "completed_at": metadata.get("completed_at"),
                        "case_dir": str(metadata_path.parent),
                    },
                })
                count += 1
            except Exception as e:
                logger.warning(f"Failed to index {metadata_path}: {e}")

        self._save_index()
        logger.info(f"Built index with {count} case studies")
        return count

    def add_to_index(self, case_dir: str):
        """Add a single case study to the index.

        Args:
            case_dir: Path to the case study directory
        """
        metadata_path = Path(case_dir) / "metadata.json"
        if not metadata_path.exists():
            logger.warning(f"No metadata.json in {case_dir}")
            return

        try:
            model = self._load_model()
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            text = metadata.get("indexed_text", "")
            if not text.strip():
                return

            embedding = model.encode(text).tolist()
            self._index.append({
                "text": text,
                "embedding": embedding,
                "metadata": {
                    "slug": metadata.get("slug"),
                    "title": metadata.get("title"),
                    "description": metadata.get("description", ""),
                    "notes": metadata.get("notes", ""),
                    "assignee": metadata.get("assignee"),
                    "value_stream": metadata.get("value_stream"),
                    "completed_at": metadata.get("completed_at"),
                    "case_dir": case_dir,
                },
            })
            self._save_index()
            logger.info(f"Added to index: {metadata.get('slug')}")
        except Exception as e:
            logger.warning(f"Failed to add {case_dir} to index: {e}")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[dict, float]]:
        """Search the index for case studies similar to the query.

        Args:
            query: Natural language search query
            top_k: Maximum results to return

        Returns:
            List of (entry, similarity_score) tuples, highest first
        """
        if not self._index:
            return []

        try:
            model = self._load_model()
            query_embedding = model.encode(query)

            results = []
            for entry in self._index:
                entry_embedding = np.array(entry["embedding"])
                # Cosine similarity
                dot = np.dot(query_embedding, entry_embedding)
                norm = np.linalg.norm(query_embedding) * np.linalg.norm(entry_embedding)
                similarity = float(dot / norm) if norm > 0 else 0.0
                results.append((entry, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


# Singleton
_rag_service: Optional[SemanticRAG] = None


def get_rag_service() -> SemanticRAG:
    global _rag_service
    if _rag_service is None:
        _rag_service = SemanticRAG()
    return _rag_service
