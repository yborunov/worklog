#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found at $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN=/path/to/python and retry." >&2
  exit 1
fi

"$PYTHON_BIN" -m pip install pyinstaller

cd "$ROOT_DIR"
"$PYTHON_BIN" -m PyInstaller \
  --name worklog \
  --onefile \
  --clean \
  --paths "$ROOT_DIR" \
  worklog_cli.py

echo "Built binary: $ROOT_DIR/dist/worklog"
