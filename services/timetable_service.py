"""
services/timetable_service.py
==============================
Business logic for timetable events.
"""
from __future__ import annotations
import logging

from repository.timetable_repo import TimetableRepository
from models.timetable_event import TimetableEvent
from database.db import log_activity

logger = logging.getLogger(__name__)


class TimetableService:

    def __init__(self, repo: TimetableRepository) -> None:
        self._repo = repo

    def get_all(self) -> list[TimetableEvent]:
        return self._repo.get_all()

    def get_today(self) -> list[TimetableEvent]:
        return self._repo.get_today()

    def get_upcoming(self, window_minutes: int = 6) -> list[TimetableEvent]:
        return self._repo.get_upcoming(window_minutes)

    def add(
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
        event = self._repo.create(
            title=title, subject=subject, event_type=event_type,
            day_of_week=day_of_week, start_time=start_time, end_time=end_time,
            color=color, is_recurring=is_recurring, specific_date=specific_date,
        )
        log_activity(f"Added event '{title}'", "Timetable")
        return event

    def update(self, event_id: int, **kwargs) -> None:
        self._repo.update(event_id, **kwargs)
        log_activity(f"Updated event #{event_id}", "Timetable")

    def delete(self, event_id: int) -> None:
        self._repo.delete(event_id)
        log_activity(f"Deleted event #{event_id}", "Timetable")

    def notify_upcoming(self) -> None:
        """Fire plyer system notifications for events starting within 6 minutes."""
        events = self.get_upcoming(window_minutes=6)
        for ev in events:
            try:
                from plyer import notification
                notification.notify(
                    title=f"📅 Starting soon: {ev.title}",
                    message=f"{ev.start_time} – {ev.end_time}  |  {ev.subject}",
                    app_name="StudyMate",
                    timeout=8,
                )
            except Exception as exc:
                logger.warning("Notification failed: %s", exc)
