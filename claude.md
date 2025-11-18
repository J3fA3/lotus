# Claude Code Project Directives - Lotus Phase 2

## Project Context
Lotus is an AI-powered task management system using LangGraph agents to automatically infer tasks from communications. Phase 1 built 4 agents + knowledge graph. Phase 2 builds unified chat interface with confidence-based autonomous task creation.

## Guiding Principles

### 1. Preserve Phase 1 - Extend, Don't Rebuild
Call existing agents via `.ainvoke()`, don't reimplement. Orchestrator coordinates, doesn't replace.

### 2. Confidence-Based Autonomy
- >80%: Act automatically
- 50-80%: Ask approval
- <50%: Ask clarification

### 3. Knowledge Graph First
ALWAYS query before creating tasks. If >70% match, ENRICH existing task.

### 4. Rich But Concise Descriptions
2-3 sentence summary + context + source. NOT full transcript.

### 5. Smart Field Population
Parse dates ("Friday" → actual date), priorities ("urgent" → high), tags (from KG). If ambiguous, return null.

## Development Workflow
1. Read full plan (this prompt)
2. Work sequentially through stages
3. Test after each service (unit tests)
4. Commit after each step
5. Verify no Phase 1 regressions

## Architecture Decisions

**Orchestrator as Coordinator:** New agent coordinates Phase 1 agents, adds confidence scoring and smart routing.

**Confidence Thresholds:** 80% (auto), 50% (ask) - may need tuning based on real usage.

**Knowledge Graph Matching:** Use entity overlap + relationship chains. Semantic embeddings optional (defer to Phase 3).

**Qwen First:** Try local LLM for everything. Add Claude API only if quality <70%.

**Polling for Real-Time:** 3-second polling for task updates. WebSockets deferred to Phase 3.

## Testing Strategy
- Test-after development (write tests immediately after implementing)
- >80% coverage for core services
- Integration tests for orchestrator branches
- End-to-end tests for 5 scenarios

## Common Commands
```bash
# Start application
./start.sh

# Run tests
pytest backend/tests/

# Database migration
cd backend && alembic upgrade head

# Linting
ruff check backend/
npm run lint
```

## Error Handling
- LLM failures: Return low confidence + fallback action
- Knowledge graph errors: Continue without enrichment
- Database errors: Use transactions (all-or-nothing)
- Input validation: Fail fast at API boundary

## Code Style
- Python: snake_case files/functions, PascalCase classes
- TypeScript: PascalCase components, camelCase functions
- Type hints required for all Python functions
- Docstrings for all public functions (Google style)

## Performance Targets
- Simple message: <30s
- Complex transcript: <60s
- Knowledge graph queries: <500ms
- UI interactions: <100ms

## Security
- All DB queries via ORM (no raw SQL)
- No eval() or exec() of user input
- Sanitize HTML in chat (react-markdown safe defaults)
- Rate limit: 10 requests/minute per session

## File Structure

### Backend
```
backend/
├── agents/
│   ├── orchestrator.py          [NEW] Coordinates all agents, confidence routing
│   ├── confidence_scorer.py     [NEW] Calculates confidence scores
│   └── [existing Phase 1 agents - preserve these]
├── services/
│   ├── task_matcher.py          [NEW] Finds related tasks via knowledge graph
│   └── field_extractor.py       [NEW] Extracts dates, priorities, tags
├── api/
│   └── assistant_routes.py      [NEW] Chat interface endpoints
└── db/
    └── models.py                [UPDATE] Add ChatMessage, FeedbackEvent models
```

### Frontend
```
src/
├── components/
│   ├── AIAssistant.tsx          [NEW] Main chat interface
│   ├── TaskCard.tsx             [EXISTS] Will be enhanced for interactive preview
│   └── ChatMessage.tsx          [NEW] Message rendering with embedded cards
├── hooks/
│   └── useChat.ts               [NEW] Chat state management
└── api/
    └── assistant.ts             [NEW] API client
```

## Phase 2 Implementation Stages

### Stage 1: Foundation (Steps 1-6)
- [x] Create claude.md with guiding principles
- [ ] Update database schema (ChatMessage, FeedbackEvent tables)
- [ ] Create Alembic migration
- [ ] Build ConfidenceScorer service (thresholds: 80%, 50%)
- [ ] Build TaskMatcher service (knowledge graph queries)
- [ ] Build FieldExtractor service (date/priority/tag parsing)

### Stage 2: Orchestrator Agent (Steps 7-10)
- [ ] Create orchestrator LangGraph structure with conditional routing
- [ ] Implement decision logic (create vs enrich vs store vs ask)
- [ ] Task generation with rich descriptions (LLM summarization)
- [ ] Execute actions (database persistence, knowledge graph update)

### Stage 3: Chat UI (Steps 11-15)
- [ ] Chat state management (Zustand store)
- [ ] Main AIAssistant component (chat layout, input area)
- [ ] TaskCard component (interactive preview with approve/edit/reject)
- [ ] ConfidenceIndicator component (visual confidence display)
- [ ] ChatMessage rendering (embedded task cards, markdown)

### Stage 4: API Integration (Steps 16-18)
- [ ] Assistant API endpoints (POST /assistant/process, /assistant/approve)
- [ ] Feedback tracking API (track edits/deletions for Phase 3 learning)
- [ ] Real-time task updates (3-second polling for Kanban board sync)

### Stage 5: Polish (Steps 19-22)
- [ ] Navigation (add route, remove old buttons)
- [ ] Parsing agent integration (route PDFs to parser)
- [ ] End-to-end testing (5 test scenarios)
- [ ] Documentation update

## Key Implementation Notes

### ConfidenceScorer
Calculates overall confidence based on:
- Entity quality (how well entities were extracted)
- Knowledge graph matches (does it match existing context?)
- Clarity (is the input ambiguous or clear?)

Returns: 0-100 score + recommendation (auto/ask/clarify)

### TaskMatcher
Finds related tasks via:
1. Exact entity match (shared people/projects) → high confidence
2. Relationship chains (connected entities) → medium confidence
3. Rank by relevance

### FieldExtractor
Extracts task fields:
- due_date: "Friday" → next Friday, "end of month" → last day
- priority: "urgent" → high, "soon" → medium, default → medium
- tags: Query knowledge graph for project names
- status: Default 'todo'

### Orchestrator Decision Flow
1. Run Context Analysis Agent (Phase 1)
2. Run Entity Extraction Agent (Phase 1)
3. Run Relationship Synthesis Agent (Phase 1)
4. Find related tasks (TaskMatcher)
5. Calculate confidence (ConfidenceScorer)
6. Decide action:
   - >80%: Auto-create/enrich task
   - 50-80%: Propose task, ask approval
   - <50%: Ask clarifying questions
7. Execute action (if auto) or return proposal (if ask)

## Testing Scenarios

1. **Simple Slack message** → Auto-create task (confidence >80%)
   - Input: "Andy needs CRESCO dashboard by Friday"
   - Expected: 1 task created automatically

2. **Ambiguous input** → Ask clarification (confidence <50%)
   - Input: "We should do that thing soon"
   - Expected: Ask "What task? For whom? When?"

3. **Existing task match** → Enrich, don't duplicate
   - Input: "CRESCO dashboard is 80% done"
   - Expected: Add comment to existing CRESCO task

4. **PDF upload** → Route to parser → extract entities → create tasks
   - Input: PDF with meeting notes
   - Expected: Multiple tasks extracted from structured content

5. **Question** → "What's my top priority?" → Analyze knowledge graph
   - Input: Question about priorities
   - Expected: Query and summarize, no task creation
