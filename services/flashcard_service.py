"""
services/flashcard_service.py
==============================
Business logic for decks and flashcards.

Owns:
- Spaced-repetition algorithm (SM-2 variant)
- Deck / card CRUD delegating to repositories
- Activity logging
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

from repository.deck_repo import DeckRepository
from repository.flashcard_repo import FlashcardRepository
from models.deck import Deck
from models.flashcard import Flashcard
from database.db import log_activity

logger = logging.getLogger(__name__)


class FlashcardService:
    """Orchestrates deck + flashcard operations with spaced-repetition."""

    def __init__(
        self,
        deck_repo: DeckRepository,
        card_repo: FlashcardRepository,
    ) -> None:
        self._decks = deck_repo
        self._cards = card_repo

    # ── Decks ────────────────────────────────────────────────────────────────

    def get_all_decks(self) -> list[Deck]:
        return self._decks.get_all()

    def create_deck(self, name: str, subject: str = "") -> Deck:
        deck = self._decks.create(name, subject)
        log_activity(f"Created deck '{name}'", "Flashcards")
        return deck

    def rename_deck(self, deck_id: int, new_name: str) -> None:
        self._decks.rename(deck_id, new_name)
        log_activity(f"Renamed deck #{deck_id} to '{new_name}'", "Flashcards")

    def delete_deck(self, deck_id: int) -> None:
        self._decks.delete(deck_id)
        log_activity(f"Deleted deck #{deck_id}", "Flashcards")

    # ── Flashcards ───────────────────────────────────────────────────────────

    def get_cards(self, deck_id: int) -> list[Flashcard]:
        return self._cards.get_for_deck(deck_id)

    def get_due_cards(self, deck_id: int) -> list[Flashcard]:
        return self._cards.get_due(deck_id)

    def add_card(self, deck_id: int, front: str, back: str) -> Flashcard:
        card = self._cards.create(deck_id, front, back)
        log_activity(f"Added card to deck #{deck_id}", "Flashcards")
        return card

    def update_card(self, card_id: int, front: str, back: str) -> None:
        self._cards.update(card_id, front, back)

    def delete_card(self, card_id: int) -> None:
        self._cards.delete(card_id)
        log_activity(f"Deleted card #{card_id}", "Flashcards")

    # ── Spaced Repetition (SM-2) ─────────────────────────────────────────────

    def record_review(self, card_id: int, difficulty: str) -> None:
        """
        Update ease_factor and next due_date using a simplified SM-2 algorithm.

        difficulty: 'easy' | 'medium' | 'hard'
        """
        card = self._cards.get_by_id(card_id)
        if card is None:
            raise ValueError(f"Card #{card_id} not found.")

        ef = card.ease_factor
        interval = card.interval_days

        if difficulty == "easy":
            ef = min(ef + 0.15, 3.0)
            interval = max(1, round(interval * ef))
        elif difficulty == "medium":
            ef = max(ef - 0.08, 1.3)
            interval = max(1, round(interval * ef * 0.9))
        else:  # hard
            ef = max(ef - 0.20, 1.3)
            interval = 1  # reset to tomorrow

        new_due = (date.today() + timedelta(days=interval)).isoformat()
        self._cards.update_review(card_id, difficulty, ef, interval, new_due)
        logger.debug(
            "Review recorded: card=%d difficulty=%s ef=%.2f interval=%d due=%s",
            card_id, difficulty, ef, interval, new_due,
        )
