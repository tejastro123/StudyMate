"""models/flashcard.py — Flashcard domain model."""
from __future__ import annotations
from dataclasses import dataclass


VALID_DIFFICULTIES = frozenset({"new", "easy", "medium", "hard"})


@dataclass
class Flashcard:
    """A single flashcard belonging to a deck."""
    id: int
    deck_id: int
    front: str
    back: str
    difficulty: str = "new"
    ease_factor: float = 2.5
    interval_days: int = 1
    due_date: str = ""        # ISO date string "YYYY-MM-DD"
    created_at: str = ""
    review_count: int = 0
    remote_id: str = ""
    is_dirty: int = 0
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.front.strip():
            raise ValueError("Flashcard front text cannot be empty.")
        if not self.back.strip():
            raise ValueError("Flashcard back text cannot be empty.")
        if self.difficulty not in VALID_DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {VALID_DIFFICULTIES}, got {self.difficulty!r}"
            )

    @property
    def is_due(self) -> bool:
        """True if this card is due for review today or overdue."""
        from datetime import date
        if not self.due_date:
            return True
        return self.due_date <= date.today().isoformat()

    @property
    def is_mastered(self) -> bool:
        return self.ease_factor >= 2.5 and self.difficulty == "easy"
