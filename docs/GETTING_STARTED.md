# 🎯 Getting Started - AI Task Inference

This guide will get you up and running in **5 minutes**! ⚡

---

## 📋 What You Need

You'll be running **3 services**:

1. **Ollama** (on your local machine) - AI model server
2. **Backend** (in GitHub Codespace) - FastAPI server
3. **Frontend** (in GitHub Codespace) - React app

---

## 🚀 Setup Instructions

### Step 1: Install Ollama on Your Local Machine

**Open Terminal on your LOCAL machine** (not in VS Code/Codespace) and run:

```bash
# macOS - Install via Homebrew
brew install ollama

# Or download from https://ollama.com/download

# Linux - Install script
curl -fsSL https://ollama.com/install.sh | sh

# Download the AI model (~4.7GB)
ollama pull qwen2.5:7b-instruct

# Start Ollama server (KEEP THIS RUNNING)
ollama serve
```

✅ **Keep this terminal window open** - Ollama needs to stay running

**Verify it's working:**
```bash
# In a new terminal on your LOCAL machine
curl http://localhost:11434/api/tags
# Should show JSON with qwen2.5:7b-instruct
```

---

### Step 2: Connect Ollama to GitHub Codespace

**On your LOCAL machine** (keep Ollama serve running in another terminal), create an SSH tunnel:

```bash
# This forwards your local Ollama (port 11434) to the codespace
gh codespace ssh -- -R 11434:localhost:11434
```

When prompted, choose your codespace (e.g., `J3fA3/task-crate [main]: cuddly spoon`)

✅ **Keep this SSH connection open** - it maintains the tunnel

**Verify the tunnel works** (in codespace terminal):
```bash
curl http://localhost:11434/api/tags
# Should show your local Ollama models
```

---

### Step 3: Start the Application (One Command!)

**In your GitHub Codespace terminal:**

```bash
./start.sh
```

This single script will:
- ✅ Check Ollama connection
- ✅ Start backend on port 8000
- ✅ Start frontend on port 8080
- ✅ Show all URLs and process IDs

Wait for:
```
✅ Task Crate is running!

📱 Frontend:  http://localhost:8080
🔧 Backend:   http://localhost:8000
📚 API Docs:  http://localhost:8000/docs
```

**That's it! Everything is running!** 🎉

---

### Step 4: Open the App

**In your browser:**

👉 http://localhost:8080

You should see:
- 🎨 Beautiful Kanban board
- 📋 Three columns: To-Do, In Progress, Done
- 🤖 Blue "AI Infer Tasks" button (top-right)

---

## 🎬 Try It Out!

### Quick Test

1. Click **"AI Infer Tasks"** button
2. Select **"Paste Text"** tab
3. Copy and paste this:

```
Meeting Notes - Nov 16, 2025

Action items from today's standup:
- @john Update API documentation before Friday release
- @sarah Review the authentication PR by tomorrow EOD
- Schedule Q4 planning meeting for next week
- @mike Finalize vendor contracts by end of week
- Everyone: Complete security training by Nov 20
```

4. Click **"Infer Tasks"**
5. Wait **10-30 seconds** (AI is thinking!)
6. **5 tasks appear automatically!** ✨

---

## 🔧 Troubleshooting

### Problem: "Backend not connected"

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/api/health

# If not, start it
./start-backend.sh
```

---

### Problem: "Ollama is not connected"

**Solution:**
1. **On your Mac**, check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. If not working, restart Ollama:
   ```bash
   ollama serve
   ```

3. **In dev container**, verify connectivity:
   ```bash
   curl http://host.docker.internal:11434/api/tags
   ```

---

### Problem: AI inference is slow or times out

**Solutions:**

1. **Close other apps** to free RAM
2. **Use smaller model** (faster but less accurate):
   ```bash
   # On your Mac
   ollama pull qwen2.5:3b-instruct
   
   # Update backend/.env
   OLLAMA_MODEL=qwen2.5:3b-instruct
   
   # Restart backend
   ```

3. **Check CPU usage** during inference

---

### Problem: Tasks not appearing

**Check:**
1. Browser console (F12) for errors
2. Backend logs in terminal
3. Ollama logs on Mac

**Fix:**
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R`
- Check backend logs for error messages

---

## 📊 Terminal Layout

Here's what your setup should look like:

```
┌─────────────────────────────────────┐
│  LOCAL Machine - Terminal 1        │
│  $ ollama serve                     │
│  [Ollama running on :11434...]      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  LOCAL Machine - Terminal 2        │
│  $ gh codespace ssh -- -R 11434:... │
│  [SSH tunnel to codespace...]       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  CODESPACE - Terminal               │
│  $ ./start.sh                       │
│  [Backend + Frontend running...]    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Browser                            │
│  http://localhost:8080              │
│  [Your beautiful Kanban app! 🎨]    │
└─────────────────────────────────────┘
```

---

## ✅ Success Checklist

Before using the app, verify:

- [ ] Ollama server is running on local machine (port 11434)
- [ ] SSH tunnel is active (`gh codespace ssh -- -R 11434:localhost:11434`)
- [ ] `./start.sh` completed successfully
- [ ] Backend is running in codespace (port 8000)
- [ ] Frontend is running in codespace (port 8080)
- [ ] Can open http://localhost:8080 in browser
- [ ] "AI Infer Tasks" button is **blue** (not gray)
- [ ] Can click button and see dialog open
- [ ] Successfully inferred tasks from sample text

---

## 💡 Usage Tips

### Getting Best Results

1. **Include context** - The more details, the better
2. **Mention dates** - AI extracts due dates automatically
3. **Use action verbs** - "Update", "Review", "Schedule", etc.
4. **Tag people** - Use @name for assignees
5. **Paste full conversations** - AI understands context

### What Works Well

✅ Slack message threads  
✅ Email threads  
✅ Meeting notes with action items  
✅ PDF documents with tasks  
✅ Project planning docs  

### What Doesn't Work

❌ Images or screenshots  
❌ Very vague descriptions  
❌ Non-English languages (depends on model)  

---

## 🎨 Features to Explore

Once you have tasks:

- **Drag & drop** - Move tasks between columns
- **Click to edit** - Click any task to see/edit details
- **Persistent storage** - Tasks saved automatically
- **Multiple inferences** - Add more tasks anytime
- **Manual tasks** - Use Quick Add button for manual entry

---

## 📚 Learn More

- **Full setup guide:** [SETUP.md](./SETUP.md)
- **Backend API docs:** http://localhost:8000/docs
- **Architecture details:** [SETUP.md](./SETUP.md) (Architecture section)

---

## 🎉 You're Ready!

Your AI-powered task management system is now fully operational!

**What you can do:**
- ✨ Paste any text and extract tasks instantly
- 📄 Upload PDFs and get tasks automatically
- 📋 Manage tasks on your Kanban board
- 💾 Everything persists in SQLite

**Everything runs locally - 100% private, no API keys, completely free!** 🔒

---

## 🛠️ Quick Commands Reference

**On your LOCAL machine:**
```bash
# Start Ollama
ollama serve

# Create SSH tunnel to codespace
gh codespace ssh -- -R 11434:localhost:11434

# Check Ollama status
ollama list

# Pull different model
ollama pull qwen2.5:3b-instruct
```

**In GitHub Codespace:**
```bash
# Start everything (one command!)
./start.sh

# Stop everything
./stop.sh

# Check if Ollama tunnel is working
curl http://localhost:11434/api/tags

# Check backend health
curl http://localhost:8000/api/health
```

---

**Need help?** Check [SETUP.md](./SETUP.md) for detailed troubleshooting! 🚑
