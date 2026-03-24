"""tests/test_stats_service.py
==========================
Unit tests for the StatsService and StatsRepository.
"""
import pytest
from datetime import date, timedelta
from repository.stats_repo import StatsRepository
from services.stats_service import StatsService
from models.study_activity import StudyActivity

@pytest.fixture
def stats_repo(conn_factory):
    return StatsRepository(conn_factory)

@pytest.fixture
def stats_service(stats_repo):
    return StatsService(stats_repo)

class TestStatsService:

    def test_add_xp_new_day(self, stats_service):
        activity = stats_service.add_xp(10)
        assert activity.xp == 10
        assert activity.streak_days == 1
        assert activity.activity_date == date.today()

    def test_add_xp_existing_day(self, stats_service):
        stats_service.add_xp(10)
        activity = stats_service.add_xp(20)
        assert activity.xp == 30
        assert activity.streak_days == 1

    def test_streak_continuation(self, stats_service, stats_repo):
        # Manually create activity for yesterday
        yesterday = date.today() - timedelta(days=1)
        stats_repo.create(yesterday, 50, 5)
        
        # Add XP today should result in streak 6
        activity = stats_service.add_xp(10)
        assert activity.streak_days == 6

    def test_get_today_empty(self, stats_service):
        activity = stats_service.get_today()
        assert activity.xp == 0
        assert activity.id == 0

    def test_get_weekly_history(self, stats_service):
        stats_service.add_xp(10)
        history = stats_service.get_weekly_history()
        assert len(history) == 1
        assert history[0].xp == 10

    def test_add_zero_xp_returns_today(self, stats_service):
        activity = stats_service.add_xp(0)
        assert activity.xp == 0
