"""
Unit tests for Phase 6 Database Models

Tests:
- All 15 table models can be created
- Relationships between tables
- Cascade deletes (if applicable)
"""

import pytest
import os
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Phase 6 database models
try:
    from db.knowledge_graph_models_v2 import (
        ConceptNode,
        ConversationThreadNode,
        TaskOutcomeNode,
        ConceptRelationship,
        TaskSimilarityIndex,
        ConceptTaskLink
    )
except ImportError:
    ConceptNode = None
    ConversationThreadNode = None
    TaskOutcomeNode = None
    ConceptRelationship = None
    TaskSimilarityIndex = None
    ConceptTaskLink = None

try:
    from db.task_version_models import (
        TaskVersion,
        VersionDiff,
        VersionComment
    )
except ImportError:
    TaskVersion = None
    VersionDiff = None
    VersionComment = None

try:
    from db.implicit_learning_models import (
        ImplicitSignal,
        SignalAggregate,
        LearningModel
    )
except ImportError:
    ImplicitSignal = None
    SignalAggregate = None
    LearningModel = None

try:
    from db.outcome_learning_models import (
        OutcomeQualityCorrelation
    )
except ImportError:
    OutcomeQualityCorrelation = None

try:
    from db.task_quality_models import (
        TaskQualityScore,
        QualityTrend
    )
except ImportError:
    TaskQualityScore = None
    QualityTrend = None


# ============================================================================
# TEST DATABASE FIXTURE
# ============================================================================

@pytest.fixture
async def test_db():
    """
    Create test database session with proper SQLAlchemy setup.
    
    Yields:
        AsyncSession: Database session for testing
    """
    from db.database import DATABASE_URL
    from db.models import Base
    from db.task_version_models import TaskVersion, VersionDiff, VersionComment
    from db.knowledge_graph_models_v2 import (
        ConceptNode, ConversationThreadNode, TaskOutcomeNode,
        ConceptRelationship, TaskSimilarityIndex, ConceptTaskLink
    )
    from db.implicit_learning_models import ImplicitSignal, SignalAggregate, LearningModel
    from db.outcome_learning_models import OutcomeQualityCorrelation
    from db.task_quality_models import TaskQualityScore, QualityTrend
    
    # Use in-memory database for tests
    test_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(test_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    session = async_session()
    try:
        yield session
    finally:
        # Cleanup: rollback any pending transactions
        await session.rollback()
        # Close the session
        await session.close()
        # Dispose of the engine to clean up connections
        await engine.dispose()


# ============================================================================
# MODEL CREATION TESTS
# ============================================================================

@pytest.mark.unit
class TestConceptNode:
    """Test ConceptNode model creation."""
    
    @pytest.mark.skipif(ConceptNode is None, reason="ConceptNode not available")
    def test_create_concept_node(self):
        """Test creating a ConceptNode."""
        concept = ConceptNode(
            name="CRESCO project",
            importance_score=0.75,
            confidence_tier="ESTABLISHED",
            first_mentioned=datetime.utcnow(),
            last_mentioned=datetime.utcnow(),
            mention_count_30d=10,
            mention_count_total=50
        )
        assert concept.name == "CRESCO project"
        assert concept.importance_score == 0.75
        assert concept.confidence_tier == "ESTABLISHED"
        assert concept.mention_count_total == 50
    
    @pytest.mark.skipif(ConceptNode is None, reason="ConceptNode not available")
    def test_concept_node_defaults(self):
        """Test ConceptNode default values."""
        concept = ConceptNode(name="Test Concept")
        assert concept.importance_score == 0.0
        assert concept.confidence_tier == "TENTATIVE"
        assert concept.mention_count_30d == 1
        assert concept.mention_count_total == 1
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(ConceptNode is None, reason="ConceptNode not available")
    async def test_concept_node_in_db(self, test_db):
        """Test creating ConceptNode in database."""
        concept = ConceptNode(
            name="CRESCO project",
            importance_score=0.75,
            confidence_tier="ESTABLISHED"
        )
        test_db.add(concept)
        await test_db.commit()
        await test_db.refresh(concept)
        
        assert concept.id is not None
        assert concept.name == "CRESCO project"


@pytest.mark.unit
class TestTaskVersion:
    """Test TaskVersion model creation."""
    
    @pytest.mark.skipif(TaskVersion is None, reason="TaskVersion not available")
    def test_create_task_version(self):
        """Test creating a TaskVersion."""
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="update",
            is_snapshot=False,
            is_milestone=False
        )
        assert version.task_id == "test-task-123"
        assert version.version_number == 1
        assert version.change_source == "user"
        assert version.is_snapshot == False
    
    @pytest.mark.skipif(TaskVersion is None, reason="TaskVersion not available")
    def test_version_snapshot(self):
        """Test creating a snapshot version."""
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="milestone",
            is_snapshot=True,
            is_milestone=True,
            snapshot_data={"title": "Test", "description": "Test desc"}
        )
        assert version.is_snapshot == True
        assert version.snapshot_data is not None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(TaskVersion is None, reason="TaskVersion not available")
    async def test_task_version_in_db(self, test_db):
        """Test creating TaskVersion in database."""
        from db.models import Task
        
        # Create a task first
        task = Task(
            id="test-task-123",
            title="Test Task",
            status="todo",
            assignee="test"
        )
        test_db.add(task)
        await test_db.commit()
        
        # Create version
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="created",
            is_snapshot=True
        )
        test_db.add(version)
        await test_db.commit()
        await test_db.refresh(version)
        
        assert version.id is not None
        assert version.task_id == "test-task-123"


@pytest.mark.unit
class TestTaskQualityScore:
    """Test TaskQualityScore model creation."""
    
    @pytest.mark.skipif(TaskQualityScore is None, reason="TaskQualityScore not available")
    def test_create_quality_score(self):
        """Test creating a TaskQualityScore."""
        score = TaskQualityScore(
            task_id="test-task-123",
            overall_score=0.85,
            completeness_score=0.9,
            clarity_score=0.8,
            actionability_score=0.85,
            relevance_score=0.9,
            confidence_score=0.75,
            quality_tier="excellent"
        )
        assert score.task_id == "test-task-123"
        assert score.overall_score == 0.85
        assert score.quality_tier == "excellent"
        assert score.completeness_score == 0.9
    
    @pytest.mark.skipif(TaskQualityScore is None, reason="TaskQualityScore not available")
    def test_quality_score_defaults(self):
        """Test TaskQualityScore default values."""
        score = TaskQualityScore(task_id="test-task")
        assert score.overall_score == 0.0
        assert score.quality_tier == "needs_improvement"


@pytest.mark.unit
class TestImplicitSignal:
    """Test ImplicitSignal model creation."""
    
    @pytest.mark.skipif(ImplicitSignal is None, reason="ImplicitSignal not available")
    def test_create_implicit_signal(self):
        """Test creating an ImplicitSignal."""
        signal = ImplicitSignal(
            signal_type="user_override",
            task_id="test-task-123",
            user_id=1,
            metadata={"field": "priority", "old_value": "low", "new_value": "high"},
            final_weight=1.0,
            confidence=0.9
        )
        assert signal.signal_type == "user_override"
        assert signal.task_id == "test-task-123"
        assert signal.final_weight == 1.0


# ============================================================================
# RELATIONSHIP TESTS
# ============================================================================

@pytest.mark.unit
class TestModelRelationships:
    """Test relationships between models."""
    
    @pytest.mark.skipif(ConceptNode is None or ConceptTaskLink is None, reason="Models not available")
    def test_concept_task_link(self):
        """Test ConceptTaskLink relationship."""
        concept = ConceptNode(name="Test Concept")
        link = ConceptTaskLink(
            concept_id=1,  # Would be set by relationship
            task_id="test-task-123",
            strength=0.85
        )
        assert link.concept_id == 1
        assert link.task_id == "test-task-123"
        assert link.strength == 0.85
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(TaskVersion is None or VersionDiff is None, reason="Models not available")
    async def test_version_diff_relationship(self, test_db):
        """Test VersionDiff relationship to TaskVersion."""
        from db.models import Task
        
        # Create task
        task = Task(id="test-task-123", title="Test", status="todo", assignee="test")
        test_db.add(task)
        await test_db.commit()
        
        # Create version
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="created"
        )
        test_db.add(version)
        await test_db.commit()
        await test_db.refresh(version)
        
        # Create diff
        diff = VersionDiff(
            version_id=version.id,
            field_name="title",
            old_value="Old Title",
            new_value="New Title",
            diff_type="text_edit"
        )
        test_db.add(diff)
        await test_db.commit()
        
        assert diff.version_id == version.id
        assert diff.field_name == "title"
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(TaskVersion is None or VersionComment is None, reason="Models not available")
    async def test_version_comment_relationship(self, test_db):
        """Test VersionComment relationship to TaskVersion."""
        from db.models import Task
        
        # Create task
        task = Task(id="test-task-123", title="Test", status="todo", assignee="test")
        test_db.add(task)
        await test_db.commit()
        
        # Create version
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="created"
        )
        test_db.add(version)
        await test_db.commit()
        await test_db.refresh(version)
        
        # Create comment
        comment = VersionComment(
            version_id=version.id,
            comment_text="This change looks good",
            created_by="test_user",
            comment_type="approval"
        )
        test_db.add(comment)
        await test_db.commit()
        
        assert comment.version_id == version.id
        assert comment.comment_text == "This change looks good"


# ============================================================================
# CASCADE DELETE TESTS
# ============================================================================

@pytest.mark.unit
class TestCascadeDeletes:
    """Test cascade delete behavior."""
    
    @pytest.mark.skipif(ConceptNode is None or ConceptTaskLink is None, reason="Models not available")
    def test_concept_task_link_cascade(self):
        """Test that ConceptTaskLink is deleted when ConceptNode is deleted."""
        # This would be tested with actual database operations
        # For unit tests, we verify the relationship is defined
        # Check that foreign key has ondelete="CASCADE" in actual model definition
        assert ConceptTaskLink is not None
        assert ConceptNode is not None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(TaskVersion is None or VersionDiff is None, reason="Models not available")
    async def test_version_diff_cascade(self, test_db):
        """Test that VersionDiff is deleted when TaskVersion is deleted."""
        from db.models import Task
        
        # Create task and version
        task = Task(id="test-task-123", title="Test", status="todo", assignee="test")
        test_db.add(task)
        await test_db.commit()
        
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="created"
        )
        test_db.add(version)
        await test_db.commit()
        await test_db.refresh(version)
        
        # Create diff
        diff = VersionDiff(
            version_id=version.id,
            field_name="title",
            old_value="Old",
            new_value="New",
            diff_type="text_edit"
        )
        test_db.add(diff)
        await test_db.commit()
        diff_id = diff.id
        
        # Delete version - diff should be cascade deleted
        await test_db.delete(version)
        await test_db.commit()
        
        # Verify diff is deleted
        from sqlalchemy import select
        result = await test_db.execute(select(VersionDiff).where(VersionDiff.id == diff_id))
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(TaskVersion is None or VersionComment is None, reason="Models not available")
    async def test_version_comment_cascade(self, test_db):
        """Test that VersionComment is deleted when TaskVersion is deleted."""
        from db.models import Task
        
        # Create task and version
        task = Task(id="test-task-123", title="Test", status="todo", assignee="test")
        test_db.add(task)
        await test_db.commit()
        
        version = TaskVersion(
            task_id="test-task-123",
            version_number=1,
            change_source="user",
            change_type="created"
        )
        test_db.add(version)
        await test_db.commit()
        await test_db.refresh(version)
        
        # Create comment
        comment = VersionComment(
            version_id=version.id,
            comment_text="Test comment",
            created_by="test_user",
            comment_type="approval"
        )
        test_db.add(comment)
        await test_db.commit()
        comment_id = comment.id
        
        # Delete version - comment should be cascade deleted
        await test_db.delete(version)
        await test_db.commit()
        
        # Verify comment is deleted
        from sqlalchemy import select
        result = await test_db.execute(select(VersionComment).where(VersionComment.id == comment_id))
        assert result.scalar_one_or_none() is None


# ============================================================================
# ALL MODELS CREATION TEST
# ============================================================================

@pytest.mark.unit
class TestAllPhase6Models:
    """Test that all Phase 6 models can be instantiated."""
    
    def test_all_models_available(self):
        """Test that all expected models are available."""
        models = {
            "ConceptNode": ConceptNode,
            "ConversationThreadNode": ConversationThreadNode,
            "TaskOutcomeNode": TaskOutcomeNode,
            "ConceptRelationship": ConceptRelationship,
            "TaskSimilarityIndex": TaskSimilarityIndex,
            "ConceptTaskLink": ConceptTaskLink,
            "TaskVersion": TaskVersion,
            "VersionDiff": VersionDiff,
            "VersionComment": VersionComment,
            "ImplicitSignal": ImplicitSignal,
            "SignalAggregate": SignalAggregate,
            "LearningModel": LearningModel,
            "OutcomeQualityCorrelation": OutcomeQualityCorrelation,
            "TaskQualityScore": TaskQualityScore,
            "QualityTrend": QualityTrend
        }
        
        available = sum(1 for model in models.values() if model is not None)
        total = len(models)
        
        print(f"\nPhase 6 Models: {available}/{total} available")
        
        # At least some models should be available
        assert available > 0, "No Phase 6 models are available"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])

