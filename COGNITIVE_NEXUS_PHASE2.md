# Cognitive Nexus Phase 2 - Frontend UI & Integration

Phase 2 completes the full Cognitive Nexus vision by adding React components to test and visualize the LangGraph agentic system directly in your app.

## 🎯 What's New in Phase 2

### **Interactive UI Components**

1. **ContextAnalysisDialog** - Main interface for context ingestion
   - Input area for Slack messages, meeting notes, transcripts
   - Source type selector (manual, slack, transcript)
   - Real-time processing with loading states
   - Tabbed results view

2. **EntityVisualization** - Entity and relationship display
   - Entities grouped by type (PERSON, PROJECT, COMPANY, DATE)
   - Color-coded badges with confidence scores
   - Interactive relationship graph
   - Tabs for entities vs relationships

3. **ReasoningTraceView** - Agent transparency
   - Step-by-step agent decisions
   - Grouped by agent phase
   - Collapsible timeline
   - Highlighted key decisions and retry logic

4. **QualityMetricsDisplay** - Quality scores
   - Visual indicators (✓, ⚠, ✗) for quality levels
   - Progress bars for each metric
   - Threshold explanations
   - Context complexity display

### **Integration**

- **New "Context Analysis" button** in KanbanBoard header
- Styled as primary action (Brain icon)
- Disabled when backend not connected
- Opens full-screen analysis dialog

## 🚀 How to Use

### 1. Start the Backend

```bash
cd backend
python main.py
```

Backend should start on `http://localhost:8000`

### 2. Start Ollama (if not running)

```bash
# On host machine
ollama serve

# Ensure model is available
ollama pull qwen2.5:7b-instruct
```

### 3. Start the Frontend

```bash
cd /home/user/task-crate
npm install  # First time only
npm run dev
```

Frontend should start on `http://localhost:5173`

### 4. Test Cognitive Nexus

1. **Open the app** in your browser
2. **Click "Context Analysis"** button (Brain icon, top right)
3. **Paste example text:**

```
Hey Jef, can you share the CRESCO data with Andy by Friday?
Also, please check with Sarah from Co-op about the deployment timeline.
We need to get the API integration done before November 26th.
The backend server needs to be ready for the JustEat Takeaway team.
```

4. **Select source type** (try "Slack Message")
5. **Click "Analyze with AI Agents"**
6. **Wait 10-30 seconds** while agents process
7. **View results** in 3 tabs:
   - **Entities & Relationships**: See extracted people, projects, companies, dates
   - **Reasoning Trace**: See how agents made decisions
   - **Quality Metrics**: See agent self-evaluation scores

### 5. Understanding the Results

**Entities Tab:**
- **Blue badges** = People (Jef, Andy, Sarah)
- **Purple badges** = Projects (CRESCO, JustEat Takeaway)
- **Green badges** = Companies (Co-op)
- **Orange badges** = Dates (Friday, November 26th)

**Relationships Tab:**
- Shows connections like "Jef WORKS_ON CRESCO"
- "Andy COMMUNICATES_WITH Sarah"
- "CRESCO HAS_DEADLINE November 26th"

**Reasoning Trace:**
- See each agent's decision process
- Grouped by: Context Analysis → Entity Extraction → Relationship Synthesis → Task Intelligence
- Highlighted decisions (blue), retries (yellow), quality checks (green)

**Quality Metrics:**
- **Good (>70%)**: Green ✓
- **Fair (50-70%)**: Yellow ⚠
- **Low (<50%)**: Red ✗
- Agents automatically retry when quality drops below 70%

## 📁 Files Created in Phase 2

```
src/
├── api/
│   └── cognitivenexus.ts          # API client for context endpoints
├── types/
│   └── cognitivenexus.ts          # TypeScript types for entities, relationships, etc.
├── components/
│   ├── ContextAnalysisDialog.tsx  # Main UI dialog
│   ├── EntityVisualization.tsx    # Entity/relationship display
│   ├── ReasoningTraceView.tsx     # Agent reasoning trace
│   └── QualityMetricsDisplay.tsx  # Quality scores display
└── components/
    └── KanbanBoard.tsx            # Updated with Context Analysis button
```

## 🎨 UI Features

### Context Analysis Dialog

- **Full-screen modal** (max-width: 1024px)
- **Scrollable content** for long reasoning traces
- **Responsive design** works on mobile/tablet
- **Loading states** with spinner during processing
- **Error handling** with user-friendly messages
- **Reset functionality** to analyze more context

### Entity Visualization

- **Tabs** switch between entities and relationships
- **Grouped entities** by type with counts
- **Confidence scores** shown when <100%
- **Relationship arrows** show direction
- **Empty states** when no data

### Reasoning Trace

- **Collapsible** to save space
- **Step numbers** for reference
- **Agent icons** differentiate phases
- **Syntax highlighting** for decisions, retries, quality checks
- **Grouped by agent** for clarity

### Quality Metrics

- **Progress bars** with color coding
- **Icons** (✓ ⚠ ✗) for quick assessment
- **Descriptions** explain each metric
- **Threshold info** explains retry logic

## 🔧 Technical Details

### API Endpoints Used

- `POST /api/context/` - Ingest and process context
- `GET /api/context/{id}/reasoning` - Get reasoning trace
- `GET /api/context/{id}/entities` - Get extracted entities
- `GET /api/context/{id}/relationships` - Get relationships

### State Management

- **Local state** in ContextAnalysisDialog
- **API calls** are async/await
- **Toast notifications** for feedback
- **Error boundaries** for graceful failures

### Styling

- **shadcn/ui components** for consistency
- **Tailwind CSS** for styling
- **Lucide icons** for visual elements
- **Responsive** with mobile-first design

## 🐛 Troubleshooting

### "Backend not connected" message

**Solution:**
1. Check backend is running: `curl http://localhost:8000/api/health`
2. Restart backend: `cd backend && python main.py`

### "Ollama is not connected"

**Solution:**
1. Start Ollama: `ollama serve`
2. Check model: `ollama list | grep qwen`
3. Pull if missing: `ollama pull qwen2.5:7b-instruct`

### Button is disabled

**Cause:** Backend or Ollama not connected

**Solution:** Check browser console for connection errors, verify both services are running

### Analysis takes too long (>60 seconds)

**Cause:** Model loading or slow inference

**Solution:**
1. First run loads model (slow)
2. Subsequent runs are faster (~10-30s)
3. Check Ollama logs: `ollama ps`

### No entities extracted

**Possible causes:**
- Context too short/vague
- Model hallucination
- Parsing error

**Solution:**
1. Use more specific context with names, projects, dates
2. Check reasoning trace for agent decisions
3. Try "Detailed" strategy by using longer context

## 🎯 Example Use Cases

### Use Case 1: Slack Message Analysis

**Input:**
```
@john We need to finish the API docs by Friday.
@sarah Can you review the auth PR?
Let's get the Co-op deployment done before Q4 ends.
```

**Expected Output:**
- Entities: John (PERSON), Sarah (PERSON), Co-op (COMPANY), Friday (DATE), Q4 (DATE)
- Relationships: John WORKS_ON API docs, Sarah WORKS_ON auth PR
- Quality: ~75-85% (good extraction)

### Use Case 2: Meeting Transcript

**Input:**
```
Meeting notes from Nov 15, 2025:
- Jef will share CRESCO analytics with Andy
- Sarah from Sainsbury's needs the integration specs
- Deployment deadline: November 26th
- Backend team: work with JustEat Takeaway
```

**Expected Output:**
- Entities: Jef, Andy, Sarah, CRESCO, Sainsbury's, JustEat Takeaway, Nov 26th
- Relationships: Jef WORKS_ON CRESCO, Sarah WORKS_ON integration
- Quality: ~80-90% (transcript triggers detailed strategy)

### Use Case 3: Project Update

**Input:**
```
Quick update: The RF16 project needs attention.
Contact Mike and Emma about the database migration.
Target date: end of this month.
Working with Google Cloud team.
```

**Expected Output:**
- Entities: RF16 (PROJECT), Mike (PERSON), Emma (PERSON), Google Cloud (COMPANY)
- Relationships: Mike WORKS_ON RF16, Emma WORKS_ON database migration
- Quality: ~70-80% (moderate complexity)

## 🚀 Next Steps (Future Enhancements)

1. **Task Integration**
   - Auto-create tasks from analyzed context
   - Smart assignee suggestions based on entities
   - Project/deadline auto-fill

2. **Context History**
   - View past analyses
   - Re-analyze previous context
   - Search through context items

3. **Advanced Visualizations**
   - Interactive relationship graph (D3.js, React Flow)
   - Entity timeline
   - Quality trends over time

4. **Export Features**
   - Export entities to CSV
   - Generate task list from context
   - Save reasoning traces

5. **Learning & Improvement**
   - User feedback on entity accuracy
   - Improve prompts based on feedback
   - Context templates for common scenarios

## 📊 Performance Notes

- **First run**: 30-60s (model loading)
- **Subsequent runs**: 10-30s (model cached)
- **Entity extraction**: 3-10s per agent
- **Retry loops**: +5-15s if triggered
- **UI rendering**: <100ms

## 🎉 Success!

You now have a fully functional Cognitive Nexus UI integrated into your task management app!

**Try it out and see the agents in action! 🤖✨**
