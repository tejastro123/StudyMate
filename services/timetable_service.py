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
                    title=f"\U0001f4c5 Starting soon: {ev.title}",
                    message=f"{ev.start_time} \u2013 {ev.end_time}  |  {ev.subject}",
                    app_name="StudyMate",
                    timeout=8,
                )
            except Exception as exc:
                logger.warning("Notification failed: %s", exc)

    # ── ICS Export / Import ──────────────────────────────────────────

    def export_ics(self, output_path: str) -> int:
        """
        Export all timetable events to an .ics file.
        Returns the number of events exported.
        """
        from icalendar import Calendar, Event as ICSEvent
        from datetime import datetime, date, timedelta
        import uuid

        cal = Calendar()
        cal.add("prodid", "-//StudyMate//Timetable//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("x-wr-calname", "StudyMate Timetable")

        events = self.get_all()
        count = 0
        today = date.today()
        WEEKDAY_NAMES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

        for ev in events:
            ics_ev = ICSEvent()
            ics_ev.add("uid", str(uuid.uuid4()))
            ics_ev.add("summary", f"{ev.title} [{ev.subject}]".strip(" []"))
            ics_ev.add("description", f"Type: {ev.event_type or 'Class'}  |  Subject: {ev.subject or ''}")

            if ev.is_recurring and ev.day_of_week is not None:
                # Create event for the next occurrence of this weekday
                days_ahead = (ev.day_of_week - today.weekday()) % 7
                event_date = today + timedelta(days=days_ahead)
            elif ev.specific_date:
                try:
                    event_date = date.fromisoformat(str(ev.specific_date))
                except Exception:
                    event_date = today
            else:
                event_date = today

            # Parse times
            try:
                start_h, start_m = map(int, (ev.start_time or "09:00").split(":"))
                end_h, end_m = map(int, (ev.end_time or "10:00").split(":"))
            except Exception:
                start_h, start_m, end_h, end_m = 9, 0, 10, 0

            ics_ev.add("dtstart", datetime(event_date.year, event_date.month, event_date.day, start_h, start_m))
            ics_ev.add("dtend",   datetime(event_date.year, event_date.month, event_date.day, end_h, end_m))
            ics_ev.add("dtstamp", datetime.now())

            if ev.is_recurring and ev.day_of_week is not None:
                ics_ev.add("rrule", {"freq": "weekly", "byday": WEEKDAY_NAMES[ev.day_of_week]})

            cal.add_component(ics_ev)
            count += 1

        with open(output_path, "wb") as f:
            f.write(cal.to_ical())

        log_activity(f"Exported {count} events to ICS", "Timetable")
        return count
