"""
PDF processing for meeting transcripts and documents

Fixed: Wraps blocking PyMuPDF operations in asyncio.to_thread() to prevent
greenlet_spawn errors when used with SQLAlchemy's async session.
"""
import io
import asyncio
from typing import Optional
import fitz  # PyMuPDF


class PDFProcessor:
    """Process PDF files and extract text content"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def _extract_text_sync(pdf_bytes: bytes) -> str:
        """
        Synchronous PDF text extraction (runs in thread pool)

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Extracted text as string
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Extract text from all pages
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts)

    @staticmethod
    def _validate_pdf_sync(pdf_bytes: bytes) -> bool:
        """
        Synchronous PDF validation (runs in thread pool)

        Args:
            pdf_bytes: File content

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            valid = len(doc) > 0
            doc.close()
            return valid
        except Exception:
            return False

    @staticmethod
    async def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """
        Extract all text from PDF file (async wrapper)

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Extracted text as string

        Raises:
            Exception: If PDF processing fails
        """
        if not pdf_bytes:
            raise ValueError("PDF bytes cannot be empty")

        if len(pdf_bytes) > PDFProcessor.MAX_FILE_SIZE:
            raise ValueError(f"PDF file too large. Maximum size: {PDFProcessor.MAX_FILE_SIZE / (1024*1024):.1f}MB")

        try:
            # Run blocking PDF operations in thread pool to avoid greenlet issues
            text = await asyncio.to_thread(PDFProcessor._extract_text_sync, pdf_bytes)
            return text
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    @staticmethod
    async def validate_pdf(pdf_bytes: bytes) -> bool:
        """
        Check if bytes represent a valid PDF (async wrapper)

        Args:
            pdf_bytes: File content

        Returns:
            True if valid PDF, False otherwise
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            return False

        # Run blocking PDF validation in thread pool
        return await asyncio.to_thread(PDFProcessor._validate_pdf_sync, pdf_bytes)
