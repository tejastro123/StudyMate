"""models/deck.py — Flashcard Deck domain model."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Deck:
    """Represents a flashcard deck owned by the user."""
    id: int
    name: str
    subject: str = ""
    created_at: str = ""
    remote_id: str = ""
    is_dirty: int = 0
    updated_at: str = ""

    # Computed stats (populated by repository JOIN queries)
    total_cards: int = 0
    due_today: int = 0
    mastered: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Deck name cannot be empty.")

    @property
    def is_empty(self) -> bool:
        return self.total_cards == 0

    @property
    def mastery_pct(self) -> float:
        """Percentage of cards considered mastered (ease_factor ≥ 2.5)."""
        if self.total_cards == 0:
            return 0.0
        return round(100 * self.mastered / self.total_cards, 1)
