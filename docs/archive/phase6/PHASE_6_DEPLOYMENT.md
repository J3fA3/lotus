# Phase 6: Cognitive Nexus - Deployment & Testing Guide

**Status**: Complete (30/30 steps)
**Version**: 1.0
**Last Updated**: 2025-11-22

## Overview

Phase 6 implements a **Living Task Intelligence & Self-Learning System** that makes the AI progressively smarter through evidence-based learning and transparent quality metrics.

### Six Stages

1. **Knowledge Graph Evolution** (Steps 1-6): Conceptual understanding with temporal tracking
2. **Contextual Task Synthesis** (Steps 7-12): AI-powered intelligent task descriptions
3. **Intelligent Updates** (Steps 13-18): Version control with PR-style change tracking
4. **Contextual Questions** (Steps 19-22): Smart question queue with batching
5. **Implicit Learning** (Steps 23-26): Self-learning from user behavior and outcomes
6. **Quality Evaluation** (Steps 27-30): Transparent quality metrics and trust index

---

## Database Migrations

### Migration Status

**Total Migrations**: 11
**All migrations must be run in order.**

| #   | Migration File                              | Description                                    |
|-----|---------------------------------------------|------------------------------------------------|
| 001 | `001_add_knowledge_graph.py`                | KG evolution with temporal concepts            |
| 002 | `002_add_task_synthesis.py`                 | Intelligent task descriptions                  |
| 003 | `003_add_task_versions.py`                  | Version control for tasks                      |
| 004 | `004_add_change_comments.py`                | PR-style change comments                       |
| 005 | `005_add_contextual_questions.py`           | Question queue system                          |
| 006 | `006_add_question_batches.py`               | Smart batching for questions                   |
| 007 | `007_add_question_priority.py`              | Priority-based question ranking                |
| 008 | `008_add_task_outcomes.py`                  | Task outcome tracking                          |
| 009 | `009_add_implicit_learning.py`              | Implicit signal capture & learning models      |
| 010 | `010_add_outcome_learning.py`               | Outcome-based learning priority                |
| 011 | `011_add_task_quality.py`                   | Quality scores & trends                        |

### Running Migrations

```bash
# Run all migrations
cd backend/db/migrations

python 001_add_knowledge_graph.py
python 002_add_task_synthesis.py
python 003_add_task_versions.py
python 004_add_change_comments.py
python 005_add_contextual_questions.py
python 006_add_question_batches.py
python 007_add_question_priority.py
python 008_add_task_outcomes.py
python 009_add_implicit_learning.py
python 010_add_outcome_learning.py
python 011_add_task_quality.py
```

### Verify Database Schema

After running all migrations, verify the database has **15 tables total**:

```bash
# Check tables
sqlite3 tasks.db ".tables"
```

Expected tables:
- `knowledge_graph_concepts` (KG)
- `concept_temporal_states` (KG)
- `intelligent_task_descriptions` (Synthesis)
- `task_versions` (Updates)
- `task_change_comments` (Updates)
- `contextual_questions` (Questions)
- `question_batches` (Questions)
- `question_priority_scores` (Questions)
- `task_outcomes` (Outcomes)
- `implicit_signals` (Learning)
- `signal_aggregates` (Learning)
- `learning_models` (Learning)
- `outcome_quality_correlations` (Learning)
- `task_quality_scores` (Quality)
- `quality_trends` (Quality)

---

## Backend Services

### Service Layer Architecture

All services follow the **factory function pattern** for dependency injection:

```python
from db.database import get_db
from services.service_name import get_service_name

async with get_db() as db:
    service = await get_service_name(db)
    result = await service.method()
```

### Core Services

| Service                            | Purpose                                        | Key Methods                                      |
|------------------------------------|------------------------------------------------|--------------------------------------------------|
| `kg_evolution_service.py`          | Knowledge graph management                     | `create_concept`, `evolve_concept`               |
| `contextual_task_synthesizer.py`   | AI-powered task synthesis                      | `synthesize_description`                         |
| `task_version_service.py`          | Version control                                | `create_version`, `get_version_timeline`         |
| `contextual_question_engine.py`    | Question generation                            | `generate_questions`                             |
| `question_batch_service.py`        | Question batching                              | `create_batch`, `answer_batch`                   |
| `implicit_learning_service.py`     | Signal capture & learning                      | `capture_signal`, `train_models_from_aggregates` |
| `outcome_learning_service.py`      | Outcome correlation analysis                   | `analyze_feature_correlations`                   |
| `learning_integration_service.py`  | Apply learning to synthesis                    | `get_learned_context_enrichment`                 |
| `task_quality_evaluator_service.py`| Quality evaluation                             | `evaluate_task_quality`                          |
| `trust_index_service.py`           | Trust metric calculation                       | `calculate_trust_index`                          |

---

## API Routes

### Quality Evaluation Routes

Add to `backend/main.py`:

```python
from routes.quality_routes import router as quality_router

app.include_router(quality_router)
```

### Available Endpoints

| Method | Endpoint                        | Description                         |
|--------|---------------------------------|-------------------------------------|
| GET    | `/api/quality/trust-index`      | Get trust index (with filters)      |
| GET    | `/api/quality/trends`           | Get quality trends over time        |
| GET    | `/api/quality/task/{task_id}`   | Get task quality score              |
| POST   | `/api/quality/evaluate/{task_id}` | Trigger task evaluation           |
| GET    | `/api/quality/recent`           | Get recent quality scores           |

### Example API Calls

```bash
# Get global trust index (last 30 days)
curl "http://localhost:8000/api/quality/trust-index?window_days=30"

# Get quality trends (daily, last 7 days)
curl "http://localhost:8000/api/quality/trends?window_days=7&period=daily"

# Evaluate a task
curl -X POST "http://localhost:8000/api/quality/evaluate/task-123"

# Get recent quality scores
curl "http://localhost:8000/api/quality/recent?limit=10"
```

---

## Background Jobs

### Required Scheduled Jobs

Phase 6 requires background jobs for learning and quality tracking.

#### 1. Daily Aggregation (Implicit Learning)

**Frequency**: Every day at 2 AM
**Service**: `ImplicitLearningService.aggregate_signals_daily()`
**Purpose**: Roll up raw signals into aggregates

```python
# Example cron job (using APScheduler or similar)
from services.implicit_learning_service import get_implicit_learning_service

async def daily_aggregation_job():
    async with get_db() as db:
        service = await get_implicit_learning_service(db)
        count = await service.aggregate_signals_daily()
        print(f"Aggregated {count} signals")
```

#### 2. Weekly Training (Pattern Extraction)

**Frequency**: Every Sunday at 3 AM
**Service**: `ImplicitLearningService.train_models_from_aggregates()`
**Purpose**: Extract patterns and train learning models

```python
async def weekly_training_job():
    async with get_db() as db:
        service = await get_implicit_learning_service(db)
        count = await service.train_models_from_aggregates(min_samples=20)
        print(f"Trained {count} models")
```

#### 3. Weekly Correlation Analysis (Outcome Learning)

**Frequency**: Every Sunday at 4 AM
**Service**: `OutcomeLearningService.analyze_feature_correlations()`
**Purpose**: Correlate features with outcomes

```python
async def weekly_correlation_job():
    async with get_db() as db:
        service = await get_outcome_learning_service(db)
        count = await service.analyze_feature_correlations(min_samples=30)
        print(f"Analyzed {count} feature correlations")
```

#### 4. Quality Trend Calculation (Optional)

**Frequency**: Daily at 1 AM
**Purpose**: Pre-calculate quality trends for dashboard performance

### Setting Up Cron Jobs

Example using Python APScheduler:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Daily aggregation at 2 AM
scheduler.add_job(
    daily_aggregation_job,
    'cron',
    hour=2,
    minute=0
)

# Weekly training at 3 AM on Sundays
scheduler.add_job(
    weekly_training_job,
    'cron',
    day_of_week='sun',
    hour=3,
    minute=0
)

# Weekly correlation analysis at 4 AM on Sundays
scheduler.add_job(
    weekly_correlation_job,
    'cron',
    day_of_week='sun',
    hour=4,
    minute=0
)

scheduler.start()
```

---

## Frontend Integration

### Quality Dashboard Component

**Location**: `src/components/QualityDashboard.tsx`
**API Client**: `src/api/quality.ts`

### Usage Example

```tsx
import { QualityDashboard } from "@/components/QualityDashboard";

// In your app
<QualityDashboard
  windowDays={30}
  projectId={currentProject.id}  // Optional
  userId={currentUser.id}         // Optional
/>
```

### Adding to Navigation

Add to your app's navigation:

```tsx
import { BarChart3 } from "lucide-react";

// Navigation item
{
  path: "/quality",
  label: "Quality Dashboard",
  icon: <BarChart3 className="h-4 w-4" />,
  component: <QualityDashboard />
}
```

---

## Testing

### End-to-End Test Scenarios

#### Scenario 1: Complete Learning Loop

**Purpose**: Verify the full learning cycle

1. **Create task** with AI synthesis
2. **User overrides** AI suggestion (signal captured)
3. **User answers** questions (signal captured)
4. **Task completed** (outcome tracked)
5. **Run aggregation** job (next day)
6. **Run training** job (next week)
7. **Create new task** - verify learned patterns applied
8. **Check quality** dashboard - verify trust index

**Expected Results**:
- Signals captured in `implicit_signals` table
- Aggregates created in `signal_aggregates` table
- Learning models trained in `learning_models` table
- Outcome correlations in `outcome_quality_correlations` table
- Quality scores in `task_quality_scores` table
- Trust index reflects learning impact

#### Scenario 2: Quality Evaluation

**Purpose**: Verify quality evaluation works

1. **Create task** with synthesis
2. **Trigger evaluation** via API
3. **Check quality score** returned
4. **View in dashboard**
5. **Verify suggestions** are actionable

**Expected Results**:
- Quality score 0-100 with tier classification
- 5 dimension scores (completeness, clarity, actionability, relevance, confidence)
- Actionable suggestions with severity and impact
- Strengths identified

#### Scenario 3: Trust Index Calculation

**Purpose**: Verify trust index components

1. **Create 10+ tasks** with varied quality
2. **Generate user interactions** (edits, overrides, questions)
3. **Complete some tasks** (outcomes)
4. **Calculate trust index** via API
5. **Verify components**:
   - Quality consistency (avg quality, variance)
   - User engagement (acceptance rate, edit rate)
   - Outcome success (completion rate, time)
   - System performance (evaluation time)

**Expected Results**:
- Trust index 0-100 with level (high/medium/low/very_low)
- All 4 components calculated
- Insights generated (strengths, weaknesses, recommendations)

### Unit Test Examples

```python
# Test quality evaluation
async def test_quality_evaluator():
    evaluator = TaskQualityEvaluatorService(db)

    task_description = {
        "summary": "Test task",
        "why_it_matters": "Important for testing",
        "how_to_approach": "1. Step one\n2. Step two\n3. Step three",
        "success_criteria": "Tests pass",
        "technical_context": "Python 3.11"
    }

    result = await evaluator.evaluate_task_quality(
        task_id="test-123",
        intelligent_description=task_description
    )

    assert result["overall_score"] > 0
    assert result["quality_tier"] in ["excellent", "good", "fair", "needs_improvement"]
    assert len(result["suggestions"]) >= 0

# Test trust index
async def test_trust_index():
    trust_service = TrustIndexService(db)

    result = await trust_service.calculate_trust_index(
        scope="global",
        window_days=30
    )

    assert 0 <= result["trust_index"] <= 100
    assert result["trust_level"] in ["high", "medium", "low", "very_low"]
    assert len(result["components"]) == 4
```

---

## Performance Considerations

### Caching

**Learning Integration Service** uses in-memory caching:
- **Cache TTL**: 10 minutes
- **Max entries**: 1000
- **Eviction**: Oldest first

For production, consider upgrading to **Redis**:

```python
# Replace in-memory cache with Redis
import redis.asyncio as redis

class LearningIntegrationService:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.CACHE_TTL_SECONDS = 600

    async def _get_from_cache(self, key):
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def _set_in_cache(self, key, value):
        await self.redis.setex(
            key,
            self.CACHE_TTL_SECONDS,
            json.dumps(value)
        )
```

### Database Indexes

All critical queries have composite indexes:
- `idx_signal_type_time` on `implicit_signals`
- `idx_task_evaluated` on `task_quality_scores`
- `idx_priority_active` on `learning_models`

Verify indexes exist:

```sql
SELECT name FROM sqlite_master WHERE type='index';
```

### Query Optimization

**Heavy queries** are run as background jobs, not on-demand:
- Signal aggregation (daily)
- Model training (weekly)
- Correlation analysis (weekly)

---

## Monitoring & Observability

### Key Metrics to Monitor

1. **Learning Health**:
   - Signal capture rate (signals/day)
   - Model training frequency (last trained timestamp)
   - Learning application rate (% of tasks using learned patterns)

2. **Quality Metrics**:
   - Average quality score (target: >75)
   - Quality variance (target: <100)
   - Excellent/good percentage (target: >60%)

3. **Trust Index**:
   - Overall trust index (target: >70)
   - Trust trend (should be "improving" or "stable")

4. **System Performance**:
   - Synthesis time (target: <2s)
   - Evaluation time (target: <50ms)
   - Question generation time (target: <1s)

### Logging

All services use Python's `logging` module:

```python
import logging

logger = logging.getLogger(__name__)

# Log levels used:
logger.info("Signal captured: {signal_type}")    # Normal operations
logger.warning("Low sample size: {count}")        # Potential issues
logger.error("Failed to train model: {error}")   # Errors (with graceful degradation)
```

Set logging level in production:

```python
logging.basicConfig(level=logging.INFO)
```

---

## Environment Variables

### Required Variables

```bash
# Database
DATABASE_URL="sqlite+aiosqlite:///./tasks.db"

# AI Provider (Gemini)
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-2.0-flash-exp"

# Learning Configuration
LEARNING_MIN_SAMPLES=10              # Minimum samples for model training
LEARNING_CONFIDENCE_THRESHOLD=0.6    # Minimum confidence for pattern application
LEARNING_CACHE_TTL=600               # Cache TTL in seconds (10 min)

# Quality Evaluation
QUALITY_MIN_SAMPLES=30               # Minimum samples for correlation analysis
QUALITY_CONFIDENCE_THRESHOLD=0.8     # High confidence threshold

# Background Jobs
ENABLE_BACKGROUND_JOBS=true          # Enable scheduled jobs
JOB_TIMEZONE="UTC"                   # Timezone for job scheduling
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All 11 migrations run successfully
- [ ] Database has 15 tables
- [ ] All environment variables configured
- [ ] Gemini API key valid
- [ ] Background jobs configured
- [ ] Redis configured (if using)

### Deployment Steps

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend**:
   ```bash
   npm install
   npm run build
   npm run start
   ```

3. **Background Jobs**:
   ```bash
   python background_jobs.py  # APScheduler
   ```

### Post-Deployment Verification

- [ ] API health check: `GET /api/health`
- [ ] Quality endpoints responding
- [ ] Quality dashboard loading
- [ ] Background jobs running
- [ ] Logging working
- [ ] Monitoring configured

---

## Troubleshooting

### Common Issues

#### 1. "No quality data available"

**Cause**: No tasks have been evaluated yet
**Fix**: Create and evaluate some tasks first

```bash
curl -X POST "http://localhost:8000/api/quality/evaluate/{task_id}"
```

#### 2. Trust index returns 50.0 for all components

**Cause**: Not enough data for statistical analysis
**Fix**: Wait for more tasks to be created and completed (aim for 20+ tasks)

#### 3. Learning not being applied

**Cause**: Background jobs not running
**Fix**:
1. Check job scheduler is running
2. Manually trigger aggregation: `await service.aggregate_signals_daily()`
3. Manually trigger training: `await service.train_models_from_aggregates()`

#### 4. Quality evaluation slow (>200ms)

**Cause**: Large number of tasks being queried
**Fix**: Add database indexes or implement pagination

#### 5. Cache not working

**Cause**: In-memory cache not persisting across requests
**Fix**: Upgrade to Redis for persistent caching

---

## Success Criteria

Phase 6 is successfully deployed when:

✅ All 6 stages implemented (30/30 steps complete)
✅ All 11 migrations run without errors
✅ 15 database tables created
✅ Quality dashboard loading and displaying data
✅ Trust index calculating (all 4 components)
✅ Background jobs running on schedule
✅ Learning loop closed (signals → aggregates → models → application)
✅ Quality improving over time (trust index increasing)
✅ No errors in production logs

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      PHASE 6: COGNITIVE NEXUS                    │
│                  Living Task Intelligence System                 │
└─────────────────────────────────────────────────────────────────┘

Stage 1: Knowledge Graph Evolution
  ↓
  Concepts → Temporal States → Task Context

Stage 2: Contextual Task Synthesis
  ↓
  Context + KG → AI Synthesis → Intelligent Description

Stage 3: Intelligent Updates
  ↓
  Description Changes → Version Control → PR-Style Comments

Stage 4: Contextual Questions
  ↓
  Context Gaps → Smart Questions → Batched Interactions

Stage 5: Implicit Learning
  ↓
  User Behavior → Signals → Aggregates → Models → Application

Stage 6: Quality Evaluation
  ↓
  Task Quality → Trust Index → Dashboard → Insights

┌──────────────────────┐
│   Learning Loop      │
│                      │
│  Better Tasks →      │
│  Better Outcomes →   │
│  Better Learning →   │
│  Better AI ↺         │
└──────────────────────┘
```

---

## Next Steps

After successful deployment:

1. **Monitor trust index** weekly - aim for steady increase
2. **Review quality trends** - identify patterns
3. **Analyze learning impact** - measure before/after learning application
4. **Optimize background jobs** - tune schedules based on usage
5. **Scale caching** - upgrade to Redis when needed
6. **Add custom metrics** - domain-specific quality factors

---

**Phase 6 Complete** ✨

For questions or issues, see the troubleshooting section or check service logs.
