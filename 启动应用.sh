#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

pick_python_bin() {
  local candidates=(
    "${STORY_PYTHON:-}"
    "/opt/homebrew/bin/python3.11"
    "/usr/local/bin/python3.11"
    "python3.11"
    "python3"
    "python"
  )
  local py
  local resolved
  local version
  for py in "${candidates[@]}"; do
    [[ -z "${py}" ]] && continue
    if ! command -v "${py}" >/dev/null 2>&1; then
      continue
    fi

    resolved="$(command -v "${py}")"
    if [[ "$(uname -s)" == "Darwin" ]]; then
      version="$("${resolved}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
      # 规避已观察到的 Python 3.12 + Tk 崩溃路径
      if [[ "${version}" == "3.12" ]]; then
        continue
      fi
    fi

    echo "${resolved}"
    return 0
  done
  return 1
}

if ! PYTHON_BIN="$(pick_python_bin)"; then
  echo "Error: no usable Python runtime found."
  echo "Checked: STORY_PYTHON, python3.11, python3, python"
  echo "Tip: install Python 3.11 and retry."
  exit 1
fi

echo "Starting ScriptWeaver with ${PYTHON_BIN}..."
exec "${PYTHON_BIN}" run_modern_app.py
