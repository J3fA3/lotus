# 🤖 AI Task Inference - Notion-like Kanban with Local AI

A powerful task management app with **AI-powered task extraction** from text and PDFs - completely free and running locally!

## ✨ Features

- 🎯 **Notion-like Kanban Board** - Beautiful drag-and-drop interface
- 🤖 **AI Task Inference** - Paste Slack messages, meeting notes, or upload PDFs - AI extracts tasks automatically
- 🔒 **100% Local & Free** - Uses Qwen 2.5 via Ollama, no API keys needed
- 💾 **Persistent Storage** - SQLite database, tasks never lost
- ⚡ **Fast & Modern** - React + TypeScript + FastAPI
- 🎨 **Beautiful UI** - shadcn/ui components with Tailwind CSS

## 🚀 Quick Start

**See [QUICKSTART.md](./QUICKSTART.md) for streamlined setup or [SETUP.md](./SETUP.md) for complete guide**

### Option 1: Using Dev Container (Current Setup)

```bash
# 1. Install Ollama on your Mac (HOST machine, not dev container)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct
ollama serve  # Keep this running

# 2. In dev container - Start backend (Terminal 1)
./start-backend.sh

# 3. In dev container - Start frontend (Terminal 2)
./start-frontend.sh

# Open http://localhost:5173 in your Mac browser
```

### Option 2: Running Locally (Without Dev Container)

```bash
# 1. Install Ollama (on your Mac)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct
ollama serve  # Keep this running

# 2. Start backend (new terminal)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py

# 3. Start frontend (new terminal)
npm install
npm run dev

# Open http://localhost:5173
```

## 🎬 Demo Flow

1. Open the app → See your Kanban board
2. Click **"AI Infer Tasks"** button
3. Paste this example:
   ```
   Meeting notes:
   - @john needs to update API docs before Friday
   - @sarah will review the auth PR tomorrow
   - Schedule Q4 roadmap meeting next week
   ```
4. Click **"Infer Tasks"**
5. Wait 10-30 seconds
6. 3 tasks automatically added to your board! ✨

## 🏗️ Architecture

```
Frontend (React + Vite) → Backend (FastAPI) → Ollama (Qwen 2.5)
        ↓
   SQLite Database
```

## 📚 Documentation

- **[GETTING_STARTED.md](./GETTING_STARTED.md)** - 🚀 **START HERE!** Quick 5-minute setup guide
- **[QUICKSTART.md](./QUICKSTART.md)** - Streamlined setup instructions
- **[SETUP.md](./SETUP.md)** - Complete setup guide with troubleshooting
- **[backend/README.md](./backend/README.md)** - Backend API documentation
- **API Docs** - http://localhost:8000/docs (when backend is running)

## 🛠️ Helpful Scripts

```bash
./health-check.sh      # Check if everything is set up correctly
./start-backend.sh     # Start the FastAPI backend
./start-frontend.sh    # Start the React frontend
```

---

## 🛠️ Technologies Used

**Frontend:**
- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

**Backend:**
- Python FastAPI
- SQLite
- Ollama (Qwen 2.5 7B Instruct)
- PyMuPDF (PDF processing)

---

## 🔧 Development

### Local Development

```sh
# Clone the repository
git clone <YOUR_GIT_URL>

# Navigate to the project directory
cd task-crate

# Install dependencies
npm install

# Start development servers
./start-backend.sh   # Terminal 1
./start-frontend.sh  # Terminal 2
```
