"""
repository/stats_repo.py
========================
Data access for the `study_activity` table.
"""
import sqlite3
from typing import Callable
from datetime import date, timedelta
from .base import BaseRepository
from models.study_activity import StudyActivity

class StatsRepository(BaseRepository[StudyActivity]):
    def __init__(self, conn_factory: Callable[[], sqlite3.Connection]) -> None:
        super().__init__(conn_factory)

    def _conn(self) -> sqlite3.Connection:
        """Helper to get a connection."""
        return self._conn_factory()

    @staticmethod
    def _row_to_activity(row: sqlite3.Row) -> StudyActivity:
        """Converts a database row to a StudyActivity object."""
        return StudyActivity(
            id=row["id"],
            activity_date=date.fromisoformat(row["date"]),
            xp=row["xp"],
            streak_days=row["streak_days"],
            remote_id=row["remote_id"] if "remote_id" in row and row["remote_id"] else "",
            is_dirty=bool(row["is_dirty"]) if "is_dirty" in row else False,
        )

    def get_by_date(self, target_date: date) -> StudyActivity | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT id, date, xp, streak_days, remote_id, is_dirty FROM study_activity WHERE date = ?",
            (target_date.isoformat(),),
        ).fetchone()
        conn.close()
        
        if row:
            return self._row_to_activity(row)
        return None

    def get_last_n_days(self, n: int) -> list[StudyActivity]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, date, xp, streak_days, remote_id, is_dirty FROM study_activity ORDER BY date DESC LIMIT ?",
            (n,),
        ).fetchall()
        conn.close()
        return [self._row_to_activity(r) for r in rows]

    def _calculate_current_streak(self, conn: sqlite3.Connection, today: date) -> int:
        """Calculates the current streak based on consecutive days with activity."""
        streak = 0
        current_date = today
        
        # Check if today has activity
        today_activity = conn.execute(
            "SELECT id FROM study_activity WHERE date = ?", (today.isoformat(),)
        ).fetchone()
        if today_activity:
            streak += 1
            current_date -= timedelta(days=1) # Start checking from yesterday

        # Check previous days
        while True:
            prev_day_activity = conn.execute(
                "SELECT id FROM study_activity WHERE date = ?", (current_date.isoformat(),)
            ).fetchone()
            if prev_day_activity:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        return streak

    def track_activity(self, activity_date: date, xp_gain: int) -> StudyActivity:
        """Add XP to a specific date and update the current streak."""
        conn = self._conn()
        existing = conn.execute(
            "SELECT id, date, xp, streak_days, remote_id, is_dirty FROM study_activity WHERE date = ?", (activity_date.isoformat(),)
        ).fetchone()

        if existing:
            new_xp = existing["xp"] + xp_gain
            conn.execute(
                "UPDATE study_activity SET xp = ?, is_dirty = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_xp, existing["id"])
            )
            conn.commit()
            conn.close()
            # Create a new row-like object with updated xp for _row_to_activity
            updated_row = dict(existing)
            updated_row["xp"] = new_xp
            updated_row["is_dirty"] = 1
            return self._row_to_activity(updated_row)
        else:
            # Handle streak
            streak = self._calculate_current_streak(conn, activity_date)
            cur = conn.execute(
                "INSERT INTO study_activity (date, xp, streak_days, is_dirty) VALUES (?, ?, ?, 1)",
                (activity_date.isoformat(), xp_gain, streak)
            )
            s_id = cur.lastrowid
            conn.commit()
            conn.close()
            return StudyActivity(id=s_id, activity_date=activity_date, xp=xp_gain, streak_days=streak, is_dirty=1, remote_id="")

    def create(self, activity_date: date, xp: int, streak_days: int, remote_id: str = "", is_dirty: bool = True) -> StudyActivity:
        conn = self._conn()
        r_id = remote_id if remote_id else None
        cur = conn.execute(
            "INSERT INTO study_activity (date, xp, streak_days, remote_id, is_dirty) VALUES (?, ?, ?, ?, ?)",
            (activity_date.isoformat(), xp, streak_days, r_id, int(is_dirty)),
        )
        act_id = cur.lastrowid
        conn.commit()
        conn.close()
        return StudyActivity(id=act_id, activity_date=activity_date, xp=xp, streak_days=streak_days, remote_id=remote_id, is_dirty=is_dirty)

    def update(self, act_id: int, xp: int, streak_days: int) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE study_activity SET xp = ?, streak_days = ?, is_dirty = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (xp, streak_days, act_id),
        )
        conn.commit()
        conn.close()
