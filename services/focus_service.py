"""
services/focus_service.py
==========================
Business logic for focus session recording and analytics.
"""
from __future__ import annotations
import logging

from repository.focus_repo import FocusRepository
from models.focus_session import FocusSession, DailyFocusStat
from database.db import log_activity

logger = logging.getLogger(__name__)


class FocusService:

    def __init__(self, repo: FocusRepository) -> None:
        self._repo = repo

    def record_session(
        self,
        subject: str,
        duration_minutes: int,
        session_type: str,
        completed: bool = True,
    ) -> FocusSession:
        session = self._repo.record(subject, duration_minutes, session_type, completed)
        status = "Completed" if completed else "Abandoned"
        log_activity(
            f"{status} focus session ({duration_minutes} min) — {subject}", "Focus Timer"
        )
        logger.info(
            "FocusSession recorded: id=%d %s %dmin type=%s",
            session.id, status, duration_minutes, session_type,
        )
        return session

    def get_today_minutes(self) -> int:
        return self._repo.get_today_total_minutes()

    def get_daily_stats(self, days: int = 7) -> list[DailyFocusStat]:
        return self._repo.get_daily_stats(days)
