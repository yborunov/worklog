# Worklog (macOS)

Local-only, always-on productivity tracker for macOS.

It records active app + front window title over time, stores events in SQLite, and generates deterministic daily Markdown reports.

## High-Level Overview

- The tracker samples your frontmost app and window title every few seconds.
- Each sample is written to a local SQLite database (`events` table).
- Reports are generated from those events into stable Markdown sections.
- Everything stays on-device (no network calls, no remote backend).
- For always-on behavior, macOS `launchd` runs the tracker at login and keeps it alive.

### Runtime Flow

1. `src.main run` starts the sampling loop.
2. Collector captures app name, bundle ID, window title, and idle state.
3. Storage writes event rows to `~/.worklog/tracker.db`.
4. Reporter groups events into sessions and builds daily report files.

## Features

- Always-running background tracker (via launchd)
- Active app detection using macOS APIs (PyObjC)
- Front window title capture (AppleScript via System Events)
- Idle detection
- Local SQLite event storage
- Daily Markdown reports with:
  - totals
  - time by app
  - time by window title
  - chronological timeline
  - focus blocks
  - raw data references

## Privacy

- Data stays local on your machine.
- No network calls.
- You control report sharing.

## Project Policies

- License: `LICENSE`
- Contributing: `CONTRIBUTING.md`
- Security: `SECURITY.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`

## Requirements

- macOS
- Python 3.11+
- Accessibility permission for terminal/python/agent process (for System Events window title access)

For users who do not want Python installed, build and run the standalone `worklog` binary (next section).

## Standalone CLI (no Python on end-user machine)

Build on a macOS machine with Python once:

```bash
cd /Users/wannabe/GitUnsynced/productivity-macos
./scripts/build_worklog_binary.sh
```

Output binary:

- `dist/worklog`

Run commands from the standalone binary:

```bash
./dist/worklog init
./dist/worklog run
./dist/worklog report --date YYYY-MM-DD
./dist/worklog health
```

Install launchd to run the standalone binary at login:

```bash
python -m src.main install --exec "$(pwd)/dist/worklog" --load
```

## Homebrew Install

To ship `worklog` via Homebrew, publish a release artifact and formula in your tap repo.

1) Build the binary:

```bash
./scripts/build_worklog_binary.sh
```

2) Package the artifact and capture sha256:

```bash
./scripts/package_homebrew_artifact.sh 0.1.0
```

This creates `dist/homebrew/worklog-0.1.0-macos-<arch>.tar.gz` and prints its `sha256`.

3) Upload the tarball to a release (GitHub/GitLab/Gitea) and copy the download URL.

4) Generate formula file:

```bash
./scripts/generate_homebrew_formula.sh \
  0.1.0 \
  "https://host/releases/download/v0.1.0/worklog-0.1.0-macos-arm64.tar.gz" \
  "<sha256>"
```

5) Commit generated `worklog.rb` into your tap repo (for example `homebrew-tools/Formula/worklog.rb`), then install:

```bash
brew tap <org>/tools
brew install worklog
```

If you do not use a tap, you can still install directly from a formula file URL:

```bash
brew install --formula https://host/path/to/worklog.rb
```

## How to Run

### 1) One-time setup

1. Create and activate a virtual env:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Initialize config and database

```bash
python -m src.main init
```

### 3) Run in foreground (test mode)

```bash
python -m src.main run
```

### 4) Generate a report

```bash
python -m src.main report --date 2026-03-20
```

If `--date` is omitted, it uses today.

### 4.5) Run health checks

Use this to verify config, database access, frontmost app detection, and launch agent wiring:

```bash
python -m src.main health
```

Expected output format:

```text
[OK] config: ...
[OK] database: ...
[OK] frontmost-detection: ...
[OK] launchagent-plist: ...
[OK] launchctl: ...
Health check passed.
```

### 5) Run in background (always-on)

Use the built-in CLI installer. By default it uses `~/.local/bin/worklog` if present, falls back to Python module mode, and loads the agent immediately (use `--no-load` to skip loading).

```bash
python -m src.main install \
  --load
```

The installer writes absolute paths into the plist.

This writes `~/Library/LaunchAgents/com.worklog.plist`, loads it, and keeps it running after login.

Check status:

```bash
launchctl list | grep com.worklog
```

Restart service:

```bash
launchctl kickstart -k gui/$(id -u)/com.worklog
```

Stop/unload service:

```bash
python -m src.main uninstall
```

## CLI Commands

```bash
python -m src.main init
python -m src.main health
python -m src.main run
python -m src.main report --date YYYY-MM-DD
python -m src.main install --load
python -m src.main uninstall
```

`health` verifies config loading, DB accessibility, frontmost app detection, launch agent plist, and current `launchctl` status.

## Install as Login Agent (Always-On)

```bash
python -m src.main install --load
```

This installs `~/Library/LaunchAgents/com.worklog.plist` and loads it.

Use Python module mode explicitly:

```bash
python -m src.main install --python "$(pwd)/.venv/bin/python" --load
```

Useful `launchctl` commands:

```bash
launchctl list | grep com.worklog
launchctl kickstart -k gui/$(id -u)/com.worklog
python -m src.main uninstall
```

## Default Data Locations

- Config: `~/.worklog/config.yaml`
- Database: `~/.worklog/tracker.db`
- Reports: `~/.worklog/reports/`
- Logs: `~/.worklog/logs/`

## Report Format

- `# Daily Productivity Report — YYYY-MM-DD`
- `## Totals`
- `## Time by App`
- `## Time by Window Title`
- `## Chronological Timeline`
- `## Focus Blocks`
- `## Raw Data References`

No interpretive AI summary is added.

## Notes on Permissions

To capture window titles, macOS may prompt for Accessibility access. Grant access to the running Python host (Terminal, iTerm, Warp, or whatever runs the process) and retry.

If window titles show as empty, re-check Accessibility permission for the exact binary in use (venv Python in `--python` mode, or `dist/worklog` in `--exec` mode).
