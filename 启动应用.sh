#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: Python is not installed or not in PATH."
  exit 1
fi

if ! "${PYTHON_BIN}" -c "import tkinter" >/dev/null 2>&1; then
  echo "Error: tkinter is missing."
  echo "Linux: install package like python3-tk"
  echo "macOS: install python.org build or brew python-tk"
  exit 1
fi

echo "Starting AI Story Creator Pro with ${PYTHON_BIN}..."
exec "${PYTHON_BIN}" run_modern_app.py
