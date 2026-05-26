#!/usr/bin/env bash
#
# Dev-only: launch the 3 v2 backend services on fixed ports without the GUI.
#
# Usage:
#   bash scripts/dev/start_services.sh         # foreground, all in tmux/3 panes
#   bash scripts/dev/start_services.sh nohup   # background via nohup, logs in logs/
#
# Stop with Ctrl-C in foreground mode, or `kill $(cat .runtime/dev.*.pid)` otherwise.
#
# Service URLs (fixed for dev):
#   rag    → http://127.0.0.1:8101
#   story  → http://127.0.0.1:8102
#   image  → http://127.0.0.1:8103
#
# These ports are intentionally distinct from production (port=0 → ephemeral)
# so the supervisor and dev mode can coexist if you forget to stop one.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p logs .runtime

export WSF_DEV=1
export WSF_NO_AUTH="${WSF_NO_AUTH:-1}"
export PYTHONPATH="${PYTHONPATH:-$REPO_ROOT}"

run_service() {
  local name="$1"
  local port="$2"
  local module="$3"
  echo "[dev] starting ${name} on :${port}  (module=${module})"
  uvicorn "${module}:app" --host 127.0.0.1 --port "${port}" --reload
}

run_nohup() {
  local name="$1"
  local port="$2"
  local module="$3"
  local log="logs/${name}.dev.log"
  local pidfile=".runtime/dev.${name}.pid"
  echo "[dev] nohup ${name} on :${port}  → ${log}"
  nohup uvicorn "${module}:app" --host 127.0.0.1 --port "${port}" \
    > "${log}" 2>&1 &
  echo $! > "${pidfile}"
}

mode="${1:-fg}"

case "$mode" in
  fg)
    if command -v tmux >/dev/null 2>&1; then
      session="wsf-dev"
      tmux kill-session -t "$session" 2>/dev/null || true
      tmux new-session -d -s "$session" -n rag   "PYTHONPATH=$REPO_ROOT WSF_DEV=1 WSF_NO_AUTH=1 uvicorn src.services.rag_service.runtime:app --host 127.0.0.1 --port 8101 --reload"
      tmux split-window -t "$session" -h          "PYTHONPATH=$REPO_ROOT WSF_DEV=1 WSF_NO_AUTH=1 uvicorn src.services.story_service.runtime:app --host 127.0.0.1 --port 8102 --reload"
      tmux split-window -t "$session" -v          "PYTHONPATH=$REPO_ROOT WSF_DEV=1 WSF_NO_AUTH=1 uvicorn src.services.image_service.runtime:app --host 127.0.0.1 --port 8103 --reload"
      echo "[dev] services launched in tmux session '${session}'."
      echo "[dev] attach with: tmux attach -t ${session}"
    else
      echo "[dev] tmux not found; falling back to nohup mode."
      run_nohup rag   8101 src.services.rag_service.runtime
      run_nohup story 8102 src.services.story_service.runtime
      run_nohup image 8103 src.services.image_service.runtime
    fi
    ;;
  nohup)
    run_nohup rag   8101 src.services.rag_service.runtime
    run_nohup story 8102 src.services.story_service.runtime
    run_nohup image 8103 src.services.image_service.runtime
    echo "[dev] all services started in background. Logs in logs/."
    echo "[dev] stop with:  kill \$(cat .runtime/dev.*.pid 2>/dev/null) && rm -f .runtime/dev.*.pid"
    ;;
  *)
    echo "Usage: $0 [fg|nohup]"
    exit 1
    ;;
esac
