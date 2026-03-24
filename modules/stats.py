"""
modules/stats.py  (Shim)
=========================
Backward-compatible shim over StatsService.
"""
from __future__ import annotations
from database.db import get_connection
from repository.stats_repo import StatsRepository
from services.stats_service import StatsService

_svc = StatsService(StatsRepository(get_connection))

def add_xp(amount: int) -> dict:
    return _svc.add_xp(amount).__dict__

def get_today() -> dict:
    return _svc.get_today().__dict__

def get_weekly_history() -> list[dict]:
    return [a.__dict__ for a in _svc.get_weekly_history()]
