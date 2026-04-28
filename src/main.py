from __future__ import annotations

import argparse
import datetime as dt
import plistlib
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from .collector import current_front_context, idle_seconds, now_iso
from .config import default_config_path, load_config, write_default_config
from .reporter import generate_daily_report
from .storage import EventRow, connect, insert_event, report_already_generated


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="macOS productivity tracker")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="Path to config.yaml",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize config and DB")
    sub.add_parser("run", help="Run continuous tracker")
    sub.add_parser("health", help="Run health checks")

    install_agent = sub.add_parser("install", help="Install launch agent")
    install_agent.add_argument(
        "--python",
        dest="python_executable",
        type=str,
        default=sys.executable,
        help="Python executable path",
    )
    install_agent.add_argument(
        "--exec",
        dest="exec_path",
        type=str,
        default="",
        help="Path to standalone worklog executable (default: ~/.local/bin/worklog)",
    )
    install_agent.add_argument(
        "--label",
        type=str,
        default="com.worklog",
        help="launchd label to install",
    )
    install_agent.set_defaults(load=True)
    install_agent.add_argument("--load", dest="load", action="store_true", help="Load after install (default)")
    install_agent.add_argument("--no-load", dest="load", action="store_false", help="Install without loading")

    uninstall_agent = sub.add_parser("uninstall", help="Remove launch agent")
    uninstall_agent.add_argument(
        "--label",
        type=str,
        default="com.worklog",
        help="launchd label to remove",
    )

    report = sub.add_parser("report", help="Generate daily report")
    report.add_argument("--date", type=str, default="", help="Date in YYYY-MM-DD (default: today)")

    return parser.parse_args(argv)


def _cmd_init(config_path: Path) -> int:
    if not config_path.exists():
        write_default_config(config_path)
        print(f"Created config: {config_path}")
    cfg = load_config(config_path)
    conn = connect(cfg.db_path)
    conn.close()
    print(f"Initialized DB: {cfg.db_path}")
    print(f"Reports dir: {cfg.reports_dir}")
    return 0


def _parse_report_day(date_str: str) -> dt.date:
    if not date_str:
        return dt.datetime.now(dt.timezone.utc).date()
    return dt.date.fromisoformat(date_str)


def _cmd_report(config_path: Path, date_str: str) -> int:
    cfg = load_config(config_path)
    conn = connect(cfg.db_path)
    day = _parse_report_day(date_str)
    path = generate_daily_report(
        conn=conn,
        report_day=day,
        reports_dir=cfg.reports_dir,
        focus_block_min_minutes=cfg.focus_block_min_minutes,
        db_path=cfg.db_path,
    )
    conn.close()
    print(f"Generated report: {path}")
    return 0


def _cmd_run(config_path: Path) -> int:
    cfg = load_config(config_path)
    conn = connect(cfg.db_path)

    should_stop = False

    def _stop(_sig: int, _frame: object) -> None:
        nonlocal should_stop
        should_stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    today = dt.datetime.now(dt.timezone.utc).date()
    print("Tracker started. Press Ctrl+C to stop.")

    while not should_stop:
        now_day = dt.datetime.now(dt.timezone.utc).date()
        if now_day != today:
            if not report_already_generated(conn, today.isoformat()):
                generate_daily_report(
                    conn=conn,
                    report_day=today,
                    reports_dir=cfg.reports_dir,
                    focus_block_min_minutes=cfg.focus_block_min_minutes,
                    db_path=cfg.db_path,
                )
            today = now_day

        app_name, bundle_id, title = current_front_context()
        if app_name in (cfg.ignored_apps or []):
            time.sleep(cfg.sample_interval_sec)
            continue

        if not app_name or app_name == "Unknown":
            app_name, bundle_id, title = current_front_context()
        is_idle = 1 if idle_seconds() >= cfg.idle_threshold_sec else 0

        insert_event(
            conn,
            EventRow(
                timestamp=now_iso(),
                app_name=app_name,
                bundle_id=bundle_id,
                window_title=title,
                is_idle=is_idle,
            ),
        )

        time.sleep(cfg.sample_interval_sec)

    conn.close()
    print("Tracker stopped.")
    return 0


def _launchctl_status(label: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return False, f"launchctl unavailable: {exc}"

    if result.returncode != 0:
        return False, f"launchctl list failed: {result.returncode}"

    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line or not line.endswith(label):
            continue
        parts = line.split()
        if len(parts) >= 3:
            pid, status, found_label = parts[0], parts[1], parts[2]
            if found_label == label:
                return True, f"pid={pid}, last_exit_status={status}"
        return True, line

    return False, "not loaded"


def _first_existing_path(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _cmd_health(config_path: Path) -> int:
    checks: list[tuple[str, bool, str]] = []

    try:
        cfg = load_config(config_path)
        checks.append(("config", True, str(config_path)))
    except Exception as exc:
        checks.append(("config", False, str(exc)))
        cfg = None

    if cfg is not None:
        try:
            conn = connect(cfg.db_path)
            count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()[0]
            conn.close()
            checks.append(("database", True, f"{cfg.db_path} (events={count})"))
        except Exception as exc:
            checks.append(("database", False, str(exc)))

        try:
            app_name, bundle_id, title = current_front_context()
            details = f"app={app_name or 'Unknown'}"
            if bundle_id:
                details += f", bundle={bundle_id}"
            if title:
                details += ", title=present"
            else:
                details += ", title=empty"
            checks.append(("frontmost-detection", bool(app_name), details))
        except Exception as exc:
            checks.append(("frontmost-detection", False, str(exc)))

    plist_path = _first_existing_path([Path.home() / "Library" / "LaunchAgents" / "com.worklog.plist"])
    if plist_path.exists():
        try:
            with plist_path.open("rb") as f:
                plist = plistlib.load(f)
            args = plist.get("ProgramArguments", [])
            python_path = args[0] if args else ""
            checks.append(("launchagent-plist", True, f"{plist_path} (python={python_path})"))
        except Exception as exc:
            checks.append(("launchagent-plist", False, str(exc)))
    else:
        checks.append(("launchagent-plist", False, f"missing: {plist_path}"))

    loaded, launchctl_msg = _launchctl_status("com.worklog")
    checks.append(("launchctl", loaded, launchctl_msg))

    ok_all = True
    for name, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")
        if not ok:
            ok_all = False

    if not ok_all:
        print("Health check failed. See FAIL items above.")
        return 1

    print("Health check passed.")
    return 0


def _cmd_install_agent(
    config_path: Path,
    python_executable: str,
    exec_path: str,
    label: str,
    load: bool,
) -> int:
    def _resolve_python_executable(value: str) -> str:
        candidate = Path(value).expanduser()
        if candidate.is_absolute() or "/" in value:
            absolute = candidate if candidate.is_absolute() else (Path.cwd() / candidate)
            absolute = Path(str(absolute))
            if not absolute.exists():
                raise FileNotFoundError(f"Python executable not found: {absolute}")
            return str(absolute)

        found = shutil.which(value)
        if not found:
            raise FileNotFoundError(f"Python executable not found in PATH: {value}")
        return found

    default_exec_path = Path.home() / ".local" / "bin" / "worklog"
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{label}.plist"

    logs_dir = Path.home() / ".worklog" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    effective_exec_path = exec_path.strip()
    if not effective_exec_path and default_exec_path.exists():
        effective_exec_path = str(default_exec_path)

    if effective_exec_path:
        candidate = Path(effective_exec_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        candidate = Path(str(candidate))
        if not candidate.exists():
            raise FileNotFoundError(f"Executable not found: {candidate}")
        exec_abs = str(candidate)
        program_args = f"""
    <key>ProgramArguments</key>
    <array>
      <string>{exec_abs}</string>
      <string>--config</string>
      <string>{config_path}</string>
      <string>run</string>
    </array>
"""
        mode = f"exec={exec_abs}"
    else:
        python_exe = _resolve_python_executable(python_executable)
        program_args = f"""
    <key>ProgramArguments</key>
    <array>
      <string>{python_exe}</string>
      <string>-m</string>
      <string>src.main</string>
      <string>--config</string>
      <string>{config_path}</string>
      <string>run</string>
    </array>
"""
        mode = f"python={python_exe}"

    content = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
  <dict>
    <key>Label</key>
    <string>{label}</string>
{program_args}

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>{Path.cwd()}</string>

    <key>StandardOutPath</key>
    <string>{logs_dir / "tracker.out.log"}</string>

    <key>StandardErrorPath</key>
    <string>{logs_dir / "tracker.err.log"}</string>
  </dict>
</plist>
"""

    plist_path.write_text(content, encoding="utf-8")
    print(f"Installed: {plist_path} ({mode})")

    if load:
        uid = subprocess.check_output(["id", "-u"], text=True).strip()
        subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(plist_path)], check=False)
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)], check=False)
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"], check=False)
        print("Loaded launch agent.")

    return 0


def _cmd_uninstall_agent(label: str) -> int:
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

    bootout_results = []
    bootout_results.append(
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}", str(plist_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    )
    bootout_results.append(
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}/{label}"],
            check=False,
            capture_output=True,
            text=True,
        )
    )

    if plist_path.exists():
        plist_path.unlink()
        print(f"Removed plist: {plist_path}")
    else:
        print(f"Plist not found: {plist_path}")

    unloaded = any(r.returncode == 0 for r in bootout_results)
    if unloaded:
        print(f"Unloaded launch agent: {label}")

    print(f"Uninstalled launch agent: {label}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if args.command == "init":
        return _cmd_init(args.config)
    if args.command == "report":
        return _cmd_report(args.config, args.date)
    if args.command == "run":
        return _cmd_run(args.config)
    if args.command == "health":
        return _cmd_health(args.config)
    if args.command == "install":
        return _cmd_install_agent(
            args.config,
            args.python_executable,
            args.exec_path,
            args.label,
            args.load,
        )
    if args.command == "uninstall":
        return _cmd_uninstall_agent(args.label)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
