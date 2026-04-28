#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_SRC="${BIN_SRC:-$ROOT_DIR/dist/worklog}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/dist/homebrew}"
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>" >&2
  echo "Example: $0 0.1.0" >&2
  exit 1
fi

if [[ ! -x "$BIN_SRC" ]]; then
  echo "worklog binary not found or not executable: $BIN_SRC" >&2
  echo "Build it first with: ./scripts/build_worklog_binary.sh" >&2
  exit 1
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64)
    PLATFORM="macos-arm64"
    ;;
  x86_64)
    PLATFORM="macos-amd64"
    ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

PKG_NAME="worklog-${VERSION}-${PLATFORM}"
PKG_DIR="$OUT_DIR/$PKG_NAME"
TARBALL="$OUT_DIR/${PKG_NAME}.tar.gz"

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"
cp "$BIN_SRC" "$PKG_DIR/worklog"
chmod +x "$PKG_DIR/worklog"

mkdir -p "$OUT_DIR"
tar -czf "$TARBALL" -C "$OUT_DIR" "$PKG_NAME"

SHA256_LINE="$(shasum -a 256 "$TARBALL")"
SHA256="${SHA256_LINE%% *}"

cat <<EOF
Created artifact: $TARBALL
sha256: $SHA256

Next step:
  Upload this tarball to a release and use its URL in your Homebrew formula.
EOF
