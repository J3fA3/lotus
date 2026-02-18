#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_ENV_FILE="$BACKEND_DIR/.env"
BACKEND_ENV_TEMPLATE="$BACKEND_DIR/.env.example"
VENV_DIR="$BACKEND_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

BACKEND_PID=""
STARTED_BACKEND="0"

log() {
  printf '[lotus] %s\n' "$1"
}

ensure_backend_env() {
  if [[ ! -f "$BACKEND_ENV_FILE" ]]; then
    if [[ -f "$BACKEND_ENV_TEMPLATE" ]]; then
      cp "$BACKEND_ENV_TEMPLATE" "$BACKEND_ENV_FILE"
      log "Created backend/.env from backend/.env.example"
    else
      log "Missing backend/.env and backend/.env.example"
      exit 1
    fi
  fi

  local api_key
  api_key="$(grep -E '^GOOGLE_AI_API_KEY=' "$BACKEND_ENV_FILE" | head -n1 | cut -d'=' -f2- || true)"

  if [[ -z "${api_key:-}" || "$api_key" == "your_gemini_api_key_here" ]]; then
    log "Warning: GOOGLE_AI_API_KEY is not set in backend/.env. AI endpoints will fail until configured."
  fi
}

ensure_backend_venv() {
  if [[ -x "$VENV_PYTHON" ]]; then
    return
  fi

  local python_candidates=("python3.13" "python3.12" "python3.11" "python3")
  local chosen_python=""

  for candidate in "${python_candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      chosen_python="$candidate"
      break
    fi
  done

  if [[ -z "$chosen_python" ]]; then
    log "No Python 3 interpreter found. Install Python 3.11+ and rerun."
    exit 1
  fi

  log "Creating backend venv with $chosen_python"
  "$chosen_python" -m venv "$VENV_DIR"
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt"
}

ensure_frontend_deps() {
  if [[ ! -d "$ROOT_DIR/node_modules" ]]; then
    log "Installing frontend dependencies"
    (cd "$ROOT_DIR" && npm install)
  fi
}

wait_for_backend() {
  local backend_url="${1:-http://localhost:8000/api/health}"

  for _ in {1..40}; do
    if curl -sS "$backend_url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done

  return 1
}

port_in_use() {
  local port="$1"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

kill_port_listeners() {
  local port="$1"
  local pids
  pids="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"

  if [[ -z "$pids" ]]; then
    return 0
  fi

  log "Killing non-Lotus process(es) on port $port: $pids"
  kill $pids >/dev/null 2>&1 || true
}

cleanup() {
  if [[ "$STARTED_BACKEND" == "1" && -n "$BACKEND_PID" ]]; then
    log "Stopping backend (PID $BACKEND_PID)"
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

main() {
  ensure_backend_env
  ensure_backend_venv
  ensure_frontend_deps

  local api_port="8000"
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    local configured_port
    configured_port="$(grep -E '^API_PORT=' "$BACKEND_ENV_FILE" | tail -n1 | cut -d'=' -f2- || true)"
    if [[ -n "${configured_port:-}" ]]; then
      api_port="$configured_port"
    fi
  fi

  if port_in_use "$api_port"; then
    log "Backend port $api_port already in use. Verifying existing backend."

    if wait_for_backend "http://localhost:${api_port}/api/health"; then
      log "Backend is ready at http://localhost:${api_port}"
    else
      log "Port $api_port is in use, but the Lotus backend is not responding."
      kill_port_listeners "$api_port"
      sleep 0.5
    fi
  fi

  if ! port_in_use "$api_port"; then
    log "Starting backend on port $api_port"
    (
      cd "$BACKEND_DIR"
      source venv/bin/activate
      python main.py
    ) > "$ROOT_DIR/.backend.log" 2>&1 &
    BACKEND_PID=$!
    STARTED_BACKEND="1"

    if wait_for_backend "http://localhost:${api_port}/api/health"; then
      log "Backend is ready at http://localhost:${api_port}"
    else
      log "Backend did not become ready. Check .backend.log"
      exit 1
    fi
  else
    log "Backend port $api_port already in use. Reusing existing backend."
  fi

  log "Starting frontend dev server"
  log "Open the URL shown by Vite below (usually http://localhost:5173)"
  (cd "$ROOT_DIR" && npm run dev)
}

main
