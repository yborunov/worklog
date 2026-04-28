from __future__ import annotations

import datetime as dt
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .storage import mark_report_generated


@dataclass
class Session:
    start: dt.datetime
    end: dt.datetime
    app_name: str
    window_title: str
    is_idle: bool

    @property
    def duration_sec(self) -> int:
        return int((self.end - self.start).total_seconds())


def parse_ts(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def fmt_seconds(total: int) -> str:
    h, rem = divmod(max(0, total), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fetch_day_events(conn: sqlite3.Connection, day: dt.date) -> list[sqlite3.Row]:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc).isoformat(timespec="seconds")
    end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc).isoformat(
        timespec="seconds"
    )
    return list(
        conn.execute(
            """
            SELECT timestamp, app_name, bundle_id, window_title, is_idle
            FROM events
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp ASC
            """,
            (start, end),
        )
    )


def _sessionize(rows: list[sqlite3.Row], max_gap_sec: int = 15) -> list[Session]:
    if not rows:
        return []
    sessions: list[Session] = []
    start = parse_ts(rows[0]["timestamp"])
    prev = start
    app = rows[0]["app_name"]
    title = rows[0]["window_title"] or ""
    idle = bool(rows[0]["is_idle"])

    for row in rows[1:]:
        ts = parse_ts(row["timestamp"])
        cur_app = row["app_name"]
        cur_title = row["window_title"] or ""
        cur_idle = bool(row["is_idle"])
        gap = (ts - prev).total_seconds()

        changed = cur_app != app or cur_title != title or cur_idle != idle or gap > max_gap_sec
        if changed:
            sessions.append(Session(start=start, end=prev, app_name=app, window_title=title, is_idle=idle))
            start = ts
            app = cur_app
            title = cur_title
            idle = cur_idle
        prev = ts

    sessions.append(Session(start=start, end=prev, app_name=app, window_title=title, is_idle=idle))
    return [s for s in sessions if s.duration_sec >= 0]


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def generate_daily_report(
    conn: sqlite3.Connection,
    report_day: dt.date,
    reports_dir: str,
    focus_block_min_minutes: int,
    db_path: str,
) -> Path:
    rows = _fetch_day_events(conn, report_day)
    sessions = _sessionize(rows)

    active_sessions = [s for s in sessions if not s.is_idle]
    idle_sessions = [s for s in sessions if s.is_idle]

    total_active = sum(s.duration_sec for s in active_sessions)
    total_idle = sum(s.duration_sec for s in idle_sessions)
    context_switches = max(0, len(active_sessions) - 1)

    app_totals: dict[str, int] = defaultdict(int)
    title_totals: dict[tuple[str, str], int] = defaultdict(int)

    for s in active_sessions:
        app_totals[s.app_name] += s.duration_sec
        title_totals[(s.app_name, s.window_title)] += s.duration_sec

    top_app = ""
    if app_totals:
        top_app = max(app_totals.items(), key=lambda item: item[1])[0]

    app_rows: list[list[str]] = []
    for app, secs in sorted(app_totals.items(), key=lambda x: x[1], reverse=True):
        pct = (secs / total_active * 100.0) if total_active else 0.0
        app_rows.append([app, fmt_seconds(secs), f"{pct:.1f}%"])

    title_rows: list[list[str]] = []
    for (app, title), secs in sorted(title_totals.items(), key=lambda x: x[1], reverse=True):
        title_rows.append([app, title or "(No title)", fmt_seconds(secs)])

    timeline_rows: list[list[str]] = []
    for s in sessions:
        timeline_rows.append(
            [
                s.start.astimezone().strftime("%H:%M:%S"),
                s.end.astimezone().strftime("%H:%M:%S"),
                s.app_name,
                s.window_title or "(No title)",
                fmt_seconds(s.duration_sec),
                "idle" if s.is_idle else "active",
            ]
        )

    focus_threshold = max(5, focus_block_min_minutes) * 60
    focus_rows: list[list[str]] = []
    for s in active_sessions:
        if s.duration_sec >= focus_threshold:
            focus_rows.append(
                [
                    s.start.astimezone().strftime("%H:%M:%S"),
                    s.end.astimezone().strftime("%H:%M:%S"),
                    s.app_name,
                    s.window_title or "(No title)",
                    fmt_seconds(s.duration_sec),
                ]
            )

    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report_day.isoformat()}.md"

    start_filter = dt.datetime.combine(report_day, dt.time.min, tzinfo=dt.timezone.utc).isoformat(timespec="seconds")
    end_filter = dt.datetime.combine(report_day + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc).isoformat(
        timespec="seconds"
    )

    lines: list[str] = []
    lines.append(f"# Daily Productivity Report - {report_day.isoformat()}")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Active time: {fmt_seconds(total_active)}")
    lines.append(f"- Idle time: {fmt_seconds(total_idle)}")
    lines.append(f"- Context switches: {context_switches}")
    lines.append("")

    lines.append("## Time by App")
    lines.append("")
    if app_rows:
        lines.append(_markdown_table(["App", "Duration", "% Active"], app_rows))
    else:
        lines.append("No active sessions captured.")
    lines.append("")

    lines.append("## Time by Window Title")
    lines.append("")
    if title_rows:
        lines.append(_markdown_table(["App", "Window Title", "Duration"], title_rows))
    else:
        lines.append("No window title activity captured.")
    lines.append("")

    lines.append("## Chronological Timeline")
    lines.append("")
    if timeline_rows:
        lines.append(_markdown_table(["Start", "End", "App", "Window Title", "Duration", "Type"], timeline_rows))
    else:
        lines.append("No events captured for this day.")
    lines.append("")

    lines.append("## Focus Blocks")
    lines.append("")
    lines.append(f"Threshold: {max(5, focus_block_min_minutes)} minutes")
    lines.append("")
    if focus_rows:
        lines.append(_markdown_table(["Start", "End", "App", "Window Title", "Duration"], focus_rows))
    else:
        lines.append("No focus blocks met threshold.")
    lines.append("")

    lines.append("## Raw Data References")
    lines.append("")
    lines.append(f"- Database: `{db_path}`")
    lines.append("- Event query:")
    lines.append("```sql")
    lines.append("SELECT timestamp, app_name, bundle_id, window_title, is_idle")
    lines.append("FROM events")
    lines.append(f"WHERE timestamp >= '{start_filter}' AND timestamp < '{end_filter}'")
    lines.append("ORDER BY timestamp ASC;")
    lines.append("```")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    mark_report_generated(
        conn=conn,
        report_date=report_day.isoformat(),
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        path=str(out_path),
        total_active_sec=total_active,
        top_app=top_app,
    )

    return out_path
