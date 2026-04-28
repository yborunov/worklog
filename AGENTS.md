# AGENTS.md

## Scope
- This repo is a single Python project (no monorepo/tooling layers): core runtime is `src/`, operational helpers are `scripts/`.

## Fast Start (verified commands)
- Create env + install deps: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Initialize local config/DB: `python -m src.main init`
- Run tracker in foreground: `python -m src.main run`
- Generate report: `python -m src.main report --date YYYY-MM-DD` (omit `--date` for today)
- Run built-in verification: `python -m src.main health`
- Build standalone binary: `./scripts/build_worklog_binary.sh` (output `dist/worklog`)
- Package Homebrew artifact: `./scripts/package_homebrew_artifact.sh <version>`
- Generate Homebrew formula: `./scripts/generate_homebrew_formula.sh <version> <artifact-url> <sha256>`

## Entrypoints That Matter
- CLI entrypoint is `src/main.py` with subcommands: `init`, `run`, `report`, `health`, `install`, `uninstall`.
- `run` writes event rows continuously and auto-generates the previous day's report on UTC day rollover.
- Storage schema is created on connect in `src/storage.py` (`events`, `daily_reports`); SQLite WAL is enabled via PRAGMA.

## Runtime/Data Paths
- Default config path: `~/.worklog/config.yaml` (auto-created if missing).
- Default DB path: `~/.worklog/tracker.db`.
- Default reports path: `~/.worklog/reports/`.
- Default logs path: `~/.worklog/logs/`.

## macOS + Permissions Gotchas
- Window-title capture uses AppleScript/System Events (`osascript` in `src/collector.py`); Accessibility permission must be granted to the exact host process/binary running Python.
- Frontmost app fallback uses `NSWorkspace`; if permissions/framework access fail, values may degrade to `Unknown`/empty title.

## launchd Workflows (repo-specific)
- Install always-on tracker (defaults to `~/.local/bin/worklog` when present and loads immediately): `python -m src.main install`.
- Install always-on tracker with explicit interpreter fallback: `python -m src.main install --python "$(pwd)/.venv/bin/python" --load`.
- Install always-on tracker from standalone binary with explicit path: `python -m src.main install --exec "$(pwd)/dist/worklog" --load`.
- Remove tracker launch agent: `python -m src.main uninstall`.
- Installer writes `~/Library/LaunchAgents/com.worklog.plist` by default and sets `WorkingDirectory` to repo root.
- Useful checks: `launchctl list | grep com.worklog` and restart with `launchctl kickstart -k gui/$(id -u)/com.worklog`.

## Verification Reality
- No dedicated lint/typecheck/test config is present in this repo; `python -m src.main health` is the only built-in operational check.
- If you change launch agent or sync behavior, verify both command success and `launchctl` status lines.
