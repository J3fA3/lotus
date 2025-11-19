# Lotus AI Assistant - Complete Guide

**Lotus** is your unified AI-powered task management interface, combining all cognitive capabilities into one seamless experience across Phase 2 and Phase 3.

## 🌟 Overview

Lotus transforms how you interact with tasks by understanding natural language, learning your context, and intelligently managing your workload.

### Key Capabilities

- **Natural conversation** - Ask questions, get answers
- **Smart task extraction** - From Slack, emails, PDFs
- **Personal awareness** - Knows your name, role, projects
- **Relevance filtering** - Only creates relevant tasks
- **Auto-enrichment** - Updates existing tasks automatically
- **Natural comments** - Human-like explanations

## 🚀 Phase 2: Unified Intelligence

### Intelligent Request Classification

Lotus automatically determines what you need:

```typescript
// Question
"What's my highest priority task?"
→ Answers directly using knowledge graph

// Slack Message  
"Hi Jef, is the algorithm team using the sheet? We need to exclude chain X."
→ Creates task (even though it contains a question)

// PDF Upload
Upload meeting transcript
→ Fast processing, creates multiple tasks

// Manual Task
"Andy needs dashboard by Friday"
→ Full pipeline with confidence scoring
```

### Confidence-Based Autonomy

Lotus decides how to handle each task based on confidence:

| Confidence | Action | Example |
|------------|--------|---------|
| **>80%** | Auto-create | "Share CRESCO data with Andy by Friday" |
| **50-80%** | Ask approval | "Jef might need to review the specs" |
| **<50%** | Request clarification | "Something about the API?" |

### Source Type Selector

Toggle buttons help Lotus understand your input:

- **Manual** → LLM classification (question vs task)
- **Slack** → Always treats as task creation
- **Transcript** → Always treats as task creation

This prevents misclassification of Slack messages containing questions.

### AI Agent Comments

Every task includes detailed reasoning:

```
🤖 Confidence: 85%

Extracted from meeting notes:
- Person: Jef Adriaenssens
- Project: CRESCO
- Deadline: Friday (Nov 22, 2025)

Decision: High confidence task creation
- Clear assignee (Jef)
- Specific deadline (Friday)
- Known project (CRESCO)
```

### Fast PDF Processing

Dedicated endpoint for speed-critical PDFs:

```python
POST /api/assistant/process-pdf-fast
→ 2-3 seconds (vs 10+ seconds with full pipeline)
→ Bypasses: classification, confidence, matching
```

## ⚡ Phase 3: Speed & Intelligence

### Gemini 2.0 Flash Integration

**45x cost reduction**: $8/mo → $0.18/mo

- Structured output with Pydantic schemas
- Automatic fallback to Qwen if unavailable
- Built-in cost tracking
- 2-3x faster processing (20-30s → 8-12s)

### User Profile System

Lotus now knows YOU:

```python
{
  "name": "Jef Adriaenssens",  # Normalized (Jeff → Jef)
  "role": "Senior Engineer",
  "projects": ["CRESCO", "Just Deals"],
  "markets": ["Spain", "Netherlands"],
  "colleagues": ["Andy", "Sarah", "Alberto"]
}
```

**Benefits:**
- Name correction in tasks
- Relevance filtering by projects/markets
- Context-aware task creation

### Relevance Filtering

**0-100 scoring** with 70+ threshold:

```python
# Example 1: High relevance (Score: 95)
"Alberto asked about pinning position 3 for pharmacies in Spain"
→ Creates task (Spain is your market ✓)

# Example 2: Low relevance (Score: 35)
"Maran needs to review the PR"
→ Filters out (not for you ✗)
```

**Scoring factors:**
- Your projects (40% weight)
- Your markets (30% weight)
- Direct mentions (20% weight)
- Your colleagues (10% weight)

### Task Enrichment Engine

Auto-updates existing tasks when new context arrives:

```python
# Context 1 (Creates task)
"Co-op presentation prep needed"
→ Creates task: "Co-op presentation prep"

# Context 2 (Enriches task)
"Sarah confirmed Co-op moved to Dec 3"
→ Updates task: due_date = Dec 3
→ Adds note: "Rescheduled per Sarah's confirmation"
```

**Confidence-based:**
- **>80%** → Auto-apply changes
- **50-80%** → Ask for approval
- **<50%** → Skip enrichment

### Natural Language Comments

No more robot emojis! Human-like explanations:

```python
# Before Phase 3
"🤖 Confidence: 75%
Extracted entities: Alberto (PERSON), Spain (LOCATION)"

# After Phase 3  
"Alberto (Spain market) asked about pharmacy pinning. 
Tagged as Spain-specific since that's his focus area."
```

### Performance Cache

**LRU cache with TTL:**
- User profiles: 5-minute cache
- Recent tasks: 30-second cache
- Knowledge graph: 60-second cache

**Results:**
- Simple messages: 20-30s → **8-12s**
- Cache hit rate: **>60%** after warm-up

## 🎯 Usage Examples

### Example 1: Question Answering

**Input:**
```
"What tasks are due this week?"
```

**Lotus Response:**
```
You have 3 tasks due this week:

1. Share CRESCO data (Due: Friday)
2. Review auth PR (Due: Thursday)
3. Q4 planning meeting (Due: Wednesday)
```

### Example 2: Slack Message Processing

**Input:**
```
Source: Slack
"Hey Jef, the CRESCO deadline moved to next Monday 
due to data collection delays."
```

**Lotus Actions:**
1. Loads your profile (knows you're working on CRESCO)
2. Extracts entities: CRESCO (project), next Monday (date)
3. Finds existing CRESCO task
4. Updates deadline to next Monday
5. Adds natural comment: "Deadline extended due to data collection delays"

**Result:** Task updated, no duplicate created ✅

### Example 3: Relevance Filtering

**Input:**
```
"Maran is sick today and won't be able to join the standup"
```

**Lotus Analysis:**
- Relevance score: 25 (below 70 threshold)
- Reason: About Maran, not you
- Decision: No task created ✗

**Result:** Notification only, no task spam ✅

### Example 4: Auto-Enrichment

**Scenario:**
```
# Week 1
"Prepare Co-op presentation for next month"
→ Creates task with due_date: Dec 15 (estimated)

# Week 2  
"Sarah confirmed Co-op presentation moved to Dec 3"
→ Finds existing Co-op task
→ Confidence: 85% (auto-apply threshold)
→ Updates due_date to Dec 3
→ Adds note: "Rescheduled to Dec 3 per Sarah"
```

**Result:** Task auto-updated, no approval needed ✅

### Example 5: PDF Processing

**Input:**
```
Upload: meeting-notes-nov-16.pdf (5 pages)
```

**Lotus Actions:**
1. Fast PDF endpoint (2-3 seconds)
2. Extracts text from all pages
3. Identifies 7 action items
4. Creates 7 tasks with context
5. Links back to source PDF

**Result:** 7 tasks created in under 5 seconds ⚡

## 🔧 Configuration

### Environment Variables

```bash
# backend/.env

# Phase 3: Gemini API
GOOGLE_AI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Phase 2: Ollama (fallback)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Performance
ENABLE_CACHE=true
CACHE_TTL_SECONDS=60
REDIS_URL=redis://localhost:6379  # Optional
```

### User Profile Setup

```bash
# Create/update your profile
curl -X POST http://localhost:8000/api/profiles/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jef Adriaenssens",
    "role": "Senior Engineer",
    "projects": ["CRESCO", "Just Deals"],
    "markets": ["Spain", "Netherlands"],
    "colleagues": ["Andy", "Sarah", "Alberto"]
  }'
```

### Relevance Threshold

Adjust in `backend/agents/relevance_filter.py`:

```python
RELEVANCE_THRESHOLD = 70  # Default: 70
# Lower = more tasks created (more false positives)
# Higher = fewer tasks (more false negatives)
```

### Confidence Thresholds

Adjust in `backend/agents/orchestrator.py`:

```python
AUTO_APPLY_THRESHOLD = 0.80  # Default: 80%
APPROVAL_THRESHOLD = 0.50    # Default: 50%
```

## 📊 Monitoring

### Usage Statistics

```bash
# View Gemini usage and cost
curl http://localhost:8000/api/assistant/usage-stats
```

**Response:**
```json
{
  "total_requests": 150,
  "total_input_tokens": 45000,
  "total_output_tokens": 15000,
  "total_cost_usd": 0.0084,
  "average_latency_ms": 1200,
  "cache_hit_rate": 0.62
}
```

### Performance Metrics

```bash
# Cache statistics
curl http://localhost:8000/api/assistant/cache-stats
```

**Response:**
```json
{
  "cache_size": 245,
  "hit_rate": 0.62,
  "miss_rate": 0.38,
  "evictions": 12,
  "avg_ttl_seconds": 180
}
```

## 🐛 Troubleshooting

### Issue: Tasks not relevant to me

**Solution:** Update your user profile with accurate projects/markets:

```bash
curl -X PUT http://localhost:8000/api/profiles/1 \
  -d '{"projects": ["CRESCO", "Your Project Here"]}'
```

### Issue: Too many tasks created

**Solution:** Increase relevance threshold:

```python
# In backend/agents/relevance_filter.py
RELEVANCE_THRESHOLD = 80  # Increase from 70
```

### Issue: Gemini not working

**Checks:**
1. API key is valid: `echo $GOOGLE_AI_API_KEY`
2. API has quota remaining
3. Internet connection working

**Fallback:** Lotus automatically uses Ollama if Gemini fails

### Issue: Slow performance

**Solutions:**
1. Enable Redis caching
2. Check Gemini API latency
3. Reduce context size
4. Use faster model (Qwen 3B)

## 🎓 Advanced Usage

### Custom Enrichment Rules

Add custom logic in `backend/agents/enrichment_engine.py`:

```python
def should_enrich(self, task, context):
    # Custom rule: Only enrich high-priority tasks
    if task.priority != "high":
        return False
    
    # Custom rule: Only if context mentions the project
    if task.project not in context:
        return False
    
    return True
```

### Custom Relevance Scoring

Modify `backend/agents/relevance_filter.py`:

```python
def calculate_relevance(self, task, profile):
    score = 0
    
    # Custom: Boost score for urgent keywords
    if any(word in task.title.lower() for word in ["urgent", "asap"]):
        score += 20
    
    # Custom: Boost for your team members
    if task.assignee in profile.team_members:
        score += 15
    
    return min(score, 100)
```

### Webhook Integration

Trigger Lotus from external systems:

```bash
# From Slack webhook
curl -X POST http://localhost:8000/api/assistant/webhook \
  -H "X-Slack-Signature: ..." \
  -d '{
    "text": "Message from Slack",
    "user": "john",
    "channel": "engineering"
  }'
```

## 🔮 Future Enhancements

Planned features for Phase 4:

1. **Multi-user support** - Team profiles and sharing
2. **Priority inference** - Auto-detect urgency
3. **Dependency detection** - Link related tasks
4. **Smart reminders** - Context-aware notifications
5. **Voice input** - Process voice notes
6. **Mobile app** - iOS/Android support

## 📚 Related Documentation

- **[Cognitive Nexus](../architecture/COGNITIVE_NEXUS.md)** - Underlying AI system
- **[Knowledge Graph](../architecture/KNOWLEDGE_GRAPH.md)** - Memory system
- **[Task Management](./TASK_MANAGEMENT.md)** - Task intelligence details
- **[API Reference](../api/API_REFERENCE.md)** - All endpoints

---

**Last Updated:** November 2025  
**Phase:** 2 & 3 Complete  
**Status:** Production Ready
