#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install productivity tracker launch agent")
    p.add_argument("--python", default=sys.executable, help="Python executable path")
    p.add_argument(
        "--exec",
        dest="exec_path",
        default="",
        help="Path to standalone worklog executable (skips Python module mode)",
    )
    p.add_argument(
        "--config",
        default=str(Path.home() / ".worklog" / "config.yaml"),
        help="Path to tracker config",
    )
    p.add_argument(
        "--label",
        default="com.worklog",
        help="launchd label to install",
    )
    p.add_argument("--load", action="store_true", help="Load the launch agent after install")
    return p.parse_args()


def resolve_python_executable(value: str) -> str:
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


def main() -> int:
    args = parse_args()
    use_exec_mode = bool(args.exec_path)
    python_exe = ""
    exec_path = ""
    if use_exec_mode:
        candidate = Path(args.exec_path).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        candidate = Path(str(candidate))
        if not candidate.exists():
            raise FileNotFoundError(f"Executable not found: {candidate}")
        exec_path = str(candidate)
    else:
        python_exe = resolve_python_executable(args.python)

    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{args.label}.plist"

    logs_dir = Path.home() / ".worklog" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if use_exec_mode:
        program_args = f"""
    <key>ProgramArguments</key>
    <array>
      <string>{exec_path}</string>
      <string>--config</string>
      <string>{args.config}</string>
      <string>run</string>
    </array>
"""
    else:
        program_args = f"""
    <key>ProgramArguments</key>
    <array>
      <string>{python_exe}</string>
      <string>-m</string>
      <string>src.main</string>
      <string>--config</string>
      <string>{args.config}</string>
      <string>run</string>
    </array>
"""

    content = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
  <dict>
    <key>Label</key>
    <string>{args.label}</string>
{program_args}

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>{Path(__file__).resolve().parent.parent}</string>

    <key>StandardOutPath</key>
    <string>{logs_dir / "tracker.out.log"}</string>

    <key>StandardErrorPath</key>
    <string>{logs_dir / "tracker.err.log"}</string>
  </dict>
</plist>
"""

    plist_path.write_text(content, encoding="utf-8")
    mode = f"exec={exec_path}" if use_exec_mode else f"python={python_exe}"
    print(f"Installed: {plist_path} ({mode})")

    if args.load:
        uid = subprocess.check_output(["id", "-u"], text=True).strip()
        for legacy in [
            launch_agents / "com.worklog.plist",
        ]:
            subprocess.run(
                ["launchctl", "bootout", f"gui/{uid}", str(legacy)],
                check=False,
            )
        subprocess.run(
            ["launchctl", "bootout", f"gui/{uid}", str(plist_path)],
            check=False,
        )
        subprocess.run(
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
            check=False,
        )
        subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{uid}/{args.label}"],
            check=False,
        )
        print("Loaded launch agent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
