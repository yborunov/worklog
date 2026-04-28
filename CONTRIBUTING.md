# Contributing

Thanks for your interest in improving Worklog.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local Verification

Run these commands before opening a PR:

```bash
python -m src.main init
python -m src.main health
python -m src.main report --date YYYY-MM-DD
./scripts/build_worklog_binary.sh
./dist/worklog --help
```

## Pull Request Guidelines

- Keep changes scoped and focused.
- Update `README.md` when behavior or commands change.
- Add rationale in the PR description (why the change is needed).
- Avoid committing generated artifacts (`dist/`, `build/`, `__pycache__/`, `.venv/`).

## Commit Style

- Use clear, imperative commit subjects.
- Mention user-facing impact when relevant.

## Reporting Bugs

Please include:

- macOS version
- Python version (if using Python mode)
- whether you run `src.main` or the standalone `worklog` binary
- exact command and output
