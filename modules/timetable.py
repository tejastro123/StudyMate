"""
modules/timetable.py  (Shim)
============================
Backward-compatible shim over TimetableService + TimetableRepository.
"""
from __future__ import annotations
from database.db import get_connection
from repository.timetable_repo import TimetableRepository
from services.timetable_service import TimetableService
import logging

logger = logging.getLogger(__name__)

_svc = TimetableService(TimetableRepository(get_connection))


def get_all_events() -> list[dict]:
    return [e.__dict__ for e in _svc.get_all()]


def get_events_for_day(day_of_week: int) -> list[dict]:
    # The service layer doesn't expose get_events_for_day directly.
    # It exposes get_todays_events() which uses today().
    # For UI compat, we can manually filter the current all_events.
    from datetime import date
    today_str = date.today().isoformat()
    # Or just use the repo directly to avoid complex logic:
    conn = get_connection()
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
    return [dict(r) for r in rows]


def get_todays_events() -> list[dict]:
    return [e.__dict__ for e in _svc.get_today()]


def add_event(
    title: str,
    subject: str,
    event_type: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    color: str = "#6C63FF",
    is_recurring: int = 0,
    specific_date: str = "",
) -> int:
    event = _svc.add(
        title=title, subject=subject, event_type=event_type, 
        day_of_week=day_of_week, start_time=start_time, end_time=end_time,
        color=color, is_recurring=bool(is_recurring), specific_date=specific_date or ""
    )
    return event.id


def update_event(
    event_id: int,
    title: str,
    subject: str,
    event_type: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    color: str,
    is_recurring: int,
    specific_date: str,
) -> None:
    _svc.update(
        event_id=event_id, title=title, subject=subject, event_type=event_type, 
        day_of_week=day_of_week, start_time=start_time, end_time=end_time,
        color=color, is_recurring=bool(is_recurring), specific_date=specific_date or ""
    )


def delete_event(event_id: int) -> None:
    _svc.delete(event_id)


def get_upcoming_events(window_minutes: int = 10) -> list[dict]:
    return [e.__dict__ for e in _svc.get_upcoming(window_minutes)]


def export_ics(output_path: str) -> int:
    return _svc.export_ics(output_path)
