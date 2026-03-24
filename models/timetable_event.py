"""models/timetable_event.py — Timetable Event domain model."""
from __future__ import annotations
from dataclasses import dataclass

VALID_TYPES = frozenset({"class", "study", "break", "exam"})
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class TimetableEvent:
    """A single timetable entry (recurring or one-off)."""
    id: int
    title: str
    subject: str
    event_type: str       # 'class' | 'study' | 'break' | 'exam'
    day_of_week: int      # 0=Mon … 6=Sun
    start_time: str       # "HH:MM"
    end_time: str         # "HH:MM"
    color: str = "#6C63FF"
    is_recurring: bool = True
    specific_date: str = ""   # "YYYY-MM-DD" for non-recurring events
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Event title cannot be empty.")
        if self.event_type not in VALID_TYPES:
            raise ValueError(
                f"event_type must be one of {VALID_TYPES}, got {self.event_type!r}"
            )
        if not (0 <= self.day_of_week <= 6):
            raise ValueError(f"day_of_week must be 0-6, got {self.day_of_week}")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time.")

    @property
    def day_name(self) -> str:
        return DAYS[self.day_of_week]

    @property
    def duration_minutes(self) -> int:
        sh, sm = map(int, self.start_time.split(":"))
        eh, em = map(int, self.end_time.split(":"))
        return (eh * 60 + em) - (sh * 60 + sm)
