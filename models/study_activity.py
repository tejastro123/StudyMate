"""
models/study_activity.py
========================
Domain model representing a single day of study.
"""
from dataclasses import dataclass
from datetime import date

@dataclass
class StudyActivity:
    id: int
    activity_date: date
    xp: int
    streak_days: int
    remote_id: str = ""
