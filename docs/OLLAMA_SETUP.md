# Ollama Setup for Dev Container

This guide explains how to connect your dev container to Ollama running on your host machine.

## Why SSH Tunnel?

Dev containers are isolated environments. To access Ollama running on your host machine (macOS), we use SSH port forwarding to tunnel the connection.

## Setup Steps

### 1. Install Ollama on Host Machine

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from https://ollama.com
```

### 2. Pull the Model

```bash
ollama pull qwen2.5:7b-instruct
```

### 3. Start Ollama Service

```bash
# This keeps running in the background
ollama serve
```

The service will be available at `http://localhost:11434` on your host machine.

### 4. Configure SSH Tunnel

Create or edit `~/.ssh/config` on your **host machine**:

```ssh
Host devcontainer
    HostName localhost
    Port 2222
    User vscode
    RemoteForward 11434 127.0.0.1:11434
```

**What this does:**
- Forwards port 11434 from dev container → host machine
- When backend in dev container calls `localhost:11434`, it reaches Ollama on host

### 5. Connect to Dev Container

```bash
# VS Code automatically handles this when opening the project
# Or manually: Remote-Containers: Reopen in Container
```

### 6. Verify Connection

Inside dev container:

```bash
# Should return model info
curl http://localhost:11434/api/tags

# Or check via backend
curl http://localhost:8000/api/health
# Should show: "ollama_connected": true
```

## Troubleshooting

### Ollama Not Connected

```bash
# 1. Check Ollama is running on host
ollama list  # Should show qwen2.5:7b-instruct

# 2. Check port 11434 is listening on host
lsof -ti:11434  # Should return a PID

# 3. Verify SSH tunnel in dev container
curl localhost:11434/api/tags
```

### Model Not Found

```bash
# Pull the model again
ollama pull qwen2.5:7b-instruct

# Verify it's downloaded
ollama list
```

### Connection Refused

```bash
# Restart Ollama service
pkill ollama
ollama serve
```

## Alternative: Direct Network Access

If SSH tunnel doesn't work, you can use Docker host networking:

```json
// In .devcontainer/devcontainer.json
{
  "runArgs": ["--network=host"]
}
```

Then update backend to use `host.docker.internal`:

```bash
# In dev container
export OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Environment Variables

Backend automatically tries these endpoints:

1. `OLLAMA_BASE_URL` env var (if set)
2. `http://localhost:11434` (SSH tunnel)
3. `http://host.docker.internal:11434` (Docker host)

Set in `.env` file:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```
