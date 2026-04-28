#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_SRC="${BIN_SRC:-$ROOT_DIR/dist/worklog}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
BIN_DEST="$BIN_DIR/worklog"

if [[ ! -x "$BIN_SRC" ]]; then
  echo "worklog binary not found or not executable: $BIN_SRC" >&2
  echo "Build it first with: ./scripts/build_worklog_binary.sh" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"
cp "$BIN_SRC" "$BIN_DEST"
chmod +x "$BIN_DEST"

echo "Installed: $BIN_DEST"

case ":${PATH}:" in
  *":$BIN_DIR:"*)
    echo "PATH already includes $BIN_DIR"
    ;;
  *)
    echo "PATH does not include $BIN_DIR"
    echo "Add this to ~/.zshrc, then run 'source ~/.zshrc':"
    echo "export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

echo "Try: worklog health"
