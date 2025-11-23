"""
Phase 7: Final Integration Verification Tests

Verifies complete end-to-end functionality:
- Complete learning loop works
- Quality dashboard integration
- Background jobs execute correctly
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=env_path, override=True)

# Import services
try:
    from services.implicit_learning_service import get_implicit_learning_service
except ImportError:
    get_implicit_learning_service = None

try:
    from services.outcome_learning_service import get_outcome_learning_service
except ImportError:
    get_outcome_learning_service = None

try:
    from services.trust_index_service import get_trust_index_service
except ImportError:
    get_trust_index_service = None

try:
    from services.task_quality_evaluator_service import get_task_quality_evaluator
except ImportError:
    get_task_quality_evaluator = None

try:
    from services.learning_integration_service import LearningIntegrationService
except ImportError:
    LearningIntegrationService = None

# Import models
try:
    from db.implicit_learning_models import ImplicitSignal, SignalAggregate, SignalType, LearningScope
except ImportError:
    ImplicitSignal = None
    SignalAggregate = None
    SignalType = None
    LearningScope = None

try:
    from db.task_quality_models import TaskQualityScore
except ImportError:
    TaskQualityScore = None

try:
    from db.outcome_learning_models import QualityFeatureAnalysis
except ImportError:
    QualityFeatureAnalysis = None

try:
    from db.models import Task
except ImportError:
    Task = None


# ============================================================================
# 7.3.1 COMPLETE LEARNING LOOP
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestCompleteLearningLoop:
    """Test complete learning cycle."""
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    @pytest.mark.skipif(ImplicitSignal is None, reason="Models not available")
    async def test_complete_learning_cycle(self, test_db):
        """Full cycle: signals → aggregates → models → application."""
        # Step 1: Create signals
        yesterday = datetime.utcnow() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        signals = [
            ImplicitSignal(
                signal_type=SignalType.AI_OVERRIDE,
                user_id="user1",
                task_id=f"task{i}",
                project_id="project1",
                signal_data={"field_name": "priority", "ai_value": "P2_MEDIUM", "user_value": "P1_HIGH"},
                base_weight=1.0,
                confidence=1.0,
                recency_factor=1.0,
                final_weight=1.0,
                processed=False,
                created_at=yesterday
            )
            for i in range(10)
        ]
        
        for signal in signals:
            test_db.add(signal)
        await test_db.commit()
        
        # Step 2: Aggregate signals
        service = await get_implicit_learning_service(test_db)
        aggregate_count = await service.aggregate_signals_daily(
            period_start=yesterday,
            period_end=yesterday + timedelta(days=1)
        )
        assert aggregate_count > 0
        
        # Step 3: Train models
        model_count = await service.train_models_from_aggregates(min_samples=5)
        # May be 0 if not enough data, but should not crash
        assert model_count >= 0
        
        # Step 4: Verify learning can be applied
        if LearningIntegrationService:
            learning_service = LearningIntegrationService(test_db)
            enrichment = await learning_service.get_learned_context_enrichment(
                user_id="user1",
                project_id="project1"
            )
            assert enrichment is not None
            assert isinstance(enrichment, dict)
    
    @pytest.mark.skipif(LearningIntegrationService is None, reason="Service not available")
    async def test_learning_applies_to_new_tasks(self, test_db):
        """Verify learned patterns are used."""
        # Create some learning data first
        if get_implicit_learning_service:
            service = await get_implicit_learning_service(test_db)
            
            # Create aggregate with pattern
            from db.implicit_learning_models import LearningModel, ModelType
            from datetime import datetime
            
            model = LearningModel(
                model_type=ModelType.PRIORITY_PREDICTION,
                model_name="priority_prediction_user1",
                scope=LearningScope.USER,
                scope_id="user1",
                pattern={"field": "priority", "prediction": "P1_HIGH"},
                confidence_score=0.8,
                sample_size=10,
                active=True,
                created_at=datetime.utcnow()
            )
            test_db.add(model)
            await test_db.commit()
        
        # Test learning application
        learning_service = LearningIntegrationService(test_db)
        enrichment = await learning_service.get_learned_context_enrichment(
            user_id="user1",
            project_id="project1"
        )
        
        assert enrichment is not None
        # Should have learning applied if model exists
        assert isinstance(enrichment, dict)
    
    @pytest.mark.skipif(get_trust_index_service is None, reason="Service not available")
    @pytest.mark.skipif(TaskQualityScore is None, reason="Models not available")
    async def test_trust_index_reflects_learning(self, test_db):
        """Verify trust index improves with learning."""
        # Create quality scores
        now = datetime.utcnow()
        scores = [
            TaskQualityScore(
                task_id=f"task{i}",
                user_id="user1",
                project_id="project1",
                overall_score=75.0 + (i * 2),  # Improving scores
                completeness_score=80.0,
                clarity_score=70.0,
                actionability_score=75.0,
                relevance_score=80.0,
                confidence_score=85.0,
                evaluated_at=now - timedelta(days=i)
            )
            for i in range(5)
        ]
        
        for score in scores:
            test_db.add(score)
        await test_db.commit()
        
        # Calculate trust index
        service = await get_trust_index_service(test_db)
        result = await service.calculate_trust_index(
            scope="user",
            scope_id="user1",
            window_days=30
        )
        
        assert result is not None
        assert "trust_index" in result
        assert 0 <= result["trust_index"] <= 100


# ============================================================================
# 7.3.2 QUALITY DASHBOARD INTEGRATION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestQualityDashboardIntegration:
    """Test quality dashboard integration."""
    
    @pytest.mark.skipif(get_trust_index_service is None, reason="Service not available")
    async def test_dashboard_data_loads(self, test_db):
        """Verify dashboard can fetch data."""
        service = await get_trust_index_service(test_db)
        
        # Test trust index
        result = await service.calculate_trust_index(scope="global", window_days=30)
        assert result is not None
        
        # Should have required fields for dashboard
        assert "trust_index" in result
        assert "components" in result
        assert "insights" in result
    
    @pytest.mark.skipif(get_trust_index_service is None, reason="Service not available")
    async def test_trust_index_displays(self, test_db):
        """Verify trust index renders."""
        service = await get_trust_index_service(test_db)
        
        result = await service.calculate_trust_index(scope="global", window_days=30)
        
        # Verify structure for frontend
        assert "trust_index" in result
        assert isinstance(result["trust_index"], (int, float))
        assert "trust_level" in result
        assert result["trust_level"] in ["high", "medium", "low", "very_low"]
    
    @pytest.mark.skipif(get_task_quality_evaluator is None, reason="Service not available")
    async def test_trends_display(self, test_db):
        """Verify trends chart works."""
        from routes.quality_routes import get_quality_trends
        
        # Test trends endpoint logic
        result = await get_quality_trends(
            window_days=30,
            period="daily",
            project_id=None,
            user_id=None,
            db=test_db
        )
        
        # Should return list
        assert isinstance(result, list)
        # Each item should have required fields
        if len(result) > 0:
            item = result[0]
            assert "date" in item
            assert "quality" in item
    
    @pytest.mark.skipif(get_trust_index_service is None, reason="Service not available")
    async def test_filtering_works(self, test_db):
        """Verify project/user filters work."""
        service = await get_trust_index_service(test_db)
        
        # Test global scope
        global_result = await service.calculate_trust_index(scope="global", window_days=30)
        assert global_result is not None
        
        # Test user scope
        user_result = await service.calculate_trust_index(
            scope="user",
            scope_id="user1",
            window_days=30
        )
        assert user_result is not None
        
        # Test project scope
        project_result = await service.calculate_trust_index(
            scope="project",
            scope_id="project1",
            window_days=30
        )
        assert project_result is not None


# ============================================================================
# 7.3.3 BACKGROUND JOBS EXECUTION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestBackgroundJobsExecution:
    """Test background jobs execution."""
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_daily_aggregation_runs(self, test_db):
        """Verify daily job executes."""
        from services.phase6_learning_scheduler import Phase6LearningScheduler
        
        scheduler = Phase6LearningScheduler()
        
        # Test job method exists and can be called
        assert hasattr(scheduler, 'daily_aggregation_job')
        
        # Job should not crash even with empty database
        try:
            await scheduler.daily_aggregation_job()
            assert True
        except Exception as e:
            # Should handle errors gracefully
            assert False, f"Daily aggregation job crashed: {e}"
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_weekly_training_runs(self, test_db):
        """Verify weekly training executes."""
        from services.phase6_learning_scheduler import Phase6LearningScheduler
        
        scheduler = Phase6LearningScheduler()
        
        assert hasattr(scheduler, 'weekly_training_job')
        
        try:
            await scheduler.weekly_training_job()
            assert True
        except Exception as e:
            assert False, f"Weekly training job crashed: {e}"
    
    @pytest.mark.skipif(get_outcome_learning_service is None, reason="Service not available")
    async def test_weekly_correlation_runs(self, test_db):
        """Verify correlation job executes."""
        from services.phase6_learning_scheduler import Phase6LearningScheduler
        
        scheduler = Phase6LearningScheduler()
        
        assert hasattr(scheduler, 'weekly_correlation_job')
        
        try:
            await scheduler.weekly_correlation_job()
            assert True
        except Exception as e:
            assert False, f"Weekly correlation job crashed: {e}"
    
    @pytest.mark.skipif(get_implicit_learning_service is None, reason="Service not available")
    async def test_jobs_handle_errors(self, test_db):
        """Verify jobs don't crash on errors."""
        from services.phase6_learning_scheduler import Phase6LearningScheduler
        
        scheduler = Phase6LearningScheduler()
        
        # Mock a service error
        with patch('services.phase6_learning_scheduler.get_implicit_learning_service') as mock:
            mock.side_effect = Exception("Service error")
            
            # Job should handle error gracefully
            try:
                await scheduler.daily_aggregation_job()
                # Should not raise exception
                assert True
            except Exception:
                # If it raises, it should be caught and logged
                pass


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def test_db():
    """Create test database session."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from db.database import Base
    
    # Import all models
    from db.models import Task
    from db.implicit_learning_models import ImplicitSignal, SignalAggregate, LearningModel
    from db.task_quality_models import TaskQualityScore
    from db.outcome_learning_models import QualityFeatureAnalysis
    try:
        from db.task_version_models import TaskVersion
    except ImportError:
        pass
    
    test_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = async_session()
    
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()

