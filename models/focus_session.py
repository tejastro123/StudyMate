"""models/focus_session.py — Focus Session domain model."""
from __future__ import annotations
from dataclasses import dataclass

VALID_TYPES = frozenset({"pomodoro", "custom"})


@dataclass
class FocusSession:
    """A completed or abandoned focus session."""
    id: int
    subject: str
    duration_minutes: int
    session_type: str        # 'pomodoro' | 'custom'
    completed: bool = True
    started_at: str = ""     # ISO datetime string
    remote_id: str = ""

    def __post_init__(self) -> None:
        if self.duration_minutes < 1:
            raise ValueError("duration_minutes must be at least 1.")
        if self.session_type not in VALID_TYPES:
            raise ValueError(
                f"session_type must be one of {VALID_TYPES}, got {self.session_type!r}"
            )

    @property
    def duration_hours(self) -> float:
        return round(self.duration_minutes / 60, 2)


@dataclass
class DailyFocusStat:
    """Aggregated focus minutes for a single calendar day."""
    date: str              # "YYYY-MM-DD"
    total_minutes: int

    @property
    def total_hours(self) -> float:
        return round(self.total_minutes / 60, 2)
