"""
Advanced PDF processing with layout analysis, table extraction, and metadata
Designed for optimal AI consumption and task extraction
"""
import io
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import fitz  # PyMuPDF
import pdfplumber
import re


@dataclass
class PDFMetadata:
    """Structured PDF metadata"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    has_tables: bool = False
    has_images: bool = False
    file_size_bytes: int = 0


@dataclass
class DocumentSection:
    """Represents a semantic section of the document"""
    section_type: str  # 'heading', 'paragraph', 'list', 'table', 'metadata'
    content: str
    page_number: int
    level: int = 0  # For headings: 1, 2, 3, etc.
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessedDocument:
    """Complete processed document with structure"""
    raw_text: str
    structured_sections: List[DocumentSection]
    tables: List[Dict[str, Any]]
    metadata: PDFMetadata
    chunks: List[Dict[str, str]]  # For LLM consumption
    summary_stats: Dict[str, Any]


class AdvancedPDFProcessor:
    """
    Advanced PDF processor with intelligent extraction capabilities

    Features:
    - Layout-aware text extraction (preserves structure)
    - Table detection and extraction
    - Metadata extraction
    - Intelligent semantic chunking
    - Document statistics
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_CHUNK_SIZE = 4000  # Characters per chunk for LLM
    MIN_CHUNK_SIZE = 500   # Minimum chunk size

    @staticmethod
    async def process_document(pdf_bytes: bytes) -> ProcessedDocument:
        """
        Process PDF with advanced extraction

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            ProcessedDocument with all extracted information

        Raises:
            ValueError: If PDF is invalid or too large
            Exception: If processing fails
        """
        if not pdf_bytes:
            raise ValueError("PDF bytes cannot be empty")

        if len(pdf_bytes) > AdvancedPDFProcessor.MAX_FILE_SIZE:
            raise ValueError(
                f"PDF file too large. Maximum size: "
                f"{AdvancedPDFProcessor.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )

        try:
            # Extract metadata
            metadata = await AdvancedPDFProcessor._extract_metadata(pdf_bytes)

            # Extract structured content
            structured_sections = await AdvancedPDFProcessor._extract_structured_content(pdf_bytes)

            # Extract tables
            tables = await AdvancedPDFProcessor._extract_tables(pdf_bytes)
            metadata.has_tables = len(tables) > 0

            # Build raw text from sections
            raw_text = "\n\n".join([
                section.content for section in structured_sections
                if section.section_type != 'metadata'
            ])

            # Create intelligent chunks
            chunks = AdvancedPDFProcessor._create_semantic_chunks(
                structured_sections,
                tables
            )

            # Calculate summary statistics
            summary_stats = {
                "total_sections": len(structured_sections),
                "total_tables": len(tables),
                "total_chunks": len(chunks),
                "average_chunk_size": sum(len(c["content"]) for c in chunks) // max(len(chunks), 1),
                "word_count": len(raw_text.split()),
                "character_count": len(raw_text)
            }

            return ProcessedDocument(
                raw_text=raw_text,
                structured_sections=structured_sections,
                tables=tables,
                metadata=metadata,
                chunks=chunks,
                summary_stats=summary_stats
            )

        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Advanced PDF processing failed: {str(e)}")

    @staticmethod
    async def _extract_metadata(pdf_bytes: bytes) -> PDFMetadata:
        """Extract comprehensive metadata from PDF"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        try:
            metadata_dict = doc.metadata

            # Parse dates if present
            creation_date = None
            mod_date = None

            if metadata_dict.get("creationDate"):
                creation_date = AdvancedPDFProcessor._parse_pdf_date(
                    metadata_dict["creationDate"]
                )

            if metadata_dict.get("modDate"):
                mod_date = AdvancedPDFProcessor._parse_pdf_date(
                    metadata_dict["modDate"]
                )

            # Check for images
            has_images = False
            for page in doc:
                if page.get_images():
                    has_images = True
                    break

            metadata = PDFMetadata(
                title=metadata_dict.get("title", "").strip() or None,
                author=metadata_dict.get("author", "").strip() or None,
                subject=metadata_dict.get("subject", "").strip() or None,
                creator=metadata_dict.get("creator", "").strip() or None,
                producer=metadata_dict.get("producer", "").strip() or None,
                creation_date=creation_date,
                modification_date=mod_date,
                page_count=len(doc),
                has_images=has_images,
                file_size_bytes=len(pdf_bytes)
            )

            return metadata

        finally:
            doc.close()

    @staticmethod
    async def _extract_structured_content(pdf_bytes: bytes) -> List[DocumentSection]:
        """
        Extract content with structure preservation
        Uses PyMuPDF's layout analysis
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        sections = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get text blocks with layout information
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if block.get("type") == 0:  # Text block
                        # Extract text from lines
                        text_parts = []
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text_parts.append(span.get("text", ""))

                        text = " ".join(text_parts).strip()
                        if not text:
                            continue

                        # Detect section type
                        section_type, level = AdvancedPDFProcessor._classify_text_block(
                            text,
                            block
                        )

                        sections.append(DocumentSection(
                            section_type=section_type,
                            content=text,
                            page_number=page_num + 1,
                            level=level,
                            metadata={
                                "bbox": block.get("bbox"),
                                "font_size": AdvancedPDFProcessor._get_avg_font_size(block)
                            }
                        ))

            return sections

        finally:
            doc.close()

    @staticmethod
    async def _extract_tables(pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract tables with structure using pdfplumber
        Returns tables as formatted markdown and JSON
        """
        tables_found = []

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Find tables on this page
                    tables = page.extract_tables()

                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:  # Skip invalid tables
                            continue

                        # Convert to markdown
                        markdown = AdvancedPDFProcessor._table_to_markdown(table)

                        # Convert to structured JSON
                        headers = table[0] if table else []
                        rows = table[1:] if len(table) > 1 else []

                        tables_found.append({
                            "page_number": page_num,
                            "table_index": table_idx,
                            "markdown": markdown,
                            "headers": headers,
                            "rows": rows,
                            "row_count": len(rows),
                            "column_count": len(headers)
                        })

            return tables_found

        except Exception as e:
            # pdfplumber might fail on some PDFs - fallback gracefully
            print(f"Table extraction warning: {e}")
            return []

    @staticmethod
    def _create_semantic_chunks(
        sections: List[DocumentSection],
        tables: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Create intelligent chunks for LLM consumption
        Tries to keep related content together
        """
        chunks = []
        current_chunk = []
        current_size = 0
        current_page = 1

        # Combine sections and tables in order
        all_items = []

        # Add sections
        for section in sections:
            all_items.append({
                "type": "section",
                "data": section,
                "page": section.page_number
            })

        # Add tables
        for table in tables:
            all_items.append({
                "type": "table",
                "data": table,
                "page": table["page_number"]
            })

        # Sort by page number
        all_items.sort(key=lambda x: x["page"])

        for item in all_items:
            if item["type"] == "section":
                section = item["data"]
                content = f"\n{section.content}"

                # Add heading markers
                if section.section_type == "heading":
                    content = f"\n{'#' * min(section.level, 6)} {section.content}\n"
                elif section.section_type == "list":
                    content = f"\n- {section.content}"

            else:  # table
                table = item["data"]
                content = f"\n\n**Table {table['table_index'] + 1}**:\n{table['markdown']}\n"

            content_size = len(content)

            # Check if we need to start a new chunk
            if current_size + content_size > AdvancedPDFProcessor.MAX_CHUNK_SIZE:
                if current_chunk and current_size >= AdvancedPDFProcessor.MIN_CHUNK_SIZE:
                    # Save current chunk
                    chunks.append({
                        "content": "".join(current_chunk),
                        "page_start": current_page,
                        "page_end": item["page"],
                        "size": current_size
                    })
                    current_chunk = []
                    current_size = 0
                    current_page = item["page"]

            current_chunk.append(content)
            current_size += content_size

        # Add final chunk
        if current_chunk:
            chunks.append({
                "content": "".join(current_chunk),
                "page_start": current_page,
                "page_end": item["page"] if all_items else 1,
                "size": current_size
            })

        return chunks

    @staticmethod
    def _classify_text_block(text: str, block: Dict) -> tuple[str, int]:
        """
        Classify text block as heading, paragraph, list, etc.
        Returns (type, level)
        """
        # Get average font size
        avg_font_size = AdvancedPDFProcessor._get_avg_font_size(block)

        # Check if it's a heading (larger font, short text, etc.)
        if len(text) < 100 and avg_font_size > 12:
            # Determine heading level based on font size
            if avg_font_size >= 18:
                return ("heading", 1)
            elif avg_font_size >= 15:
                return ("heading", 2)
            else:
                return ("heading", 3)

        # Check if it's a list item
        if re.match(r'^[\d\-•*]\s', text):
            return ("list", 0)

        # Default to paragraph
        return ("paragraph", 0)

    @staticmethod
    def _get_avg_font_size(block: Dict) -> float:
        """Get average font size from block"""
        sizes = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if "size" in span:
                    sizes.append(span["size"])

        return sum(sizes) / len(sizes) if sizes else 11.0

    @staticmethod
    def _table_to_markdown(table: List[List[str]]) -> str:
        """Convert table to markdown format"""
        if not table or len(table) < 2:
            return ""

        # Clean cells
        cleaned = []
        for row in table:
            cleaned_row = [str(cell or "").strip() for cell in row]
            cleaned.append(cleaned_row)

        # Get max widths
        max_widths = [
            max(len(str(row[i] or "")) for row in cleaned)
            for i in range(len(cleaned[0]))
        ]

        # Build markdown
        lines = []

        # Header row
        header = cleaned[0]
        lines.append("| " + " | ".join(
            str(cell).ljust(max_widths[i]) for i, cell in enumerate(header)
        ) + " |")

        # Separator
        lines.append("| " + " | ".join(
            "-" * max_widths[i] for i in range(len(header))
        ) + " |")

        # Data rows
        for row in cleaned[1:]:
            lines.append("| " + " | ".join(
                str(cell).ljust(max_widths[i]) for i, cell in enumerate(row)
            ) + " |")

        return "\n".join(lines)

    @staticmethod
    def _parse_pdf_date(pdf_date_str: str) -> Optional[str]:
        """Parse PDF date format to ISO format"""
        try:
            # PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
            match = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", pdf_date_str)
            if match:
                year, month, day, hour, minute, second = match.groups()
                dt = datetime(
                    int(year), int(month), int(day),
                    int(hour), int(minute), int(second)
                )
                return dt.isoformat()
        except Exception:
            pass

        return None

    @staticmethod
    def validate_pdf(pdf_bytes: bytes) -> bool:
        """
        Check if bytes represent a valid PDF

        Args:
            pdf_bytes: File content

        Returns:
            True if valid PDF, False otherwise
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            return False

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            valid = len(doc) > 0
            doc.close()
            return valid
        except Exception:
            return False
