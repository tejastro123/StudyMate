"""tests/test_flashcard_repo.py — FlashcardRepository integration tests."""
from datetime import date, timedelta
from models.flashcard import Flashcard


class TestFlashcardRepository:
    def _make_deck(self, deck_repo, name="Test Deck"):
        return deck_repo.create(name)

    def test_create_and_get_for_deck(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card = card_repo.create(deck.id, "What is H2O?", "Water")
        assert card.id > 0
        cards = card_repo.get_for_deck(deck.id)
        assert len(cards) == 1
        assert cards[0].front == "What is H2O?"

    def test_get_due_returns_new_cards(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card_repo.create(deck.id, "Q1", "A1")   # no due_date → always due
        due = card_repo.get_due(deck.id)
        assert len(due) == 1

    def test_get_due_excludes_future_cards(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card = card_repo.create(deck.id, "Q1", "A1")
        future_date = (date.today() + timedelta(days=7)).isoformat()
        card_repo.update_review(card.id, "easy", 2.6, 7, future_date)
        due = card_repo.get_due(deck.id)
        assert len(due) == 0

    def test_update_card(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card = card_repo.create(deck.id, "Old Q", "Old A")
        card_repo.update(card.id, "New Q", "New A")
        updated = card_repo.get_by_id(card.id)
        assert updated.front == "New Q"
        assert updated.back == "New A"

    def test_delete_card(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card = card_repo.create(deck.id, "Q", "A")
        card_repo.delete(card.id)
        assert card_repo.get_by_id(card.id) is None

    def test_update_review(self, deck_repo, card_repo):
        deck = self._make_deck(deck_repo)
        card = card_repo.create(deck.id, "Q", "A")
        new_due = (date.today() + timedelta(days=3)).isoformat()
        card_repo.update_review(card.id, "easy", 2.7, 3, new_due)
        updated = card_repo.get_by_id(card.id)
        assert updated.difficulty == "easy"
        assert updated.ease_factor == 2.7
        assert updated.interval_days == 3
        assert updated.review_count == 1
