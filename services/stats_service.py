"""
services/stats_service.py
=========================
Business logic for Gamification and XP tracking.
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

from repository.stats_repo import StatsRepository
from models.study_activity import StudyActivity
from database.db import log_activity

logger = logging.getLogger(__name__)

class StatsService:
    def __init__(self, repo: StatsRepository) -> None:
        self._repo = repo

    def add_xp(self, amount: int) -> StudyActivity:
        if amount <= 0:
            return self.get_today()
            
        today = date.today()
        activity = self._repo.get_by_date(today)

        if activity:
            new_xp = activity.xp + amount
            self._repo.update(activity.id, new_xp, activity.streak_days)
            activity.xp = new_xp
            logger.debug(f"Added {amount} XP. Total today: {new_xp}")
            return activity
            
        # Create new daily record
        yesterday = today - timedelta(days=1)
        prev_activity = self._repo.get_by_date(yesterday)
        streak = prev_activity.streak_days + 1 if prev_activity else 1
        
        log_activity(f"Got a {streak} day streak!", "Gamification")
        return self._repo.create(today, amount, streak)

    def get_today(self) -> StudyActivity:
        today = date.today()
        activity = self._repo.get_by_date(today)
        if not activity:
            # Check for streak continuation
            yesterday = today - timedelta(days=1)
            prev_activity = self._repo.get_by_date(yesterday)
            streak = prev_activity.streak_days if prev_activity else 0
            # We don't increment the streak until they earn XP
            return StudyActivity(id=0, activity_date=today, xp=0, streak_days=streak)
        return activity

    def get_weekly_history(self) -> list[StudyActivity]:
        return self._repo.get_last_n_days(7)
