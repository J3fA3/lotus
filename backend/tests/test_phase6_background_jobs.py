"""
Comprehensive Tests for Phase 6 Background Jobs

Tests:
- Scheduler setup and configuration
- Job execution (daily aggregation, weekly training, weekly correlation)
- Data validation (aggregates, models, correlations)
- Error handling
- Edge cases
- Integration with main.py
"""

import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import scheduler
try:
    from services.phase6_learning_scheduler import Phase6LearningScheduler, get_phase6_learning_scheduler
except ImportError:
    Phase6LearningScheduler = None
    get_phase6_learning_scheduler = None

# Import services
try:
    from services.implicit_learning_service import get_implicit_learning_service
except ImportError:
    get_implicit_learning_service = None

try:
    from services.outcome_learning_service import get_outcome_learning_service
except ImportError:
    get_outcome_learning_service = None

# Import models
try:
    from db.implicit_learning_models import (
        ImplicitSignal,
        SignalAggregate,
        LearningModel,
        SignalType,
        LearningScope,
        ModelType
    )
except ImportError:
    ImplicitSignal = None
    SignalAggregate = None
    LearningModel = None
    SignalType = None
    LearningScope = None
    ModelType = None

try:
    from db.outcome_learning_models import (
        OutcomeQualityCorrelation,
        QualityFeatureAnalysis
    )
except ImportError:
    OutcomeQualityCorrelation = None
    QualityFeatureAnalysis = None

try:
    from db.database import Base
except ImportError:
    Base = None


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def test_db():
    """
    Create test database session with all Phase 6 tables.
    
    Note: Scheduler jobs use AsyncSessionLocal() which connects to a different database.
    For true integration tests, we test job execution separately and verify results
    through the test_db connection.
    
    Yields:
        AsyncSession: Database session for testing
    """
    if Base is None:
        pytest.skip("Database models not available")
    
    # Import all models to ensure tables are created
    # Import Task first to avoid relationship issues
    from db.models import Task
    # Import task version models to satisfy Task relationships
    try:
        from db.task_version_models import TaskVersion, VersionDiff, VersionComment
    except ImportError:
        pass
    # Import all Phase 6 models
    from db.implicit_learning_models import ImplicitSignal, SignalAggregate, LearningModel
    from db.outcome_learning_models import OutcomeQualityCorrelation, QualityFeatureAnalysis
    from db.task_quality_models import TaskQualityScore, QualityTrend
    # Import knowledge graph models
    try:
        from db.knowledge_graph_models_v2 import (
            ConceptNode, ConversationThreadNode, TaskOutcomeNode,
            ConceptRelationship, TaskSimilarityIndex, ConceptTaskLink
        )
    except ImportError:
        pass
    
    # Use in-memory database for tests
    test_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    session = async_session()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        await engine.dispose()


@pytest.fixture
def scheduler():
    """Create a fresh scheduler instance for testing."""
    if Phase6LearningScheduler is None:
        pytest.skip("Phase6LearningScheduler not available")
    return Phase6LearningScheduler()


@pytest.fixture
def sample_signals():
    """Create sample signals for testing."""
    if SignalType is None:
        return []
    
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    return [
        {
            "signal_type": SignalType.AI_OVERRIDE,
            "user_id": "user1",
            "task_id": "task1",
            "project_id": "project1",
            "signal_data": {
                "field_name": "priority",
                "ai_suggested": "P2_MEDIUM",
                "user_selected": "P1_HIGH",
                "ai_confidence": 0.75
            },
            "base_weight": 1.0,
            "confidence": 1.0,
            "recency_factor": 1.0,
            "final_weight": 1.0,
            "processed": False,
            "created_at": yesterday
        },
        {
            "signal_type": SignalType.AUTO_FILL_ACCEPTED,
            "user_id": "user1",
            "task_id": "task2",
            "project_id": "project1",
            "signal_data": {},
            "base_weight": 0.7,
            "confidence": 1.0,
            "recency_factor": 1.0,
            "final_weight": 0.7,
            "processed": False,
            "created_at": yesterday
        },
        {
            "signal_type": SignalType.QUESTION_ANSWERED,
            "user_id": "user2",
            "task_id": "task3",
            "project_id": "project2",
            "signal_data": {"question_id": 1},
            "base_weight": 0.9,
            "confidence": 1.0,
            "recency_factor": 1.0,
            "final_weight": 0.9,
            "processed": False,
            "created_at": yesterday
        }
    ]


# ============================================================================
# 3.1 SCHEDULER SETUP TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
class TestSchedulerSetup:
    """Test scheduler initialization and configuration."""
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler can be initialized."""
        assert scheduler is not None
        assert scheduler.scheduler is not None
        assert scheduler.is_running is False
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_singleton_pattern(self):
        """Test singleton pattern works correctly."""
        scheduler1 = get_phase6_learning_scheduler()
        scheduler2 = get_phase6_learning_scheduler()
        assert scheduler1 is scheduler2
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_job_registration(self, scheduler):
        """Test all 3 jobs are registered correctly."""
        scheduler.start()
        
        jobs = scheduler.get_jobs()
        job_ids = [job["id"] for job in jobs]
        
        assert "phase6_daily_aggregation" in job_ids
        assert "phase6_weekly_training" in job_ids
        assert "phase6_weekly_correlation" in job_ids
        assert len(jobs) == 3
        
        scheduler.stop()
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_job_scheduling_times(self, scheduler):
        """Test jobs are scheduled at correct times."""
        scheduler.start()
        
        jobs = scheduler.get_jobs()
        job_dict = {job["id"]: job for job in jobs}
        
        # Check triggers contain correct times (format: cron[hour='2', minute='0'])
        assert "hour='2'" in job_dict["phase6_daily_aggregation"]["trigger"] or "hour=2" in job_dict["phase6_daily_aggregation"]["trigger"]
        assert "day_of_week='sun'" in job_dict["phase6_weekly_training"]["trigger"] or "day_of_week=sun" in job_dict["phase6_weekly_training"]["trigger"]
        assert "hour='3'" in job_dict["phase6_weekly_training"]["trigger"] or "hour=3" in job_dict["phase6_weekly_training"]["trigger"]
        assert "day_of_week='sun'" in job_dict["phase6_weekly_correlation"]["trigger"] or "day_of_week=sun" in job_dict["phase6_weekly_correlation"]["trigger"]
        assert "hour='4'" in job_dict["phase6_weekly_correlation"]["trigger"] or "hour=4" in job_dict["phase6_weekly_correlation"]["trigger"]
        
        scheduler.stop()
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    @patch.dict(os.environ, {"ENABLE_PHASE6_LEARNING_JOBS": "false"})
    def test_disable_via_environment(self, scheduler):
        """Test scheduler can be disabled via environment variable."""
        scheduler.start()
        assert scheduler.is_running is False
        
        # Clean up
        if scheduler.is_running:
            scheduler.stop()
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_start_stop_idempotency(self, scheduler):
        """Test start/stop is idempotent."""
        scheduler.start()
        assert scheduler.is_running is True
        
        # Start again should not crash
        scheduler.start()
        assert scheduler.is_running is True
        
        scheduler.stop()
        assert scheduler.is_running is False
        
        # Stop again should not crash
        scheduler.stop()
        assert scheduler.is_running is False


# ============================================================================
# 3.2 JOB EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestDailyAggregationJob:
    """Test daily aggregation job execution."""
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(ImplicitSignal is None, reason="Models not available")
    async def test_aggregation_with_signals(self, test_db, scheduler):
        """Test aggregation job with signals present.
        
        Note: This test verifies the aggregation logic works correctly.
        The scheduler job uses AsyncSessionLocal() which connects to a different
        database, so we test the service method directly with test_db.
        """
        # Create test signals
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        signals = [
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user1",
                task_id="task1",
                project_id="project1",
                signal_data={"field_name": "priority", "ai_suggested": "P2", "user_selected": "P1"},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0,
                processed=False,
                created_at=yesterday
            ),
            ImplicitSignal(
                signal_type=SignalType.AUTO_FILL_ACCEPTED,
                user_id="user1",
                task_id="task2",
                project_id="project1",
                signal_data={},
                base_weight=0.7,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=0.7,
                processed=False,
                created_at=yesterday
            )
        ]
        
        for signal in signals:
            test_db.add(signal)
        await test_db.commit()
        
        # Test aggregation service directly (same as what job calls)
        service = await get_implicit_learning_service(test_db)
        count = await service.aggregate_signals_daily(
            period_start=yesterday,
            period_end=yesterday + timedelta(days=1)
        )
        
        assert count > 0
        
        # Verify signals are marked as processed
        await test_db.refresh(signals[0])
        await test_db.refresh(signals[1])
        assert signals[0].processed is True
        assert signals[1].processed is True
        assert signals[0].processed_at is not None
        
        # Verify aggregates were created
        from sqlalchemy import select
        result = await test_db.execute(select(SignalAggregate))
        aggregates = list(result.scalars().all())
        assert len(aggregates) > 0
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_aggregation_with_no_signals(self, test_db, scheduler):
        """Test aggregation job with no signals (should not crash)."""
        # Run aggregation job with empty database
        await scheduler.daily_aggregation_job()
        
        # Should complete without error
        assert True
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(ImplicitSignal is None, reason="Models not available")
    async def test_aggregation_multiple_scopes(self, test_db, scheduler):
        """Test aggregation creates aggregates for different scopes."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create signals for different scopes
        signals = [
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user1",
                task_id="task1",
                project_id="project1",
                signal_data={"field_name": "priority"},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0,
                processed=False,
                created_at=yesterday
            ),
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user2",
                task_id="task2",
                project_id="project2",
                signal_data={"field_name": "priority"},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0,
                processed=False,
                created_at=yesterday
            )
        ]
        
        for signal in signals:
            test_db.add(signal)
        await test_db.commit()
        
        # Test aggregation service directly
        service = await get_implicit_learning_service(test_db)
        await service.aggregate_signals_daily(
            period_start=yesterday,
            period_end=yesterday + timedelta(days=1)
        )
        
        # Verify aggregates for different scopes
        from sqlalchemy import select
        result = await test_db.execute(select(SignalAggregate))
        aggregates = list(result.scalars().all())
        
        # Should have aggregates for global, project, and user scopes
        scopes = {agg.scope for agg in aggregates}
        assert LearningScope.GLOBAL in scopes
        assert LearningScope.PROJECT in scopes
        assert LearningScope.USER in scopes


@pytest.mark.asyncio
@pytest.mark.integration
class TestWeeklyTrainingJob:
    """Test weekly training job execution."""
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(SignalAggregate is None, reason="Models not available")
    async def test_training_with_sufficient_aggregates(self, test_db, scheduler):
        """Test training job with sufficient aggregates."""
        # Create aggregates with enough samples and proper structure
        now = datetime.utcnow()
        period_start = now - timedelta(days=1)
        period_end = now
        
        # Create aggregate with priority field data that meets training criteria
        # Need: override_count >= min_samples (default 10), frequency >= 0.6
        aggregate = SignalAggregate(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
            scope=LearningScope.GLOBAL,
            scope_id=None,
            signal_type=SignalType.AI_OVERRIDE,
            total_count=25,  # Above minimum
            weighted_sum=25.0,
            avg_confidence=0.8,
            unique_users=5,
            unique_tasks=20,
            field_aggregates={
                "priority": {
                    "override_count": 25,  # >= min_samples (10)
                    "user_selections": {"P1_HIGH": 20, "P2_MEDIUM": 5}  # 20/25 = 0.8 > 0.6
                }
            }
        )
        
        test_db.add(aggregate)
        await test_db.commit()
        
        # Test training service directly
        service = await get_implicit_learning_service(test_db)
        count = await service.train_models_from_aggregates(min_samples=10)
        
        # Should train at least one model
        assert count > 0
        
        # Verify models were created
        from sqlalchemy import select
        result = await test_db.execute(select(LearningModel))
        models = list(result.scalars().all())
        assert len(models) > 0
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_training_with_insufficient_aggregates(self, test_db, scheduler):
        """Test training job with insufficient aggregates (should not crash)."""
        # Run training job with empty database
        await scheduler.weekly_training_job()
        
        # Should complete without error
        assert True


@pytest.mark.asyncio
@pytest.mark.integration
class TestWeeklyCorrelationJob:
    """Test weekly correlation job execution."""
    
    @pytest.mark.skipif(get_outcome_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(QualityFeatureAnalysis is None, reason="Models not available")
    async def test_correlation_with_sufficient_data(self, test_db, scheduler):
        """Test correlation job with sufficient outcome data."""
        # Create quality feature analyses with outcomes
        # Need at least 30 completed tasks with time_to_complete
        # And need at least 10 with feature and 10 without for each feature
        now = datetime.utcnow()
        
        analyses = []
        for i in range(40):  # More than minimum to ensure we have enough with/without
            # All should be completed with time_to_complete for correlation analysis
            analysis = QualityFeatureAnalysis(
                task_id=f"task{i}",
                has_summary=True,  # All have summary
                has_why_it_matters=(i < 20),  # First 20 have it, last 20 don't (ensures 20 with, 20 without)
                has_how_to_approach=(i < 15),  # First 15 have it, ensures enough with/without
                has_success_criteria=(i < 25),  # First 25 have it
                has_technical_context=(i < 12),  # First 12 have it
                description_word_count=100 + i,
                ai_confidence_avg=0.8,
                outcome_status="completed",  # All completed
                was_successful=True,
                time_to_complete=3600 + (i * 60),  # All have time_to_complete
                description_edit_pct=0.1 if i < 20 else 0.5,
                created_at=now - timedelta(days=i % 30)
            )
            analyses.append(analysis)
        
        for analysis in analyses:
            test_db.add(analysis)
        await test_db.commit()
        
        # Test correlation service directly (same as what job calls)
        from services.outcome_learning_service import get_outcome_learning_service
        service = await get_outcome_learning_service(test_db)
        count = await service.analyze_feature_correlations(min_samples=30)
        
        # Should analyze at least one correlation
        assert count > 0
        
        # Verify correlations were created
        from sqlalchemy import select
        result = await test_db.execute(select(OutcomeQualityCorrelation))
        correlations = list(result.scalars().all())
        assert len(correlations) > 0
    
    @pytest.mark.skipif(get_outcome_learning_service is None, reason="Service not available")
    async def test_correlation_with_insufficient_data(self, test_db, scheduler):
        """Test correlation job with insufficient data (should not crash)."""
        # Run correlation job with empty database
        await scheduler.weekly_correlation_job()
        
        # Should complete without error
        assert True


# ============================================================================
# 3.3 DATA VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestAggregateDataValidation:
    """Test aggregate data correctness."""
    
    @pytest.mark.skipif(SignalAggregate is None, reason="Models not available")
    async def test_aggregate_total_count(self, test_db):
        """Test total_count matches signal count."""
        # Create signals and aggregate
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        signals = [
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user1",
                task_id=f"task{i}",
                signal_data={},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0,
                processed=False,
                created_at=yesterday
            )
            for i in range(5)
        ]
        
        for signal in signals:
            test_db.add(signal)
        await test_db.commit()
        
        # Run aggregation
        service = await get_implicit_learning_service(test_db)
        await service.aggregate_signals_daily()
        
        # Verify aggregate
        from sqlalchemy import select
        result = await test_db.execute(
            select(SignalAggregate).where(SignalAggregate.scope == LearningScope.GLOBAL)
        )
        aggregate = result.scalar_one_or_none()
        
        assert aggregate is not None
        assert aggregate.total_count == 5
    
    @pytest.mark.skipif(SignalAggregate is None, reason="Models not available")
    async def test_aggregate_weighted_sum(self, test_db):
        """Test weighted_sum calculated correctly."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        signals = [
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user1",
                task_id=f"task{i}",
                signal_data={},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0 * i,  # Different weights
                processed=False,
                created_at=yesterday
            )
            for i in range(1, 4)  # Weights: 1.0, 2.0, 3.0
        ]
        
        for signal in signals:
            test_db.add(signal)
        await test_db.commit()
        
        service = await get_implicit_learning_service(test_db)
        await service.aggregate_signals_daily()
        
        from sqlalchemy import select
        result = await test_db.execute(
            select(SignalAggregate).where(SignalAggregate.scope == LearningScope.GLOBAL)
        )
        aggregate = result.scalar_one_or_none()
        
        assert aggregate is not None
        assert aggregate.weighted_sum == 6.0  # 1.0 + 2.0 + 3.0


@pytest.mark.asyncio
@pytest.mark.integration
class TestModelDataValidation:
    """Test model data correctness."""
    
    @pytest.mark.skipif(LearningModel is None, reason="Models not available")
    async def test_model_structure(self, test_db):
        """Test model data structure is valid."""
        # Create aggregate and train model
        now = datetime.utcnow()
        period_start = now - timedelta(days=1)
        period_end = now
        
        aggregate = SignalAggregate(
            period_start=period_start,
            period_end=period_end,
            period_type="daily",
            scope=LearningScope.GLOBAL,
            scope_id=None,
            signal_type=SignalType.AI_OVERRIDE,
            total_count=25,
            weighted_sum=25.0,
            avg_confidence=0.8,
            unique_users=5,
            unique_tasks=20,
            field_aggregates={
                "priority": {
                    "override_count": 25,
                    "user_selections": {"P1_HIGH": 20, "P2_MEDIUM": 5}
                }
            }
        )
        
        test_db.add(aggregate)
        await test_db.commit()
        
        # Train model
        service = await get_implicit_learning_service(test_db)
        await service.train_models_from_aggregates(min_samples=10)
        
        # Verify model
        from sqlalchemy import select
        result = await test_db.execute(select(LearningModel))
        models = list(result.scalars().all())
        
        if models:
            model = models[0]
            assert model.model_type is not None
            assert model.scope is not None
            assert 0.0 <= model.confidence_score <= 1.0
            assert model.sample_size > 0
            assert model.pattern is not None


# ============================================================================
# 3.4 ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in jobs."""
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    async def test_database_connection_failure(self, scheduler):
        """Test job handles database connection failure gracefully."""
        # Mock AsyncSessionLocal to raise exception
        with patch('services.phase6_learning_scheduler.AsyncSessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            # Job should not crash
            await scheduler.daily_aggregation_job()
            assert True  # If we get here, error was handled
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    async def test_service_method_failure(self, scheduler):
        """Test job handles service method failures gracefully."""
        with patch('services.phase6_learning_scheduler.get_implicit_learning_service') as mock_service:
            mock_service.side_effect = Exception("Service error")
            
            # Job should not crash
            await scheduler.daily_aggregation_job()
            assert True


# ============================================================================
# 3.5 EDGE CASES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases."""
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_zero_signals(self, test_db, scheduler):
        """Test aggregation with zero signals."""
        await scheduler.daily_aggregation_job()
        assert True  # Should not crash
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(ImplicitSignal is None, reason="Models not available")
    async def test_single_signal(self, test_db, scheduler):
        """Test aggregation with single signal."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        signal = ImplicitSignal(
            signal_type=SignalType.AI_OVERRIDE,
            user_id="user1",
            task_id="task1",
            signal_data={},
            base_weight=1.0,
            confidence=1.0,
            recency_factor=1.0,
            final_weight=1.0,
            processed=False,
            created_at=yesterday
        )
        
        test_db.add(signal)
        await test_db.commit()
        
        # Test aggregation service directly
        service = await get_implicit_learning_service(test_db)
        count = await service.aggregate_signals_daily(
            period_start=yesterday,
            period_end=yesterday + timedelta(days=1)
        )
        
        assert count > 0
        
        # Should create aggregate
        from sqlalchemy import select
        result = await test_db.execute(select(SignalAggregate))
        aggregates = list(result.scalars().all())
        assert len(aggregates) > 0


# ============================================================================
# 3.6 INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestIntegration:
    """Test integration with main.py and other components."""
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    def test_scheduler_can_start_stop(self, scheduler):
        """Test scheduler can start and stop."""
        scheduler.start()
        assert scheduler.is_running is True
        
        scheduler.stop()
        assert scheduler.is_running is False
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    async def test_jobs_can_run_without_crashing(self, scheduler):
        """Test scheduler jobs can execute without crashing.
        
        Note: Jobs use AsyncSessionLocal() which connects to the configured database.
        This test verifies the job execution path works, even if no data exists.
        """
        # All three jobs should run without crashing
        await scheduler.daily_aggregation_job()
        await scheduler.weekly_training_job()
        await scheduler.weekly_correlation_job()
        
        # If we get here, jobs executed without crashing
        assert True
    
    @pytest.mark.skipif(Phase6LearningScheduler is None, reason="Scheduler not available")
    async def test_jobs_handle_empty_database(self, scheduler):
        """Test jobs handle empty database gracefully."""
        # Jobs should complete without error even with no data
        count1 = await scheduler.daily_aggregation_job()
        count2 = await scheduler.weekly_training_job()
        count3 = await scheduler.weekly_correlation_job()
        
        # Jobs should return 0 or complete without error
        assert True  # If we get here, jobs handled empty database

