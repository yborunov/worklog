from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


def default_base_dir() -> Path:
    return Path.home() / ".worklog"


@dataclass
class TrackerConfig:
    sample_interval_sec: int = 5
    idle_threshold_sec: int = 300
    focus_block_min_minutes: int = 25
    ignored_apps: list[str] | None = None
    db_path: str = ""
    reports_dir: str = ""
    logs_dir: str = ""

    def normalized(self) -> "TrackerConfig":
        base = default_base_dir()
        ignored = self.ignored_apps if self.ignored_apps is not None else []
        return TrackerConfig(
            sample_interval_sec=max(1, int(self.sample_interval_sec)),
            idle_threshold_sec=max(30, int(self.idle_threshold_sec)),
            focus_block_min_minutes=max(5, int(self.focus_block_min_minutes)),
            ignored_apps=ignored,
            db_path=self.db_path or str(base / "tracker.db"),
            reports_dir=self.reports_dir or str(base / "reports"),
            logs_dir=self.logs_dir or str(base / "logs"),
        )


def default_config_path() -> Path:
    return default_base_dir() / "config.yaml"


def ensure_parent_dirs(config: TrackerConfig) -> None:
    Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.reports_dir).mkdir(parents=True, exist_ok=True)
    Path(config.logs_dir).mkdir(parents=True, exist_ok=True)


def write_default_config(path: Path | None = None) -> Path:
    cfg_path = path or default_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = TrackerConfig(
        ignored_apps=["ScreenSaverEngine", "loginwindow"],
    ).normalized()
    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(cfg), f, sort_keys=True)
    return cfg_path


def load_config(path: Path | None = None) -> TrackerConfig:
    cfg_path = path or default_config_path()
    if not cfg_path.exists():
        write_default_config(cfg_path)
    with cfg_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    cfg = TrackerConfig(**raw).normalized()
    ensure_parent_dirs(cfg)
    return cfg
