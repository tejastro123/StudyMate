"""repository/focus_repo.py — Focus session persistence."""
from __future__ import annotations
from datetime import date
from .base import BaseRepository
from models.focus_session import FocusSession, DailyFocusStat


class FocusRepository(BaseRepository[FocusSession]):

    def record(
        self, subject: str, duration_minutes: int, session_type: str, completed: bool = True
    ) -> FocusSession:
        return self.record_session(subject, duration_minutes, session_type, completed)

    def record_session(
        self, subject: str, duration_minutes: int, session_type: str, completed: bool = True
    ) -> FocusSession:
        conn = self._conn()
        cur = conn.execute(
            """
            INSERT INTO focus_sessions (subject, duration_minutes, session_type, completed, is_dirty)
            VALUES (?, ?, ?, ?, 1)
            """,
            (subject, duration_minutes, session_type, int(completed)),
        )
        s_id = cur.lastrowid
        conn.commit()
        conn.close()
        return FocusSession(
            id=s_id, subject=subject, duration_minutes=duration_minutes,
            session_type=session_type, completed=completed, is_dirty=1
        )

    def get_today_total_minutes(self) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM focus_sessions WHERE DATE(started_at) = DATE('now')",
        ).fetchone()
        conn.close()
        return int(row[0])

    def get_daily_stats(self, days: int = 7) -> list[DailyFocusStat]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT DATE(started_at) AS day, SUM(duration_minutes) AS total_minutes
            FROM focus_sessions
            WHERE DATE(started_at) >= DATE('now', ?)
            GROUP BY day
            ORDER BY day
            """,
            (f"-{days - 1} days",),
        ).fetchall()
        conn.close()
        return [
            DailyFocusStat(date=r["day"], total_minutes=int(r["total_minutes"]))
            for r in rows
        ]
