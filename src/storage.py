from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    app_name TEXT NOT NULL,
    bundle_id TEXT,
    window_title TEXT,
    is_idle INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_app_name ON events(app_name);

CREATE TABLE IF NOT EXISTS daily_reports (
    report_date TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    path TEXT NOT NULL,
    total_active_sec INTEGER NOT NULL DEFAULT 0,
    top_app TEXT
);
"""


@dataclass
class EventRow:
    timestamp: str
    app_name: str
    bundle_id: str
    window_title: str
    is_idle: int


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    return conn


def insert_event(conn: sqlite3.Connection, event: EventRow) -> None:
    conn.execute(
        """
        INSERT INTO events(timestamp, app_name, bundle_id, window_title, is_idle)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event.timestamp, event.app_name, event.bundle_id, event.window_title, event.is_idle),
    )
    conn.commit()


def mark_report_generated(
    conn: sqlite3.Connection,
    report_date: str,
    generated_at: str,
    path: str,
    total_active_sec: int,
    top_app: str,
) -> None:
    conn.execute(
        """
        INSERT INTO daily_reports(report_date, generated_at, path, total_active_sec, top_app)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(report_date) DO UPDATE SET
            generated_at=excluded.generated_at,
            path=excluded.path,
            total_active_sec=excluded.total_active_sec,
            top_app=excluded.top_app
        """,
        (report_date, generated_at, path, total_active_sec, top_app),
    )
    conn.commit()


def report_already_generated(conn: sqlite3.Connection, report_date: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM daily_reports WHERE report_date = ?",
        (report_date,),
    ).fetchone()
    return row is not None
