"""
Document-Cognitive Nexus Integration Service

Bridges advanced PDF processing with the Cognitive Nexus knowledge graph system.
Enables automatic knowledge graph population from document uploads.

Flow:
1. Document uploaded → Advanced PDF processing
2. Extract entities, summaries, relationships
3. Feed to Cognitive Nexus for knowledge graph building
4. Enable cross-document intelligence
"""

from typing import Dict, List, Optional
from dataclasses import asdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from agents.advanced_pdf_processor import ProcessedDocument
from agents.document_analyzer import DocumentAnalysis, DocumentAnalyzer
from agents.cognitive_nexus_graph import process_context
from db.models import ContextItem, Entity, Relationship, Task
from services.knowledge_graph_service import KnowledgeGraphService
from config.constants import (
    MAX_RECENT_TASKS_FOR_MATCHING,
    ENTITY_TYPE_PERSON,
    ENTITY_TYPE_PROJECT,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_DATE
)


class DocumentCognitiveIntegration:
    """
    Integrates document processing with Cognitive Nexus knowledge graph

    Provides unified document intelligence that:
    - Extracts entities from documents
    - Builds persistent knowledge graph across documents
    - Enables cross-document relationship tracking
    - Provides organizational context over time
    """

    def __init__(self, db: AsyncSession):
        """Initialize integration service

        Args:
            db: Async database session
        """
        self.db = db
        self.kg_service = KnowledgeGraphService(db)

    async def process_document_with_knowledge_graph(
        self,
        processed_doc: ProcessedDocument,
        analysis: DocumentAnalysis,
        document_id: Optional[str] = None,
        source_identifier: Optional[str] = None
    ) -> Dict:
        """
        Process document and populate knowledge graph

        Args:
            processed_doc: ProcessedDocument from AdvancedPDFProcessor
            analysis: DocumentAnalysis from DocumentAnalyzer
            document_id: Optional document ID for tracking
            source_identifier: Optional source identifier

        Returns:
            Dict with knowledge graph results and statistics
        """
        # Build context text for Cognitive Nexus
        context_text = self._build_context_text(processed_doc, analysis)

        # Get existing tasks for matching
        existing_tasks = await self._get_existing_tasks()

        # Process through Cognitive Nexus
        final_state = await process_context(
            text=context_text,
            source_type="document",
            source_identifier=source_identifier or document_id,
            existing_tasks=existing_tasks
        )

        # Store context item
        context_item = await self._store_context_item(
            content=context_text[:1000],  # Store truncated for performance
            processed_doc=processed_doc,
            analysis=analysis,
            final_state=final_state,
            source_identifier=source_identifier or document_id
        )

        # Store entities and merge into knowledge graph
        entity_count = await self._store_entities(
            entities=final_state.get("extracted_entities", []),
            context_item_id=context_item.id
        )

        # Store relationships
        relationship_count = await self._store_relationships(
            relationships=final_state.get("inferred_relationships", []),
            context_item_id=context_item.id
        )

        # Execute task operations
        task_stats = await self._execute_task_operations(
            task_operations=final_state.get("task_operations", [])
        )

        await self.db.commit()

        return {
            "context_item_id": context_item.id,
            "entities_extracted": entity_count,
            "relationships_inferred": relationship_count,
            "tasks_created": task_stats["created"],
            "tasks_updated": task_stats["updated"],
            "comments_added": task_stats["commented"],
            "quality_metrics": {
                "entity_quality": final_state.get("entity_quality", 0.0),
                "relationship_quality": final_state.get("relationship_quality", 0.0),
                "task_quality": final_state.get("task_quality", 0.0),
                "context_complexity": final_state.get("context_complexity", 0.0)
            },
            "reasoning_steps": final_state.get("reasoning_steps", []),
            "extraction_strategy": final_state.get("extraction_strategy", "unknown")
        }

    async def enrich_document_with_entities(
        self,
        analysis: DocumentAnalysis
    ) -> List[Dict]:
        """
        Convert DocumentAnalysis entities to Cognitive Nexus format

        Args:
            analysis: DocumentAnalysis from DocumentAnalyzer

        Returns:
            List of entities in Cognitive Nexus format
        """
        entities = []

        # Map people to PERSON entities
        for person in analysis.entities.people:
            entities.append({
                "name": person,
                "type": ENTITY_TYPE_PERSON,
                "confidence": 0.9,
                "source": "document_analyzer"
            })

        # Map organizations to TEAM entities
        for org in analysis.entities.organizations:
            entities.append({
                "name": org,
                "type": ENTITY_TYPE_TEAM,
                "confidence": 0.9,
                "source": "document_analyzer"
            })

        # Map dates to DATE entities
        for date in analysis.entities.dates:
            entities.append({
                "name": date,
                "type": ENTITY_TYPE_DATE,
                "confidence": 0.85,
                "source": "document_analyzer"
            })

        # Try to infer PROJECT entities from key decisions or action items
        for decision in analysis.entities.key_decisions:
            # Simple heuristic: if decision mentions a project-like term
            if any(term in decision.lower() for term in ["project", "initiative", "program"]):
                # Extract potential project name
                words = decision.split()
                for i, word in enumerate(words):
                    if word.lower() in ["project", "initiative"]:
                        if i > 0:
                            project_name = words[i-1]
                            entities.append({
                                "name": project_name,
                                "type": ENTITY_TYPE_PROJECT,
                                "confidence": 0.7,
                                "source": "document_analyzer_inferred"
                            })

        return entities

    def _build_context_text(
        self,
        processed_doc: ProcessedDocument,
        analysis: DocumentAnalysis
    ) -> str:
        """Build rich context text from document for Cognitive Nexus

        Args:
            processed_doc: Processed document
            analysis: Document analysis

        Returns:
            Formatted context text
        """
        parts = []

        # Add document metadata
        if processed_doc.metadata.title:
            parts.append(f"Document: {processed_doc.metadata.title}")
        if processed_doc.metadata.author:
            parts.append(f"Author: {processed_doc.metadata.author}")

        # Add executive summary
        if analysis.summary.executive_summary:
            parts.append(f"\nSummary: {analysis.summary.executive_summary}")

        # Add key points
        if analysis.summary.key_points:
            parts.append("\nKey Points:")
            for point in analysis.summary.key_points:
                parts.append(f"- {point}")

        # Add entities context
        if analysis.entities.people:
            parts.append(f"\nPeople mentioned: {', '.join(analysis.entities.people)}")
        if analysis.entities.organizations:
            parts.append(f"Organizations: {', '.join(analysis.entities.organizations)}")

        # Add key decisions
        if analysis.entities.key_decisions:
            parts.append("\nKey Decisions:")
            for decision in analysis.entities.key_decisions:
                parts.append(f"- {decision}")

        # Add action items
        if analysis.entities.action_items:
            parts.append("\nAction Items:")
            for item in analysis.entities.action_items:
                parts.append(f"- {item}")

        # Add sample of actual content (first chunk)
        if processed_doc.chunks:
            parts.append("\n--- Document Content ---")
            parts.append(processed_doc.chunks[0]["content"][:2000])

        return "\n".join(parts)

    async def _get_existing_tasks(self) -> List[Dict]:
        """Get recent tasks for matching

        Returns:
            List of task dicts
        """
        result = await self.db.execute(
            select(Task)
            .order_by(Task.updated_at.desc())
            .limit(MAX_RECENT_TASKS_FOR_MATCHING)
        )
        tasks = result.scalars().all()

        return [
            {
                "id": task.id,
                "title": task.title,
                "assignee": task.assignee,
                "value_stream": task.value_stream,
                "description": task.description,
                "status": task.status,
                "due_date": task.due_date
            }
            for task in tasks
        ]

    async def _store_context_item(
        self,
        content: str,
        processed_doc: ProcessedDocument,
        analysis: DocumentAnalysis,
        final_state: Dict,
        source_identifier: Optional[str]
    ) -> ContextItem:
        """Store context item in database

        Args:
            content: Context content
            processed_doc: Processed document
            analysis: Document analysis
            final_state: Cognitive Nexus final state
            source_identifier: Source identifier

        Returns:
            Created ContextItem
        """
        context_item = ContextItem(
            content=content,
            source_type="document",
            source_identifier=source_identifier,
            extraction_strategy=final_state.get("extraction_strategy"),
            context_complexity=final_state.get("context_complexity"),
            entity_quality=final_state.get("entity_quality"),
            relationship_quality=final_state.get("relationship_quality"),
            task_quality=final_state.get("task_quality"),
            reasoning_trace=json.dumps(final_state.get("reasoning_steps", []))
        )
        self.db.add(context_item)
        await self.db.flush()

        return context_item

    async def _store_entities(
        self,
        entities: List[Dict],
        context_item_id: int
    ) -> int:
        """Store entities and merge into knowledge graph

        Args:
            entities: List of entity dicts
            context_item_id: Context item ID

        Returns:
            Number of entities stored
        """
        entity_map = {}

        for entity_data in entities:
            entity = Entity(
                name=entity_data["name"],
                type=entity_data["type"],
                confidence=entity_data.get("confidence", 1.0),
                entity_metadata=entity_data.get("metadata"),
                context_item_id=context_item_id
            )
            self.db.add(entity)
            await self.db.flush()

            # Merge into knowledge graph
            await self.kg_service.merge_entity_to_knowledge_graph(entity)

            entity_map[entity_data["name"]] = entity

        return len(entities)

    async def _store_relationships(
        self,
        relationships: List[Dict],
        context_item_id: int
    ) -> int:
        """Store relationships and aggregate into knowledge graph

        Args:
            relationships: List of relationship dicts
            context_item_id: Context item ID

        Returns:
            Number of relationships stored
        """
        # Get all entities for this context
        result = await self.db.execute(
            select(Entity).where(Entity.context_item_id == context_item_id)
        )
        entities = result.scalars().all()
        entity_map = {e.name: e for e in entities}

        count = 0
        for rel_data in relationships:
            subject_name = rel_data.get("subject")
            object_name = rel_data.get("object")

            if subject_name in entity_map and object_name in entity_map:
                subject_entity = entity_map[subject_name]
                object_entity = entity_map[object_name]

                relationship = Relationship(
                    subject_entity_id=subject_entity.id,
                    predicate=rel_data.get("predicate"),
                    object_entity_id=object_entity.id,
                    confidence=rel_data.get("confidence", 1.0),
                    context_item_id=context_item_id
                )
                self.db.add(relationship)
                await self.db.flush()

                # Aggregate into knowledge graph
                await self.kg_service.aggregate_relationship_to_knowledge_graph(relationship)

                count += 1

        return count

    async def _execute_task_operations(
        self,
        task_operations: List[Dict]
    ) -> Dict[str, int]:
        """Execute task operations (CREATE, UPDATE, COMMENT, ENRICH)

        Args:
            task_operations: List of task operation dicts

        Returns:
            Dict with operation counts
        """
        from config.constants import TASK_OP_CREATE, TASK_OP_UPDATE, TASK_OP_COMMENT, TASK_OP_ENRICH
        from db.models import Comment
        import uuid
        from datetime import datetime

        stats = {
            "created": 0,
            "updated": 0,
            "commented": 0,
            "enriched": 0
        }

        for op in task_operations:
            operation = op.get("operation")

            if operation == TASK_OP_CREATE:
                # Create new task
                task_data = op.get("data", {})
                task = Task(
                    id=str(uuid.uuid4()),
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    assignee=task_data.get("assignee", "You"),
                    status=task_data.get("status", "todo"),
                    value_stream=task_data.get("value_stream"),
                    due_date=task_data.get("due_date"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(task)
                stats["created"] += 1

            elif operation == TASK_OP_UPDATE:
                # Update existing task
                task_id = op.get("task_id")
                updates = op.get("data", {})

                result = await self.db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if task:
                    for key, value in updates.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
                    task.updated_at = datetime.utcnow()
                    stats["updated"] += 1

            elif operation == TASK_OP_COMMENT:
                # Add comment to task
                task_id = op.get("task_id")
                comment_text = op.get("data", {}).get("comment")

                if task_id and comment_text:
                    comment = Comment(
                        task_id=task_id,
                        author="System",
                        text=comment_text,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(comment)
                    stats["commented"] += 1

            elif operation == TASK_OP_ENRICH:
                # Enrich task with additional context
                task_id = op.get("task_id")
                enrichment = op.get("data", {})

                result = await self.db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

                if task:
                    # Add enrichment to description or notes
                    if enrichment.get("context"):
                        current_notes = task.notes or ""
                        task.notes = f"{current_notes}\n\nContext from document: {enrichment['context']}"
                    task.updated_at = datetime.utcnow()
                    stats["enriched"] += 1

        return stats
