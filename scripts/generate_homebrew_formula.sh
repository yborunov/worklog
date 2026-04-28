#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FORMULA_PATH="${FORMULA_PATH:-$ROOT_DIR/dist/homebrew/worklog.rb}"

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <version> <artifact-url> <sha256> [homepage]" >&2
  echo "Example: $0 0.1.0 https://example.com/worklog-0.1.0-macos-arm64.tar.gz abc123... https://git.yura.cc/wannabe/productivity-tracker-macos" >&2
  exit 1
fi

VERSION="$1"
ARTIFACT_URL="$2"
SHA256="$3"
HOMEPAGE="${4:-https://git.yura.cc/wannabe/productivity-tracker-macos}"

mkdir -p "$(dirname "$FORMULA_PATH")"

cat >"$FORMULA_PATH" <<EOF
class Worklog < Formula
  desc "Local-only, always-on productivity tracker for macOS"
  homepage "$HOMEPAGE"
  url "$ARTIFACT_URL"
  sha256 "$SHA256"
  version "$VERSION"

  depends_on :macos

  def install
    bin.install "worklog"
  end

  test do
    output = shell_output("#{bin}/worklog --help")
    assert_match "macOS productivity tracker", output
  end
end
EOF

echo "Wrote formula: $FORMULA_PATH"
