"""
Document Analyzer Agent - AI-powered document understanding
Provides summarization, entity extraction, and context-aware analysis
"""
import json
import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import httpx
from .advanced_pdf_processor import ProcessedDocument, DocumentSection


@dataclass
class DocumentSummary:
    """Structured document summary"""
    executive_summary: str
    key_points: List[str]
    document_type: str  # meeting_notes, report, invoice, etc.
    topics: List[str]
    confidence: float


@dataclass
class ExtractedEntities:
    """Entities extracted from document"""
    people: List[str]
    organizations: List[str]
    dates: List[str]
    locations: List[str]
    key_decisions: List[str]
    action_items: List[str]


@dataclass
class DocumentAnalysis:
    """Complete document analysis result"""
    summary: DocumentSummary
    entities: ExtractedEntities
    context: Dict[str, Any]
    inference_time_ms: int
    model_used: str


class DocumentAnalyzer:
    """
    AI-powered document analysis using local LLM

    Features:
    - Document summarization (executive summary)
    - Entity extraction (people, dates, organizations, etc.)
    - Document type classification
    - Key insights and decisions extraction
    - Context-aware task extraction
    """

    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_TOP_P = 0.9
    DEFAULT_MAX_TOKENS = 2000  # More tokens for summaries
    REQUEST_TIMEOUT = 180.0  # 3 minutes for analysis

    def __init__(self, ollama_base_url: str, model: str):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT)

    async def analyze_document(
        self,
        processed_doc: ProcessedDocument
    ) -> DocumentAnalysis:
        """
        Perform comprehensive document analysis

        Args:
            processed_doc: ProcessedDocument from AdvancedPDFProcessor

        Returns:
            DocumentAnalysis with summary, entities, and context

        Raises:
            Exception: If analysis fails
        """
        start_time = time.time()

        try:
            # Run analysis tasks
            summary = await self._generate_summary(processed_doc)
            entities = await self._extract_entities(processed_doc)

            # Build context
            context = {
                "page_count": processed_doc.metadata.page_count,
                "has_tables": processed_doc.metadata.has_tables,
                "table_count": len(processed_doc.tables),
                "word_count": processed_doc.summary_stats.get("word_count", 0),
                "section_count": processed_doc.summary_stats.get("total_sections", 0),
                "metadata": {
                    "title": processed_doc.metadata.title,
                    "author": processed_doc.metadata.author,
                    "creation_date": processed_doc.metadata.creation_date
                }
            }

            inference_time_ms = int((time.time() - start_time) * 1000)

            return DocumentAnalysis(
                summary=summary,
                entities=entities,
                context=context,
                inference_time_ms=inference_time_ms,
                model_used=self.model
            )

        except Exception as e:
            raise Exception(f"Document analysis failed: {str(e)}")

    async def _generate_summary(
        self,
        processed_doc: ProcessedDocument
    ) -> DocumentSummary:
        """Generate comprehensive document summary"""
        from .prompts import get_document_summary_prompt

        # Use chunks for long documents or full text for short ones
        if len(processed_doc.chunks) > 1:
            # For multi-chunk docs, summarize each chunk then combine
            text_to_analyze = processed_doc.chunks[0]["content"][:8000]  # First chunk
        else:
            text_to_analyze = processed_doc.raw_text[:8000]  # Limit to 8k chars

        # Add metadata context
        metadata_context = ""
        if processed_doc.metadata.title:
            metadata_context += f"Title: {processed_doc.metadata.title}\n"
        if processed_doc.metadata.author:
            metadata_context += f"Author: {processed_doc.metadata.author}\n"
        if processed_doc.metadata.creation_date:
            metadata_context += f"Date: {processed_doc.metadata.creation_date}\n"

        full_context = f"{metadata_context}\n{text_to_analyze}"

        # Generate summary prompt
        prompts = get_document_summary_prompt(full_context)

        # Call LLM
        response = await self._call_ollama(prompts["system"], prompts["user"])

        # Parse response
        summary = self._parse_summary_response(response)

        return summary

    async def _extract_entities(
        self,
        processed_doc: ProcessedDocument
    ) -> ExtractedEntities:
        """Extract entities from document"""
        from .prompts import get_entity_extraction_prompt

        # Use first chunk or full text
        text_to_analyze = (
            processed_doc.chunks[0]["content"][:6000]
            if processed_doc.chunks
            else processed_doc.raw_text[:6000]
        )

        # Generate entity extraction prompt
        prompts = get_entity_extraction_prompt(text_to_analyze)

        # Call LLM
        response = await self._call_ollama(prompts["system"], prompts["user"])

        # Parse response
        entities = self._parse_entity_response(response)

        return entities

    async def extract_tasks_with_context(
        self,
        processed_doc: ProcessedDocument,
        assignee: str = "You"
    ) -> Dict[str, Any]:
        """
        Extract tasks with full document context

        Args:
            processed_doc: ProcessedDocument
            assignee: Default assignee

        Returns:
            Dict with tasks, context, and metadata
        """
        from .prompts import get_context_aware_task_extraction_prompt

        # Build rich context
        context_info = {
            "metadata": asdict(processed_doc.metadata),
            "has_tables": len(processed_doc.tables) > 0,
            "table_summaries": [
                f"Table {i+1} on page {t['page_number']}: {t['row_count']} rows, {t['column_count']} columns"
                for i, t in enumerate(processed_doc.tables[:3])  # First 3 tables
            ]
        }

        # Use first chunk or full text
        text_to_analyze = (
            processed_doc.chunks[0]["content"][:6000]
            if processed_doc.chunks
            else processed_doc.raw_text[:6000]
        )

        # Generate context-aware prompt
        prompts = get_context_aware_task_extraction_prompt(
            text_to_analyze,
            context_info
        )

        # Call LLM
        response = await self._call_ollama(prompts["system"], prompts["user"])

        # Parse tasks
        tasks = self._parse_task_response(response, assignee)

        return {
            "tasks": tasks,
            "context": context_info,
            "tasks_inferred": len(tasks)
        }

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama API with formatted prompts"""
        url = f"{self.ollama_base_url}/api/generate"

        # Combine prompts for Qwen 2.5 format
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.DEFAULT_TEMPERATURE,
                "top_p": self.DEFAULT_TOP_P,
                "num_predict": self.DEFAULT_MAX_TOKENS,
            }
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.ConnectError:
            raise Exception(
                "Cannot connect to Ollama. Ensure Ollama is running (ollama serve)"
            )
        except httpx.HTTPError as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def _parse_summary_response(self, response: str) -> DocumentSummary:
        """Parse LLM summary response"""
        # Extract JSON from response
        json_text = self._extract_json(response)

        try:
            data = json.loads(json_text) if json_text else {}

            return DocumentSummary(
                executive_summary=data.get("executive_summary", ""),
                key_points=data.get("key_points", []),
                document_type=data.get("document_type", "unknown"),
                topics=data.get("topics", []),
                confidence=data.get("confidence", 0.8)
            )
        except json.JSONDecodeError:
            # Fallback: extract key information from text
            return DocumentSummary(
                executive_summary=response[:500],
                key_points=[],
                document_type="unknown",
                topics=[],
                confidence=0.5
            )

    def _parse_entity_response(self, response: str) -> ExtractedEntities:
        """Parse LLM entity extraction response"""
        json_text = self._extract_json(response)

        try:
            data = json.loads(json_text) if json_text else {}

            return ExtractedEntities(
                people=data.get("people", []),
                organizations=data.get("organizations", []),
                dates=data.get("dates", []),
                locations=data.get("locations", []),
                key_decisions=data.get("key_decisions", []),
                action_items=data.get("action_items", [])
            )
        except json.JSONDecodeError:
            return ExtractedEntities(
                people=[],
                organizations=[],
                dates=[],
                locations=[],
                key_decisions=[],
                action_items=[]
            )

    def _parse_task_response(
        self,
        response: str,
        assignee: str
    ) -> List[Dict[str, Any]]:
        """Parse task extraction response"""
        import uuid
        from datetime import datetime

        json_text = self._extract_json(response)
        if not json_text:
            return []

        try:
            data = json.loads(json_text)
            tasks_data = data.get("tasks", [])

            tasks = []
            now = datetime.utcnow().isoformat()

            for task in tasks_data:
                if not task.get("title"):
                    continue

                formatted_task = {
                    "id": str(uuid.uuid4()),
                    "title": task["title"],
                    "status": "todo",
                    "assignee": assignee,
                    "startDate": None,
                    "dueDate": task.get("dueDate"),
                    "valueStream": task.get("valueStream"),
                    "description": task.get("description"),
                    "attachments": [],
                    "comments": [],
                    "createdAt": now,
                    "updatedAt": now
                }

                tasks.append(formatted_task)

            return tasks
        except json.JSONDecodeError:
            return []

    def _extract_json(self, response: str) -> Optional[str]:
        """Extract JSON from LLM response"""
        # Try to extract full JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json_match.group(0)

        # Try to find just array and wrap it
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            return f'{{"items": {array_match.group(0)}}}'

        return None

    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
