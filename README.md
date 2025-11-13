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

**See [SETUP.md](./SETUP.md) for complete installation guide**

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

## 📚 Full Documentation

- **[SETUP.md](./SETUP.md)** - Complete setup guide with troubleshooting
- **[backend/README.md](./backend/README.md)** - Backend API documentation
- **API Docs** - http://localhost:8000/docs (when backend is running)

---

## Project info

**URL**: https://lovable.dev/projects/0e90d6d8-b0b8-4b08-905c-6892833be7c7

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/0e90d6d8-b0b8-4b08-905c-6892833be7c7) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

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

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/0e90d6d8-b0b8-4b08-905c-6892833be7c7) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
