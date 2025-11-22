# Phase 5 Test Suite Documentation

Comprehensive testing suite for Gmail Integration + Agent Refactoring.

## Test Structure

```
backend/tests/
├── conftest.py                           # Shared fixtures and configuration
├── pytest.ini                            # Pytest configuration
├── test_email_classification.py          # Email classification agent tests (12 tests)
├── test_email_to_task_pipeline.py        # Email→Task pipeline integration (12 tests)
├── test_email_polling_service.py         # Polling service tests (17 tests)
├── test_email_calendar_intelligence.py   # Meeting invite→Calendar tests (19 tests)
├── test_agent_interactions.py            # Multi-agent orchestrator tests (15 tests)
├── evaluation/
│   └── test_classification_eval.py       # LLM-as-a-judge evaluations (7 tests)
└── e2e/
    └── test_email_ingestion_e2e.py       # End-to-end workflows (8 tests)
```

**Total: 90+ comprehensive tests**

## Running Tests

### All Tests

```bash
# Run entire test suite
cd backend
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=services --cov-report=html
```

### By Category

```bash
# Unit tests only
pytest tests/ -m "unit" -v

# Integration tests only
pytest tests/ -m "integration" -v

# End-to-end tests only
pytest tests/ -m "e2e" -v

# Evaluation tests only (LLM-as-a-judge)
pytest tests/ -m "evaluation" -v
```

### By Test File

```bash
# Email classification tests
pytest tests/test_email_classification.py -v

# Email→Task pipeline tests
pytest tests/test_email_to_task_pipeline.py -v

# Email polling service tests
pytest tests/test_email_polling_service.py -v

# Email-calendar intelligence tests
pytest tests/test_email_calendar_intelligence.py -v

# Agent interaction tests
pytest tests/test_agent_interactions.py -v

# LLM-as-a-judge evaluation tests
pytest tests/evaluation/test_classification_eval.py -v

# End-to-end tests
pytest tests/e2e/test_email_ingestion_e2e.py -v
```

### Specific Tests

```bash
# Run single test
pytest tests/test_email_classification.py::test_classification_actionable_task_high_confidence -v

# Run tests matching pattern
pytest tests/ -k "classification" -v

# Run tests by keyword
pytest tests/ -k "high_confidence" -v
```

### Performance & Quality

```bash
# Run slow tests only
pytest tests/ -m "slow" -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Run with performance profiling
pytest tests/ --durations=10

# Run in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

## Test Categories

### 1. Email Classification Tests
**File:** `test_email_classification.py` (12 tests)

Tests the email classification agent's ability to:
- Detect actionable tasks with high confidence
- Identify meeting invites
- Classify FYI/informational emails
- Detect automated newsletters
- Handle ambiguous emails with appropriate confidence
- Extract deadlines, projects, and action items
- Validate response structure
- Handle edge cases (empty fields, HTML, special characters)

**Run:**
```bash
pytest tests/test_email_classification.py -v
```

### 2. Email→Task Pipeline Integration Tests
**File:** `test_email_to_task_pipeline.py` (12 tests)

Tests the complete email→task creation pipeline:
- High confidence emails auto-create tasks (>80%)
- Medium confidence emails require confirmation (50-80%)
- Low confidence emails skip task creation (<50%)
- Multiple action items are extracted
- Deadlines are parsed correctly
- Project references are detected
- Entities are extracted
- Urgency is classified correctly
- Confidence scoring is calibrated
- Error handling for malformed data

**Run:**
```bash
pytest tests/test_email_to_task_pipeline.py -v
```

### 3. Email Polling Service Tests
**File:** `test_email_polling_service.py` (17 tests)

Tests the background polling service:
- Service initialization and configuration
- Email fetching from Gmail
- Polling intervals and scheduling
- Manual sync triggering
- Service status reporting
- Error handling (Gmail API failures, classification errors)
- Deduplication of existing emails
- Batch processing multiple emails
- High confidence → task creation
- Medium confidence → no auto-task
- Meeting invites → calendar events

**Run:**
```bash
pytest tests/test_email_polling_service.py -v
```

### 4. Email-Calendar Intelligence Tests
**File:** `test_email_calendar_intelligence.py` (19 tests)

Tests meeting invite processing:
- Meeting time extraction (explicit dates/times)
- Relative time parsing ("tomorrow", "next Monday")
- Location detection (Zoom, Google Meet, Teams links)
- Physical room detection
- Attendee parsing from CC field
- Calendar event creation
- Deduplication of events
- Meeting description cleaning
- Default vs explicit duration
- Timezone handling
- Recurring meeting detection

**Run:**
```bash
pytest tests/test_email_calendar_intelligence.py -v
```

### 5. Agent Interaction & Orchestrator Tests
**File:** `test_agent_interactions.py` (15 tests)

Tests multi-agent coordination:
- Agent node sequencing
- Parallel execution speedup (Phase 5 optimization)
- Data flow between agents
- Task proposal generation
- Enrichment checking
- Reasoning accumulation
- Parallelization benchmark (1.5x+ speedup expected)
- State immutability
- Email source type routing
- Error recovery
- Knowledge graph integration
- Multi-task creation

**Run:**
```bash
pytest tests/test_agent_interactions.py -v
```

### 6. LLM-as-a-Judge Evaluation Tests
**File:** `evaluation/test_classification_eval.py` (7 tests)

Advanced evaluation using Gemini to judge classification quality:
- Classification correctness evaluation
- Confidence appropriateness scoring
- Reasoning quality assessment
- Batch evaluation with aggregate metrics
- Consistency testing (same input → same output)
- Edge case robustness
- Performance targets:
  - **80%+ accuracy**
  - **6.5+/10 avg quality score**
  - **70%+ confidence calibration rate**

**Run:**
```bash
pytest tests/evaluation/test_classification_eval.py -v
```

**Note:** These tests call the Gemini API, so they require `GEMINI_API_KEY` configured.

### 7. End-to-End Email Workflow Tests
**File:** `e2e/test_email_ingestion_e2e.py` (8 tests)

Complete user journey simulations:
- Email→Task complete flow (fetch, parse, classify, create task, link)
- Meeting invite→Calendar event flow
- Newsletter filtering (no task creation)
- Batch email processing (3+ emails)
- Email thread consolidation (5+ messages)
- End-to-end performance (<5s target)

**Run:**
```bash
pytest tests/e2e/test_email_ingestion_e2e.py -v
```

## Fixtures & Utilities

### Database Fixtures
- `mock_db_session`: Mock async database session

### Email Test Data
- `sample_actionable_email`: High-confidence task email
- `sample_meeting_email`: Meeting invite
- `sample_newsletter_email`: Automated newsletter
- `sample_fyi_email`: Informational email
- `sample_ambiguous_email`: Medium-confidence email
- `sample_multi_action_email`: Multiple action items

### Service Mocks
- `mock_gmail_service`: Mock Gmail API
- `mock_gemini_service`: Mock Gemini AI
- `mock_calendar_service`: Mock Google Calendar

### Utilities
- `assert_email_classification`: Helper for asserting classification results

## Performance Benchmarks

### Target Metrics (from Test Plan)

| Metric | Target | Test Coverage |
|--------|--------|---------------|
| Email classification | <2s per email | ✓ Covered in polling tests |
| Email parsing | <100ms per email | ✓ Covered in pipeline tests |
| Knowledge graph caching | 50%+ speedup | ✓ Covered in agent tests |
| Agent parallelization | 30%+ speedup | ✓ Covered in interaction tests |
| End-to-end email→task | <5s total | ✓ Covered in E2E tests |
| Classification accuracy | 80%+ | ✓ Covered in evaluation tests |
| Confidence calibration | 70%+ | ✓ Covered in evaluation tests |

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Phase 5 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run unit tests
        run: pytest tests/ -m "not e2e and not evaluation" -v
      - name: Run integration tests
        run: pytest tests/ -m "integration" -v
      - name: Generate coverage report
        run: pytest tests/ --cov=agents --cov=services --cov-report=xml
```

## Test Development Guidelines

### Writing New Tests

1. **Use fixtures** - Leverage shared fixtures in `conftest.py`
2. **Mark appropriately** - Use markers (`@pytest.mark.e2e`, etc.)
3. **Mock external services** - Don't make real API calls in unit tests
4. **Test edge cases** - Empty strings, None values, large inputs
5. **Assert thoroughly** - Check both happy path and error cases
6. **Document test purpose** - Clear docstrings explaining what's tested

### Example Test Structure

```python
@pytest.mark.asyncio
async def test_feature_name(mock_db_session, sample_actionable_email):
    """Test that feature X does Y when Z condition."""

    # Arrange - Set up test data
    email_data = sample_actionable_email

    # Act - Execute the code under test
    result = await classify_email_content(**email_data)

    # Assert - Verify results
    assert result["classification"].is_actionable == True
    assert result["classification"].confidence >= 0.8
```

## Debugging Failed Tests

### Verbose Output

```bash
# Maximum verbosity
pytest tests/ -vvv

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l

# Drop into debugger on failure
pytest tests/ --pdb
```

### Logging

```bash
# Show logs during test execution
pytest tests/ --log-cli-level=DEBUG
```

### Isolate Failures

```bash
# Run only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

## Common Issues

### Issue: "ImportError: No module named 'agents'"

**Solution:**
```bash
# Ensure you're in the backend directory
cd backend

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

### Issue: "asyncio.exceptions.InvalidStateError"

**Solution:** Ensure `@pytest.mark.asyncio` decorator is used on async tests.

### Issue: "Mock object has no attribute"

**Solution:** Check that mocks in `conftest.py` have all required methods/attributes.

## Test Coverage

Generate HTML coverage report:

```bash
pytest tests/ --cov=agents --cov=services --cov=db --cov-report=html
open htmlcov/index.html  # View in browser
```

Coverage targets:
- **Overall: 80%+**
- **Email classification: 90%+**
- **Email polling service: 85%+**
- **Email-calendar intelligence: 80%+**
- **Orchestrator: 85%+**

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Phase 5 Test Plan](../../PHASE5_TEST_PLAN.md)
- [Phase 5 Implementation Status](../../PHASE5_IMPLEMENTATION_STATUS.md)

## Questions?

For questions about the test suite, refer to:
1. This README
2. [PHASE5_TEST_PLAN.md](../../PHASE5_TEST_PLAN.md) - Comprehensive test strategy
3. Test file docstrings - Each test file has detailed documentation
4. [DEPLOYMENT_CHECKLIST.md](../../DEPLOYMENT_CHECKLIST.md) - Pre-deployment testing requirements
