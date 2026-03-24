"""
modules/focus_timer.py  (Phase 2 shim)
========================================
Backward-compatible shim over FocusService + FocusRepository.
"""
from __future__ import annotations
from database.db import get_connection
from repository.focus_repo import FocusRepository
from services.focus_service import FocusService

_svc = FocusService(FocusRepository(get_connection))


def record_session(
    subject: str,
    duration_minutes: int,
    session_type: str,
    completed: int = 1,
) -> int:
    session = _svc.record_session(
        subject, duration_minutes, session_type, completed=bool(completed)
    )
    return session.id


def get_today_total_minutes() -> int:
    return _svc.get_today_minutes()


def get_daily_totals(days: int = 7) -> list[dict]:
    stats = _svc.get_daily_stats(days)
    return [{"day": s.date, "total_minutes": s.total_minutes} for s in stats]
