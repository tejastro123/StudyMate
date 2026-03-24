"""repository/timetable_repo.py — Timetable event persistence."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from .base import BaseRepository
from models.timetable_event import TimetableEvent


class TimetableRepository(BaseRepository[TimetableEvent]):

    def get_all(self) -> list[TimetableEvent]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM timetable_events ORDER BY day_of_week, start_time"
        ).fetchall()
        conn.close()
        return [self._row_to_event(r) for r in rows]

    def get_for_day(self, day_of_week: int) -> list[TimetableEvent]:
        today_str = date.today().isoformat()
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM timetable_events
            WHERE (is_recurring = 1 AND day_of_week = ?)
               OR (is_recurring = 0 AND specific_date = ?)
            ORDER BY start_time
            """,
            (day_of_week, today_str),
        ).fetchall()
        conn.close()
        return [self._row_to_event(r) for r in rows]

    def get_today(self) -> list[TimetableEvent]:
        return self.get_for_day(date.today().weekday())

    def get_upcoming(self, window_minutes: int = 10) -> list[TimetableEvent]:
        """Events starting within the next *window_minutes* minutes."""
        now = datetime.now()
        today_str = date.today().isoformat()
        current_str = now.strftime("%H:%M")
        future_str = (now + timedelta(minutes=window_minutes)).strftime("%H:%M")
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM timetable_events
            WHERE ((is_recurring = 1 AND day_of_week = ?)
                   OR (is_recurring = 0 AND specific_date = ?))
              AND start_time > ?
              AND start_time <= ?
            ORDER BY start_time
            """,
            (now.weekday(), today_str, current_str, future_str),
        ).fetchall()
        conn.close()
        return [self._row_to_event(r) for r in rows]

    def create(
        self,
        title: str,
        subject: str,
        event_type: str,
        day_of_week: int,
        start_time: str,
        end_time: str,
        color: str = "#6C63FF",
        is_recurring: bool = True,
        specific_date: str = "",
    ) -> TimetableEvent:
        conn = self._conn()
        cur = conn.execute(
            """
            INSERT INTO timetable_events
                (title, subject, event_type, day_of_week, start_time, end_time,
                 color, is_recurring, specific_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, subject, event_type, day_of_week, start_time, end_time,
             color, int(is_recurring), specific_date or None),
        )
        event_id = cur.lastrowid
        conn.commit()
        conn.close()
        return TimetableEvent(
            id=event_id, title=title, subject=subject, event_type=event_type,
            day_of_week=day_of_week, start_time=start_time, end_time=end_time,
            color=color, is_recurring=is_recurring, specific_date=specific_date,
        )

    def update(self, event_id: int, **kwargs) -> None:
        fields = {
            "title", "subject", "event_type", "day_of_week",
            "start_time", "end_time", "color", "is_recurring", "specific_date",
        }
        updates = {k: v for k, v in kwargs.items() if k in fields}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn = self._conn()
        conn.execute(
            f"UPDATE timetable_events SET {set_clause} WHERE id = ?",
            (*updates.values(), event_id),
        )
        conn.commit()
        conn.close()

    def delete(self, event_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM timetable_events WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def _row_to_event(row) -> TimetableEvent:
        return TimetableEvent(
            id=row["id"],
            title=row["title"],
            subject=row["subject"] or "",
            event_type=row["event_type"] or "class",
            day_of_week=int(row["day_of_week"]),
            start_time=row["start_time"],
            end_time=row["end_time"],
            color=row["color"] or "#6C63FF",
            is_recurring=bool(row["is_recurring"]),
            specific_date=row["specific_date"] or "",
            created_at=row["created_at"] or "",
        )
