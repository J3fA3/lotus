# Phase 6: Deployment Checklist

**Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Status**: ✅ Ready for Production

---

## Pre-Deployment Verification

### 1. Database Migrations

- [ ] **All 11 migrations run successfully**
  ```bash
  cd backend/db/migrations
  python 001_add_knowledge_graph_tables.py
  python 002_add_phase2_assistant_tables.py
  python 003_add_phase3_tables.py
  python 004_add_phase5_email_tables.py
  python 006_add_phase6_kg_tables.py
  python 007_add_task_version_control.py
  python 008_add_question_queue.py
  python 009_add_implicit_learning.py
  python 010_add_outcome_learning.py
  python 011_add_task_quality.py
  ```

- [ ] **Verify 15+ tables created**
  ```bash
  sqlite3 tasks.db ".tables"
  ```

- [ ] **Verify critical indexes exist**
  ```sql
  SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';
  ```

### 2. Environment Variables

- [ ] **Required variables set**
  - [ ] `GOOGLE_AI_API_KEY` - Gemini API key
  - [ ] `DATABASE_URL` - Database connection string
  - [ ] `GEMINI_MODEL` - Model name (default: "gemini-2.0-flash-exp")

- [ ] **Optional variables configured**
  - [ ] `ENABLE_PHASE6_LEARNING_JOBS` - Enable background jobs (default: "true")
  - [ ] `LEARNING_MIN_SAMPLES` - Min samples for training (default: 10)
  - [ ] `LEARNING_CONFIDENCE_THRESHOLD` - Confidence threshold (default: 0.6)
  - [ ] `QUALITY_MIN_SAMPLES` - Min samples for correlation (default: 30)

- [ ] **Verify environment variables loaded**
  ```bash
  cd backend
  python -c "from dotenv import load_dotenv; import os; load_dotenv('.env'); print('GOOGLE_AI_API_KEY:', bool(os.getenv('GOOGLE_AI_API_KEY')))"
  ```

### 3. Dependencies

- [ ] **All Python packages installed**
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

- [ ] **Verify key packages**
  - [ ] `google-generativeai==0.3.2`
  - [ ] `sqlalchemy==2.0.36`
  - [ ] `apscheduler==3.10.4`
  - [ ] `fastapi==0.115.0`

### 4. Code Verification

- [ ] **Quality router registered in main.py**
  ```python
  from routes.quality_routes import router as quality_router
  app.include_router(quality_router, prefix="/api")
  ```

- [ ] **Phase 6 scheduler started in lifespan**
  ```python
  from services.phase6_learning_scheduler import get_phase6_learning_scheduler
  phase6_scheduler = get_phase6_learning_scheduler()
  phase6_scheduler.start()
  ```

- [ ] **All services importable**
  ```bash
  python -c "from services.implicit_learning_service import get_implicit_learning_service; print('OK')"
  python -c "from services.trust_index_service import get_trust_index_service; print('OK')"
  python -c "from services.task_quality_evaluator_service import get_task_quality_evaluator; print('OK')"
  ```

---

## Deployment Steps

### 1. Backend Deployment

- [ ] **Stop existing services** (if running)
  ```bash
  # Stop any running uvicorn processes
  pkill -f uvicorn
  ```

- [ ] **Pull latest code**
  ```bash
  git pull origin main
  ```

- [ ] **Install/update dependencies**
  ```bash
  cd backend
  source venv/bin/activate
  pip install -r requirements.txt
  ```

- [ ] **Run database migrations**
  ```bash
  cd db/migrations
  # Run all migrations in order (see Pre-Deployment section)
  ```

- [ ] **Start backend server**
  ```bash
  cd backend
  source venv/bin/activate
  python -m uvicorn main:app --host 0.0.0.0 --port 8000
  ```

- [ ] **Verify server starts**
  - [ ] Check logs for "Starting Phase 6 Learning scheduler..."
  - [ ] Check logs for "Quality router registered"
  - [ ] No errors in startup logs

### 2. Background Jobs Verification

- [ ] **Verify scheduler started**
  - [ ] Check logs: "Phase 6 learning scheduler started successfully"
  - [ ] Check logs: "Scheduled daily aggregation at 2:00 AM"
  - [ ] Check logs: "Scheduled weekly training on Sunday at 3:00 AM"
  - [ ] Check logs: "Scheduled weekly correlation analysis on Sunday at 4:00 AM"

- [ ] **Test job execution** (optional - manual trigger)
  ```python
  from services.phase6_learning_scheduler import get_phase6_learning_scheduler
  scheduler = get_phase6_learning_scheduler()
  await scheduler.daily_aggregation_job()
  ```

### 3. API Endpoints Verification

- [ ] **Health check**
  ```bash
  curl http://localhost:8000/api/health
  ```
  Expected: `{"status": "healthy", ...}`

- [ ] **Trust index endpoint**
  ```bash
  curl "http://localhost:8000/api/quality/trust-index?window_days=30"
  ```
  Expected: `{"trust_index": 50.0, ...}` or 404 if no data

- [ ] **Quality trends endpoint**
  ```bash
  curl "http://localhost:8000/api/quality/trends?window_days=7&period=daily"
  ```
  Expected: `[]` or array of trend data

- [ ] **Recent quality scores**
  ```bash
  curl "http://localhost:8000/api/quality/recent?limit=10"
  ```
  Expected: `[]` or array of quality scores

### 4. Frontend Integration

- [ ] **Quality dashboard route configured**
  - [ ] Route `/quality` exists in frontend routing
  - [ ] `QualityDashboard` component imported
  - [ ] API client configured for quality endpoints

- [ ] **Test dashboard access**
  - [ ] Navigate to `/quality` route
  - [ ] Dashboard loads without errors
  - [ ] Trust index displays (or shows "No data" message)
  - [ ] Trends chart renders (or shows empty state)

---

## Post-Deployment Verification

### 1. Functional Verification

- [ ] **Create test task**
  - [ ] Task created successfully
  - [ ] Quality evaluation triggered
  - [ ] Quality score saved

- [ ] **Verify signal capture**
  - [ ] User override captured as signal
  - [ ] Signal appears in `implicit_signals` table
  - [ ] Signal has correct type and data

- [ ] **Verify learning loop**
  - [ ] Signals aggregated (run daily job or wait)
  - [ ] Models trained (run weekly job or wait)
  - [ ] Learning applied to new tasks

- [ ] **Verify trust index**
  - [ ] Trust index calculates correctly
  - [ ] All 4 components present
  - [ ] Insights generated

### 2. Performance Verification

- [ ] **Latency checks**
  - [ ] Task evaluation < 50ms
  - [ ] Trust index calculation < 2s
  - [ ] Question generation < 1s

- [ ] **Load testing**
  - [ ] 10 concurrent evaluations complete successfully
  - [ ] No performance degradation
  - [ ] Error rate < 1%

### 3. Monitoring Setup

- [ ] **Logging configured**
  - [ ] Application logs to file
  - [ ] Error logs captured
  - [ ] Background job logs captured

- [ ] **Health monitoring**
  - [ ] Health check endpoint monitored
  - [ ] Alert on health check failures
  - [ ] Alert on background job failures

- [ ] **Metrics tracking**
  - [ ] Trust index trend tracked
  - [ ] Quality score distribution tracked
  - [ ] Background job execution tracked

---

## Rollback Plan

### If Deployment Fails

1. **Stop new services**
   ```bash
   pkill -f uvicorn
   ```

2. **Restore previous version**
   ```bash
   git checkout <previous-commit>
   ```

3. **Restart services**
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Database Rollback

- [ ] **Migration rollback scripts available**
  - [ ] Each migration has rollback capability
  - [ ] Rollback tested in staging

- [ ] **Database backup before migration**
  ```bash
  cp tasks.db tasks.db.backup
  ```

---

## Success Criteria

Phase 6 deployment is successful when:

- ✅ All 11 migrations run without errors
- ✅ All 15+ database tables created
- ✅ Quality router registered and accessible
- ✅ Background jobs scheduled and running
- ✅ API endpoints responding correctly
- ✅ Quality dashboard accessible and functional
- ✅ Trust index calculating correctly
- ✅ Learning loop closing (signals → aggregates → models → application)
- ✅ No errors in production logs
- ✅ Performance targets met

---

## Troubleshooting

### Common Issues

#### 1. Quality endpoints return 404

**Cause**: Quality router not registered  
**Fix**: Verify `app.include_router(quality_router, prefix="/api")` in `main.py`

#### 2. Background jobs not running

**Cause**: `ENABLE_PHASE6_LEARNING_JOBS` set to "false"  
**Fix**: Set `ENABLE_PHASE6_LEARNING_JOBS=true` in `.env`

#### 3. Trust index returns 50.0 for all components

**Cause**: Not enough data  
**Fix**: Create 20+ tasks and wait for evaluation

#### 4. Database migration errors

**Cause**: Migrations run out of order  
**Fix**: Run migrations in sequence (001, 002, 003, ...)

#### 5. Import errors

**Cause**: Dependencies not installed  
**Fix**: Run `pip install -r requirements.txt`

---

## Maintenance

### Daily Checks

- [ ] Background jobs executed (check logs)
- [ ] No errors in application logs
- [ ] Trust index trending upward or stable

### Weekly Checks

- [ ] Model training completed
- [ ] Correlation analysis completed
- [ ] Quality trends reviewed

### Monthly Checks

- [ ] Database size and performance
- [ ] Cache hit rates
- [ ] Overall system health

---

**Checklist Complete**: ✅  
**Ready for Production**: ✅  
**Last Verified**: 2025-01-XX

