#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

pick_python_with_tk() {
  local candidates=(
    "/opt/homebrew/bin/python3.11"
    "python3"
    "python"
  )
  local py
  for py in "${candidates[@]}"; do
    if ! command -v "${py}" >/dev/null 2>&1; then
      continue
    fi
    # 检查 tkinter 不仅能 import，还能真正创建 Tk 窗口（避免 macOS 运行时版本坑）
    if "${py}" -c "import tkinter as tk; r=tk.Tk(); r.withdraw(); r.destroy()" >/dev/null 2>&1; then
      echo "${py}"
      return 0
    fi
  done
  return 1
}

if ! PYTHON_BIN="$(pick_python_with_tk)"; then
  echo "Error: no usable Python runtime with Tk support found."
  echo "Checked: /opt/homebrew/bin/python3.11, python3, python"
  echo "Tip: install/repair a Python that can run 'tkinter.Tk()' successfully."
  exit 1
fi

echo "Starting AI Story Creator Pro with ${PYTHON_BIN}..."
exec "${PYTHON_BIN}" run_modern_app.py
