"""tests/test_focus_service.py — FocusService tests."""
import pytest


class TestFocusService:
    def test_record_session(self, focus_service):
        session = focus_service.record_session("Physics", 25, "pomodoro", completed=True)
        assert session.id > 0
        assert session.duration_minutes == 25
        assert session.completed is True

    def test_today_minutes_accumulate(self, focus_service):
        focus_service.record_session("Math", 25, "pomodoro")
        focus_service.record_session("Math", 5, "pomodoro")
        total = focus_service.get_today_minutes()
        assert total == 30

    def test_daily_stats(self, focus_service):
        focus_service.record_session("Science", 50, "custom")
        stats = focus_service.get_daily_stats(days=7)
        assert len(stats) >= 1
        today_stat = stats[-1]
        assert today_stat.total_minutes >= 50
        assert today_stat.total_hours == pytest.approx(today_stat.total_minutes / 60, abs=0.01)

    def test_record_invalid_type_raises(self, focus_service):
        with pytest.raises(ValueError):
            focus_service.record_session("Math", 25, "ultra-mode")

    def test_record_zero_minutes_raises(self, focus_service):
        with pytest.raises(ValueError):
            focus_service.record_session("Math", 0, "pomodoro")
