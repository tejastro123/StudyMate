"""tests/test_timetable_service.py — TimetableService tests."""
from datetime import date
import pytest


class TestTimetableService:
    def _add_event(self, svc, title="Physics", day=0,
                   start="09:00", end="10:00", recurring=True):
        return svc.add(
            title=title, subject="Science", event_type="class",
            day_of_week=day, start_time=start, end_time=end,
            is_recurring=recurring,
        )

    def test_add_and_get_all(self, timetable_service):
        self._add_event(timetable_service)
        events = timetable_service.get_all()
        assert len(events) == 1
        assert events[0].title == "Physics"

    def test_get_today(self, timetable_service):
        today_dow = date.today().weekday()
        self._add_event(timetable_service, title="Today's Class", day=today_dow)
        self._add_event(timetable_service, title="Other Day", day=(today_dow + 1) % 7)
        today_events = timetable_service.get_today()
        assert any(e.title == "Today's Class" for e in today_events)
        assert not any(e.title == "Other Day" for e in today_events)

    def test_delete(self, timetable_service):
        ev = self._add_event(timetable_service)
        timetable_service.delete(ev.id)
        assert len(timetable_service.get_all()) == 0

    def test_update(self, timetable_service):
        ev = self._add_event(timetable_service, title="Old Title")
        timetable_service.update(ev.id, title="New Title")
        events = timetable_service.get_all()
        assert events[0].title == "New Title"

    def test_add_invalid_event_type_raises(self, timetable_service):
        with pytest.raises(ValueError):
            timetable_service.add(
                title="X", subject="Y", event_type="lecture",  # invalid
                day_of_week=0, start_time="09:00", end_time="10:00",
            )

    def test_add_invalid_time_order_raises(self, timetable_service):
        with pytest.raises(ValueError):
            timetable_service.add(
                title="X", subject="Y", event_type="class",
                day_of_week=0, start_time="11:00", end_time="10:00",
            )
