# Phase 5 Deployment Checklist

**Version:** Phase 5 - Gmail Integration + Agent Refactoring
**Target Date:** TBD
**Branch:** `claude/lotus-gmail-agent-refactor-01AeBjVzAjmAjSZu5wSuk69U`

---

## Pre-Deployment Checklist

### 1. Code Quality & Testing

- [ ] **All unit tests passing**
  ```bash
  pytest backend/tests/ -v
  ```

- [ ] **Integration tests passing**
  ```bash
  pytest backend/tests/integration/ -v
  ```

- [ ] **Email integration end-to-end test**
  - [ ] Gmail OAuth authentication works
  - [ ] Email polling fetches emails successfully
  - [ ] Email classification returns correct confidence scores
  - [ ] Email→Task creation pipeline works
  - [ ] Email→Calendar event creation works
  - [ ] Thread consolidation works for 5+ message threads

- [ ] **Performance benchmarks met**
  - [ ] Knowledge graph caching: 50%+ speedup ✓
  - [ ] Agent parallelization: 30%+ speedup ✓
  - [ ] Email classification: <2s per email ✓
  - [ ] Email parsing: <100ms per email ✓
  - [ ] Database queries: All using indexes ✓

- [ ] **Regression tests passing**
  - [ ] Phase 1 features (Cognitive Nexus agents) ✓
  - [ ] Phase 2 features (Knowledge graph) ✓
  - [ ] Phase 3 features (Gemini migration, user profiles) ✓
  - [ ] Phase 4 features (Calendar integration) ✓

### 2. Database Migration

- [ ] **Backup production database**
  ```bash
  python scripts/backup_database.py --env production
  ```

- [ ] **Test migration on staging**
  ```bash
  python -m db.migrations.004_add_phase5_email_tables --env staging
  ```

- [ ] **Verify migration rollback works**
  ```bash
  python -m db.migrations.rollback --migration 004 --env staging
  ```

- [ ] **Run migration on production**
  ```bash
  python -m db.migrations.004_add_phase5_email_tables --env production
  ```

- [ ] **Verify migration success**
  - [ ] All 4 tables created (email_accounts, email_messages, email_threads, email_task_links)
  - [ ] All 12 indexes created
  - [ ] Foreign keys working
  - [ ] Sample query performance acceptable

### 3. Environment Configuration

- [ ] **Production `.env` file updated**
  ```bash
  # Gmail API Configuration
  GMAIL_CREDENTIALS_PATH=gmail_credentials.json
  GMAIL_TOKEN_PATH=gmail_token.json
  GMAIL_POLL_INTERVAL_MINUTES=20
  GMAIL_MAX_RESULTS=50

  # Email Classification
  EMAIL_CLASSIFICATION_THRESHOLD=0.7
  EMAIL_AUTO_CREATE_THRESHOLD=0.8

  # Performance Optimization (Phase 5)
  ENABLE_AGENT_PARALLELIZATION=true
  MAX_PARALLEL_AGENTS=4
  KG_CACHE_TTL_SECONDS=60

  # Gemini API (existing)
  GEMINI_API_KEY=<production-key>
  GEMINI_MODEL=gemini-2.0-flash-exp

  # Google Calendar (existing - Phase 4)
  GOOGLE_CALENDAR_CREDENTIALS_PATH=calendar_credentials.json
  GOOGLE_CALENDAR_TOKEN_PATH=calendar_token.json
  ```

- [ ] **Gmail OAuth credentials configured**
  - [ ] gmail_credentials.json uploaded to server
  - [ ] OAuth consent screen configured with correct scopes:
    - `https://www.googleapis.com/auth/calendar`
    - `https://www.googleapis.com/auth/gmail.readonly`
    - `https://www.googleapis.com/auth/gmail.modify`
  - [ ] Test users added to OAuth consent screen (if in testing mode)
  - [ ] OAuth token generated and saved to gmail_token.json

- [ ] **Google Calendar OAuth working** (Phase 4 - verify still works)
  - [ ] calendar_credentials.json present
  - [ ] calendar_token.json present
  - [ ] Test calendar event creation works

- [ ] **Gemini API key configured**
  - [ ] Key has sufficient quota for production traffic
  - [ ] Billing account active
  - [ ] Rate limits appropriate (100 req/min for Gemini 2.0 Flash)

### 4. Dependencies

- [ ] **Python dependencies installed**
  ```bash
  pip install -r backend/requirements.txt
  ```

- [ ] **New Phase 5 dependencies verified**
  - [ ] email-validator==2.3.0 ✓
  - [ ] html2text==2025.4.15 ✓
  - [ ] beautifulsoup4==4.14.2 ✓

- [ ] **Service dependencies running**
  - [ ] Ollama running (for Qwen 2.5 7B fallback)
  - [ ] SQLite database accessible
  - [ ] Google APIs accessible (gmail.googleapis.com, calendar.google.com)

### 5. Background Services

- [ ] **Email polling service configured**
  - [ ] Service starts automatically on server boot
  - [ ] Polling interval set correctly (20 minutes)
  - [ ] Logs configured and rotating
  - [ ] Error alerting configured

- [ ] **Email polling service deployment script**
  ```bash
  # Add to systemd (example)
  sudo cp deployment/email-polling.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable email-polling
  sudo systemctl start email-polling
  ```

- [ ] **Monitor email polling service**
  - [ ] Status endpoint accessible: `GET /api/email/status`
  - [ ] Service health check passing
  - [ ] Logs show successful email fetches

### 6. API Endpoints

- [ ] **New email endpoints deployed**
  - [ ] `GET /api/email/status` - Polling service status ✓
  - [ ] `POST /api/email/sync` - Force sync ✓
  - [ ] `GET /api/email/recent` - List recent emails ✓
  - [ ] `GET /api/email/{id}` - Get email details ✓
  - [ ] `GET /api/email/thread/{id}` - Get thread details ✓
  - [ ] `POST /api/email/{id}/reprocess` - Reclassify email ✓

- [ ] **API documentation updated**
  - [ ] OpenAPI/Swagger docs regenerated
  - [ ] Email endpoints documented
  - [ ] Example requests/responses added

### 7. Monitoring & Logging

- [ ] **Application logs configured**
  - [ ] Email polling service logs to dedicated file
  - [ ] Log rotation configured (daily, keep 30 days)
  - [ ] Error logs sent to monitoring system

- [ ] **Performance monitoring**
  - [ ] Knowledge graph cache hit rate monitored
  - [ ] Agent parallelization timing logged
  - [ ] Email classification confidence scores tracked
  - [ ] Database query performance monitored

- [ ] **Alerting configured**
  - [ ] Alert on email polling failures (>5 consecutive failures)
  - [ ] Alert on low classification confidence (<50% for >10% of emails)
  - [ ] Alert on database migration failures
  - [ ] Alert on API errors (>10 per minute)

### 8. Security

- [ ] **OAuth credentials secured**
  - [ ] gmail_credentials.json has 600 permissions (read-only by owner)
  - [ ] gmail_token.json encrypted at rest
  - [ ] Credentials not in version control (.gitignore)

- [ ] **API authentication**
  - [ ] Email endpoints require authentication
  - [ ] Rate limiting configured (100 req/min per user)
  - [ ] CORS configured correctly

- [ ] **Data privacy**
  - [ ] Email content encrypted at rest (if required)
  - [ ] PII handling complies with regulations (GDPR, etc.)
  - [ ] Email retention policy configured

### 9. Documentation

- [ ] **User documentation updated**
  - [ ] Gmail setup guide: `docs/PHASE5_GMAIL_SETUP.md` ✓
  - [ ] Phase 5 features documented ✓
  - [ ] Troubleshooting guide added

- [ ] **Developer documentation updated**
  - [ ] Architecture diagrams updated ✓
  - [ ] API documentation regenerated
  - [ ] Database schema documented ✓
  - [ ] Query optimization guide: `backend/db/query_optimization.py` ✓

- [ ] **Deployment documentation**
  - [ ] This checklist ✓
  - [ ] Rollback procedures documented
  - [ ] Disaster recovery plan updated

### 10. Rollback Plan

- [ ] **Rollback procedure documented**
  1. Stop email polling service
  2. Revert code to previous version
  3. Rollback database migration 004
  4. Restart services
  5. Verify Phase 1-4 features still working

- [ ] **Rollback tested on staging**

- [ ] **Database backup verified**
  - [ ] Backup can be restored successfully
  - [ ] Restoration time acceptable (<30 minutes)

---

## Deployment Steps

### 1. Pre-Deployment

```bash
# 1. Backup production database
python scripts/backup_database.py --env production

# 2. Create deployment tag
git tag -a v1.5.0-phase5 -m "Phase 5: Gmail Integration + Agent Refactoring"
git push origin v1.5.0-phase5

# 3. Build deployment package
./scripts/build_deployment.sh
```

### 2. Staging Deployment

```bash
# 1. Deploy to staging
./scripts/deploy.sh --env staging --branch claude/lotus-gmail-agent-refactor-01AeBjVzAjmAjSZu5wSuk69U

# 2. Run database migration
python -m db.migrations.004_add_phase5_email_tables --env staging

# 3. Configure Gmail OAuth
python scripts/setup_gmail_oauth.py --env staging

# 4. Start email polling service
sudo systemctl start email-polling-staging

# 5. Run integration tests
pytest backend/tests/integration/ -v --env staging

# 6. Verify email pipeline
curl http://staging.lotus.example.com/api/email/status
curl -X POST http://staging.lotus.example.com/api/email/sync
```

### 3. Production Deployment

**IMPORTANT: Schedule deployment during low-traffic hours (e.g., 2-4 AM local time)**

```bash
# 1. Put application in maintenance mode (optional)
./scripts/maintenance_mode.sh --enable

# 2. Stop services
sudo systemctl stop lotus-backend
sudo systemctl stop lotus-frontend

# 3. Deploy code
./scripts/deploy.sh --env production --branch claude/lotus-gmail-agent-refactor-01AeBjVzAjmAjSZu5wSuk69U

# 4. Install dependencies
cd backend && pip install -r requirements.txt --upgrade

# 5. Run database migration
python -m db.migrations.004_add_phase5_email_tables --env production

# 6. Configure Gmail OAuth (first time)
python scripts/setup_gmail_oauth.py --env production

# 7. Start services
sudo systemctl start lotus-backend
sudo systemctl start lotus-frontend
sudo systemctl start email-polling

# 8. Verify deployment
./scripts/verify_deployment.sh --env production

# 9. Disable maintenance mode
./scripts/maintenance_mode.sh --disable

# 10. Monitor logs
tail -f /var/log/lotus/backend.log
tail -f /var/log/lotus/email-polling.log
```

### 4. Post-Deployment Verification

```bash
# 1. Verify API health
curl https://lotus.example.com/api/health

# 2. Verify email polling service
curl https://lotus.example.com/api/email/status

# 3. Force first email sync
curl -X POST https://lotus.example.com/api/email/sync

# 4. Check logs for errors
grep ERROR /var/log/lotus/backend.log | tail -20
grep ERROR /var/log/lotus/email-polling.log | tail -20

# 5. Verify Phase 1-4 features still working
./scripts/regression_test.sh --env production --quick

# 6. Monitor performance metrics
./scripts/check_performance.sh --env production
```

---

## Post-Deployment Monitoring (First 24 Hours)

### Hour 1
- [ ] All services running
- [ ] No error spikes in logs
- [ ] Email polling completing successfully
- [ ] First emails classified correctly

### Hour 6
- [ ] Email→Task creation working
- [ ] Email→Calendar events created
- [ ] Knowledge graph cache hit rate >50%
- [ ] Agent parallelization showing speedup

### Hour 24
- [ ] No user-reported issues
- [ ] Performance metrics stable
- [ ] Database queries using indexes
- [ ] No memory leaks in services

### Week 1
- [ ] Email classification accuracy >80%
- [ ] Thread consolidation working correctly
- [ ] Calendar integration stable
- [ ] User feedback collected

---

## Rollback Procedure (If Needed)

**If critical issues discovered, execute immediately:**

```bash
# 1. Stop services
sudo systemctl stop lotus-backend
sudo systemctl stop lotus-frontend
sudo systemctl stop email-polling

# 2. Revert code to previous version
git checkout v1.4.0-phase4  # Previous stable version

# 3. Rollback database migration
python -m db.migrations.rollback --migration 004 --env production

# 4. Restart services
sudo systemctl start lotus-backend
sudo systemctl start lotus-frontend

# 5. Verify rollback successful
./scripts/verify_deployment.sh --env production

# 6. Notify team of rollback
./scripts/send_alert.sh "Phase 5 deployment rolled back due to issues"
```

---

## Success Criteria

Phase 5 deployment is considered successful when:

- ✅ All Phase 5 features working:
  - Gmail OAuth authenticated
  - Email polling running every 20 minutes
  - Email classification accuracy >80%
  - Email→Task pipeline creating tasks correctly
  - Email→Calendar events created for meeting invites
  - Thread consolidation working for 5+ message threads

- ✅ All Phase 1-4 features still working:
  - Cognitive Nexus agents functioning
  - Knowledge graph updating correctly
  - Calendar sync working
  - User profiles loading

- ✅ Performance targets met:
  - Knowledge graph queries 50%+ faster
  - Agent processing 30%+ faster
  - Email classification <2s per email
  - No N+1 database query issues

- ✅ No critical bugs reported
- ✅ User satisfaction maintained or improved
- ✅ System stability maintained (uptime >99.9%)

---

## Contact Information

**Deployment Lead:** Jef Adriaenssens
**Backup Contact:** TBD
**Emergency Hotline:** TBD

**Critical Issues:**
- Email polling failures: Check `/var/log/lotus/email-polling.log`
- Classification errors: Check Gemini API quota
- Database issues: Check migration status and indexes
- OAuth failures: Regenerate tokens with `python scripts/setup_gmail_oauth.py`

---

**Last Updated:** November 19, 2025
**Version:** 1.0
**Status:** Ready for Staging Deployment
