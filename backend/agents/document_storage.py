"""
Document Storage System

Handles persistent storage of uploaded documents with:
- Unique file naming to prevent collisions
- Organized directory structure
- File retrieval and deletion
- Metadata tracking
"""
import asyncio
import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import uuid


class DocumentStorage:
    """
    Manage persistent storage of documents

    Directory structure:
    documents/
    ├── tasks/          # Documents attached to tasks
    ├── inference/      # Documents used for AI inference
    └── knowledge/      # Documents in knowledge base
    """

    def __init__(self, base_dir: str = "./data/documents"):
        """
        Initialize document storage

        Args:
            base_dir: Base directory for document storage
        """
        self.base_dir = Path(base_dir)
        self.tasks_dir = self.base_dir / "tasks"
        self.inference_dir = self.base_dir / "inference"
        self.knowledge_dir = self.base_dir / "knowledge"

    async def initialize(self):
        """Create directory structure if it doesn't exist"""
        def create_dirs():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.tasks_dir.mkdir(exist_ok=True)
            self.inference_dir.mkdir(exist_ok=True)
            self.knowledge_dir.mkdir(exist_ok=True)

        await asyncio.to_thread(create_dirs)

    @staticmethod
    def _generate_file_id() -> str:
        """Generate unique file ID"""
        return str(uuid.uuid4())

    @staticmethod
    def _compute_hash(file_bytes: bytes) -> str:
        """Compute SHA-256 hash of file content"""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        # Remove any path components
        filename = os.path.basename(filename)
        # Remove any potentially dangerous characters
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        filename = ''.join(c if c in safe_chars else '_' for c in filename)
        return filename

    def _get_storage_path(self, category: str, file_id: str, original_filename: str) -> Path:
        """
        Get storage path for document

        Args:
            category: Storage category (tasks, inference, knowledge)
            file_id: Unique file ID
            original_filename: Original filename (will be sanitized)

        Returns:
            Path to store the file
        """
        if category == "tasks":
            base = self.tasks_dir
        elif category == "inference":
            base = self.inference_dir
        elif category == "knowledge":
            base = self.knowledge_dir
        else:
            raise ValueError(f"Invalid category: {category}")

        # Create filename: {file_id}_{sanitized_original_name}
        safe_filename = self._sanitize_filename(original_filename)
        filename = f"{file_id}_{safe_filename}"

        return base / filename

    async def save_document(
        self,
        file_bytes: bytes,
        original_filename: str,
        category: str = "tasks",
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Save document to storage

        Args:
            file_bytes: File content
            original_filename: Original filename
            category: Storage category (tasks, inference, knowledge)
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with file information:
            {
                "file_id": str,
                "storage_path": str,
                "original_filename": str,
                "file_hash": str,
                "size_bytes": int,
                "saved_at": str (ISO timestamp)
            }
        """
        # Ensure directories exist
        await self.initialize()

        # Generate file ID and compute hash
        file_id = self._generate_file_id()
        file_hash = await asyncio.to_thread(self._compute_hash, file_bytes)

        # Get storage path
        storage_path = self._get_storage_path(category, file_id, original_filename)

        # Save file
        def write_file():
            with open(storage_path, 'wb') as f:
                f.write(file_bytes)

        await asyncio.to_thread(write_file)

        # Return file info
        return {
            "file_id": file_id,
            "storage_path": str(storage_path),
            "relative_path": str(storage_path.relative_to(self.base_dir)),
            "original_filename": original_filename,
            "file_hash": file_hash,
            "size_bytes": len(file_bytes),
            "category": category,
            "saved_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

    async def get_document(self, file_id: str, category: str) -> Optional[bytes]:
        """
        Retrieve document from storage

        Args:
            file_id: File ID
            category: Storage category

        Returns:
            File bytes or None if not found
        """
        # Find file with this ID
        if category == "tasks":
            search_dir = self.tasks_dir
        elif category == "inference":
            search_dir = self.inference_dir
        elif category == "knowledge":
            search_dir = self.knowledge_dir
        else:
            return None

        # Search for file starting with file_id
        def find_and_read():
            if not search_dir.exists():
                return None

            for file_path in search_dir.iterdir():
                if file_path.is_file() and file_path.name.startswith(file_id):
                    with open(file_path, 'rb') as f:
                        return f.read()
            return None

        return await asyncio.to_thread(find_and_read)

    async def delete_document(self, file_id: str, category: str) -> bool:
        """
        Delete document from storage

        Args:
            file_id: File ID
            category: Storage category

        Returns:
            True if deleted, False if not found
        """
        if category == "tasks":
            search_dir = self.tasks_dir
        elif category == "inference":
            search_dir = self.inference_dir
        elif category == "knowledge":
            search_dir = self.knowledge_dir
        else:
            return False

        def find_and_delete():
            if not search_dir.exists():
                return False

            for file_path in search_dir.iterdir():
                if file_path.is_file() and file_path.name.startswith(file_id):
                    file_path.unlink()
                    return True
            return False

        return await asyncio.to_thread(find_and_delete)

    async def get_document_path(self, file_id: str, category: str) -> Optional[str]:
        """
        Get path to stored document

        Args:
            file_id: File ID
            category: Storage category

        Returns:
            Full path to file or None if not found
        """
        if category == "tasks":
            search_dir = self.tasks_dir
        elif category == "inference":
            search_dir = self.inference_dir
        elif category == "knowledge":
            search_dir = self.knowledge_dir
        else:
            return None

        def find_path():
            if not search_dir.exists():
                return None

            for file_path in search_dir.iterdir():
                if file_path.is_file() and file_path.name.startswith(file_id):
                    return str(file_path)
            return None

        return await asyncio.to_thread(find_path)

    async def list_documents(self, category: str) -> list:
        """
        List all documents in a category

        Args:
            category: Storage category

        Returns:
            List of document info dictionaries
        """
        if category == "tasks":
            search_dir = self.tasks_dir
        elif category == "inference":
            search_dir = self.inference_dir
        elif category == "knowledge":
            search_dir = self.knowledge_dir
        else:
            return []

        def list_files():
            if not search_dir.exists():
                return []

            files = []
            for file_path in search_dir.iterdir():
                if file_path.is_file():
                    # Parse filename: {file_id}_{original_name}
                    parts = file_path.name.split('_', 1)
                    file_id = parts[0] if len(parts) > 0 else ""
                    original_name = parts[1] if len(parts) > 1 else file_path.name

                    stat = file_path.stat()
                    files.append({
                        "file_id": file_id,
                        "original_filename": original_name,
                        "storage_path": str(file_path),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

            return files

        return await asyncio.to_thread(list_files)
