"""tests/test_flashcard_service.py — FlashcardService (spaced repetition) tests."""
import pytest
from datetime import date, timedelta


class TestFlashcardService:
    def test_create_deck(self, fc_service):
        deck = fc_service.create_deck("Chemistry")
        assert deck.name == "Chemistry"
        assert deck.id > 0

    def test_rename_deck(self, fc_service):
        deck = fc_service.create_deck("Old")
        fc_service.rename_deck(deck.id, "New")
        decks = fc_service.get_all_decks()
        assert any(d.name == "New" for d in decks)

    def test_add_and_get_card(self, fc_service):
        deck = fc_service.create_deck("Physics")
        card = fc_service.add_card(deck.id, "What is F=ma?", "Newton's 2nd law")
        cards = fc_service.get_cards(deck.id)
        assert len(cards) == 1
        assert cards[0].id == card.id

    def test_review_easy_increases_interval(self, fc_service, card_repo, deck_repo):
        deck = fc_service.create_deck("Bio")
        card = fc_service.add_card(deck.id, "Q", "A")

        fc_service.record_review(card.id, "easy")
        updated = card_repo.get_by_id(card.id)

        assert updated.difficulty == "easy"
        assert updated.ease_factor > 2.5   # increased
        assert updated.interval_days >= 1
        # Due date should be in the future
        assert updated.due_date > date.today().isoformat()

    def test_review_hard_resets_interval(self, fc_service, card_repo, deck_repo):
        deck = fc_service.create_deck("Math")
        card = fc_service.add_card(deck.id, "Q", "A")

        fc_service.record_review(card.id, "hard")
        updated = card_repo.get_by_id(card.id)

        assert updated.difficulty == "hard"
        assert updated.interval_days == 1   # reset to tomorrow

    def test_review_medium_reduces_ease_factor(self, fc_service, card_repo, deck_repo):
        deck = fc_service.create_deck("History")
        card = fc_service.add_card(deck.id, "Q", "A")

        original_ef = 2.5
        fc_service.record_review(card.id, "medium")
        updated = card_repo.get_by_id(card.id)

        assert updated.ease_factor < original_ef + 0.01  # not increased

    def test_review_invalid_card_raises(self, fc_service):
        with pytest.raises(ValueError):
            fc_service.record_review(99999, "easy")

    def test_delete_card(self, fc_service, card_repo, deck_repo):
        deck = fc_service.create_deck("Temp")
        card = fc_service.add_card(deck.id, "Q", "A")
        fc_service.delete_card(card.id)
        assert card_repo.get_by_id(card.id) is None
