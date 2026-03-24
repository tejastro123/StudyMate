"""models/quiz.py — Quiz domain model."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Quiz:
    """A quiz container with metadata."""
    id: int
    title: str
    subject: str = ""
    created_at: str = ""

    # Populated by JOIN
    question_count: int = 0
    last_score_pct: float | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Quiz title cannot be empty.")
