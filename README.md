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

1. `worklog run` starts the sampling loop.
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
- Accessibility permission for the host process (Terminal/iTerm/Warp for foreground runs, or LaunchAgent host for background runs)

For users who do not want Python installed, install the standalone `worklog` binary via Homebrew.

## Homebrew Install

```bash
brew tap yborunov/tap
brew install worklog
```

If you already tapped it:

```bash
brew update
brew install worklog
```

Install or refresh the launch agent using the installed binary:

```bash
worklog install
```

Uninstall the launch agent:

```bash
worklog uninstall
```

## How to Run

### 1) Initialize config and database

```bash
worklog init
```

### 2) Run in foreground (test mode)

```bash
worklog run
```

### 3) Generate a report

```bash
worklog report --date 2026-03-20
```

If `--date` is omitted, it uses today.

### 4) Run health checks

Use this to verify config, database access, frontmost app detection, and launch agent wiring:

```bash
worklog health
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

Use the built-in installer from the binary. It loads the agent immediately (use `--no-load` to skip loading).

```bash
worklog install \
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
worklog uninstall
```

## CLI Commands

```bash
worklog init
worklog health
worklog run
worklog report --date YYYY-MM-DD
worklog install --load
worklog uninstall
```

`health` verifies config loading, DB accessibility, frontmost app detection, launch agent plist, and current `launchctl` status.

## Install as Login Agent (Always-On)

```bash
worklog install --load
```

This installs `~/Library/LaunchAgents/com.worklog.plist` and loads it.

Useful `launchctl` commands:

```bash
launchctl list | grep com.worklog
launchctl kickstart -k gui/$(id -u)/com.worklog
worklog uninstall
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

To capture window titles, macOS may prompt for Accessibility access. Grant access to the running host process (Terminal, iTerm, Warp, or LaunchAgent-hosted binary) and retry.

If window titles show as empty, re-check Accessibility permission for the exact binary in use (`worklog`).
