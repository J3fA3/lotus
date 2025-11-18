"""
Knowledge Base Integration

Manages document context and provides:
- Document indexing for AI context
- Full-text search capabilities
- Document summarization
- Context retrieval for task extraction
"""
import asyncio
import re
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from db.models import Document


class KnowledgeBase:
    """
    Manage document knowledge base for AI context

    Provides document indexing, search, and context retrieval.
    """

    def __init__(self):
        """Initialize knowledge base"""
        pass

    @staticmethod
    async def index_document(
        db: AsyncSession,
        document_id: str,
        extracted_text: str
    ) -> bool:
        """
        Index document for search and retrieval

        Args:
            db: Database session
            document_id: Document ID
            extracted_text: Extracted text content

        Returns:
            True if successful
        """
        try:
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()

            if not doc:
                return False

            # Update extracted text and preview
            doc.extracted_text = extracted_text
            doc.text_preview = extracted_text[:500] if extracted_text else None
            doc.updated_at = datetime.utcnow()

            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            print(f"Failed to index document: {e}")
            return False

    @staticmethod
    async def search_documents(
        db: AsyncSession,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Document]:
        """
        Search documents by text content

        Args:
            db: Database session
            query: Search query
            category: Optional category filter
            limit: Maximum results to return

        Returns:
            List of matching documents
        """
        try:
            # Build search query
            # Note: This is a simple LIKE search. For production, consider
            # using full-text search extensions like FTS5 for SQLite
            search_pattern = f"%{query}%"

            stmt = select(Document).where(
                or_(
                    Document.extracted_text.like(search_pattern),
                    Document.original_filename.like(search_pattern),
                    Document.text_preview.like(search_pattern)
                )
            )

            if category:
                stmt = stmt.where(Document.category == category)

            stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            documents = result.scalars().all()

            return list(documents)

        except Exception as e:
            print(f"Document search failed: {e}")
            return []

    @staticmethod
    async def get_document_context(
        db: AsyncSession,
        document_ids: List[str],
        max_chars: int = 10000
    ) -> str:
        """
        Get combined context from multiple documents

        Args:
            db: Database session
            document_ids: List of document IDs
            max_chars: Maximum characters to return

        Returns:
            Combined document text
        """
        try:
            result = await db.execute(
                select(Document).where(Document.id.in_(document_ids))
            )
            documents = result.scalars().all()

            context_parts = []
            total_chars = 0

            for doc in documents:
                if total_chars >= max_chars:
                    break

                header = f"\n\n=== Document: {doc.original_filename} ===\n"
                content = doc.extracted_text or ""

                # Calculate how much content we can add
                available = max_chars - total_chars - len(header)
                if available > 0:
                    context_parts.append(header)
                    context_parts.append(content[:available])
                    total_chars += len(header) + min(len(content), available)

            return "".join(context_parts)

        except Exception as e:
            print(f"Failed to get document context: {e}")
            return ""

    @staticmethod
    async def get_related_documents(
        db: AsyncSession,
        task_id: Optional[str] = None,
        inference_id: Optional[int] = None
    ) -> List[Document]:
        """
        Get documents related to a task or inference

        Args:
            db: Database session
            task_id: Optional task ID
            inference_id: Optional inference history ID

        Returns:
            List of related documents
        """
        try:
            stmt = select(Document)

            if task_id:
                stmt = stmt.where(Document.task_id == task_id)
            elif inference_id:
                stmt = stmt.where(Document.inference_history_id == inference_id)
            else:
                return []

            result = await db.execute(stmt)
            documents = result.scalars().all()

            return list(documents)

        except Exception as e:
            print(f"Failed to get related documents: {e}")
            return []

    @staticmethod
    async def get_knowledge_base_summary(db: AsyncSession) -> Dict:
        """
        Get summary statistics of the knowledge base

        Args:
            db: Database session

        Returns:
            Dictionary with statistics
        """
        try:
            # Get total document count
            result = await db.execute(select(Document))
            all_docs = result.scalars().all()

            # Calculate statistics
            total_docs = len(all_docs)
            total_size = sum(doc.size_bytes for doc in all_docs)
            by_category = {}
            by_extension = {}

            for doc in all_docs:
                # Count by category
                by_category[doc.category] = by_category.get(doc.category, 0) + 1

                # Count by extension
                ext = doc.file_extension
                by_extension[ext] = by_extension.get(ext, 0) + 1

            return {
                "total_documents": total_docs,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_category": by_category,
                "by_extension": by_extension,
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Failed to get knowledge base summary: {e}")
            return {
                "total_documents": 0,
                "total_size_bytes": 0,
                "error": str(e)
            }

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
        """
        Extract keywords from text (simple implementation)

        Args:
            text: Text content
            max_keywords: Maximum keywords to return

        Returns:
            List of keywords
        """
        if not text:
            return []

        # Simple keyword extraction: remove common words and get most frequent
        # For production, consider using NLP libraries like spaCy or NLTK

        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())

        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'her', 'was', 'one', 'our', 'out', 'this', 'that', 'have', 'from',
            'with', 'they', 'been', 'will', 'what', 'when', 'make', 'like',
            'has', 'had', 'into', 'than', 'more', 'some', 'could', 'them'
        }

        filtered_words = [w for w in words if w not in stop_words]

        # Count frequency
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords]]

        return keywords
