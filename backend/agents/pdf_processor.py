"""
PDF processing for meeting transcripts and documents
"""
import io
from typing import Optional
import fitz  # PyMuPDF


class PDFProcessor:
    """Process PDF files and extract text"""

    @staticmethod
    async def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """
        Extract all text from PDF file

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Extracted text as string
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()

            full_text = "\n\n".join(text_parts)
            return full_text
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    @staticmethod
    def validate_pdf(pdf_bytes: bytes) -> bool:
        """
        Check if bytes represent a valid PDF

        Args:
            pdf_bytes: File content

        Returns:
            True if valid PDF
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            valid = len(doc) > 0
            doc.close()
            return valid
        except:
            return False
