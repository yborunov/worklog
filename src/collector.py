from __future__ import annotations

import datetime as dt
import subprocess

try:
    from AppKit import NSWorkspace  # type: ignore[import-not-found]
    from Quartz import CGEventSourceSecondsSinceLastEventType, kCGAnyInputEventType  # type: ignore[import-not-found]
except Exception:
    NSWorkspace = None
    CGEventSourceSecondsSinceLastEventType = None
    kCGAnyInputEventType = 0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _run_osascript(script: str, timeout_sec: int = 2) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def current_front_context(timeout_sec: int = 2) -> tuple[str, str, str]:
    script = (
        'tell application "System Events"\n'
        "set frontApp to first application process whose frontmost is true\n"
        "set appName to name of frontApp\n"
        "try\n"
        "set bundleId to bundle identifier of frontApp\n"
        "on error\n"
        'set bundleId to ""\n'
        "end try\n"
        "try\n"
        "set winName to name of front window of frontApp\n"
        "on error\n"
        'set winName to ""\n'
        "end try\n"
        "return appName & linefeed & bundleId & linefeed & winName\n"
        "end tell"
    )
    out = _run_osascript(script, timeout_sec=timeout_sec)
    if out:
        lines = out.splitlines()
        app_name = lines[0].strip() if len(lines) > 0 else ""
        bundle_id = lines[1].strip() if len(lines) > 1 else ""
        window_title = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""
        if app_name:
            return app_name, bundle_id, window_title

    app_name, bundle_id = _frontmost_app_nsworkspace()
    return app_name, bundle_id, ""


def current_frontmost_app() -> tuple[str, str]:
    app_name, bundle_id, _window_title = current_front_context()
    return app_name, bundle_id


def _frontmost_app_nsworkspace() -> tuple[str, str]:
    if NSWorkspace is None:
        return "Unknown", ""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return "Unknown", ""
    app_name = app.localizedName() or "Unknown"
    bundle_id = app.bundleIdentifier() or ""
    return app_name, bundle_id


def current_front_window_title(timeout_sec: int = 2) -> str:
    script = (
        'tell application "System Events"\n'
        "set frontApp to first application process whose frontmost is true\n"
        "try\n"
        "set winName to name of front window of frontApp\n"
        "on error\n"
        'set winName to ""\n'
        "end try\n"
        "return winName\n"
        "end tell"
    )
    out = _run_osascript(script, timeout_sec=timeout_sec)
    return out.strip()


def idle_seconds() -> float:
    try:
        if CGEventSourceSecondsSinceLastEventType is None:
            return 0.0
        return float(CGEventSourceSecondsSinceLastEventType(0, kCGAnyInputEventType))
    except Exception:
        return 0.0
