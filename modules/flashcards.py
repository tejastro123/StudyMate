"""
modules/flashcards.py  (Phase 2 shim)
======================================
Backward-compatible shim over FlashcardService + repositories.
The existing UI code imports these functions unchanged.
"""
from __future__ import annotations
from database.db import get_connection
from repository.deck_repo import DeckRepository
from repository.flashcard_repo import FlashcardRepository
from services.flashcard_service import FlashcardService

# ── Shared service instance ─────────────────────────────────────────────────
_svc = FlashcardService(
    DeckRepository(get_connection),
    FlashcardRepository(get_connection),
)


# ── Deck helpers (return dicts for UI backward-compat) ──────────────────────

def get_all_decks() -> list[dict]:
    return [deck.__dict__ for deck in _svc.get_all_decks()]

def create_deck(name: str, subject: str = "") -> int:
    return _svc.create_deck(name, subject).id

def rename_deck(deck_id: int, name: str) -> None:
    _svc.rename_deck(deck_id, name)

def delete_deck(deck_id: int) -> None:
    _svc.delete_deck(deck_id)


# ── Card helpers ─────────────────────────────────────────────────────────────

def get_cards_for_deck(deck_id: int) -> list[dict]:
    return [c.__dict__ for c in _svc.get_cards(deck_id)]

def get_due_cards(deck_id: int) -> list[dict]:
    return [c.__dict__ for c in _svc.get_due_cards(deck_id)]

def add_card(deck_id: int, front: str, back: str) -> int:
    return _svc.add_card(deck_id, front, back).id

def update_card(card_id: int, front: str, back: str) -> None:
    _svc.update_card(card_id, front, back)

def delete_card(card_id: int) -> None:
    _svc.delete_card(card_id)


# ── Spaced repetition ────────────────────────────────────────────────────────

def record_review(card_id: int, difficulty: str) -> None:
    _svc.record_review(card_id, difficulty)
    import modules.stats as stats_logic
    xp_map = {"easy": 1, "medium": 2, "hard": 3}
    stats_logic.add_xp(xp_map.get(difficulty, 1))
