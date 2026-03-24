"""tests/test_deck_repo.py — DeckRepository integration tests."""
import pytest
from models.deck import Deck


class TestDeckRepository:
    def test_create_and_get_all(self, deck_repo):
        deck = deck_repo.create("Biology", "Science")
        assert isinstance(deck, Deck)
        assert deck.id > 0
        assert deck.name == "Biology"

        all_decks = deck_repo.get_all()
        assert len(all_decks) == 1
        assert all_decks[0].name == "Biology"

    def test_get_by_id(self, deck_repo):
        deck = deck_repo.create("Physics")
        found = deck_repo.get_by_id(deck.id)
        assert found is not None
        assert found.name == "Physics"

    def test_get_by_id_missing_returns_none(self, deck_repo):
        assert deck_repo.get_by_id(9999) is None

    def test_rename(self, deck_repo):
        deck = deck_repo.create("Old Name")
        deck_repo.rename(deck.id, "New Name")
        found = deck_repo.get_by_id(deck.id)
        assert found.name == "New Name"

    def test_rename_empty_raises(self, deck_repo):
        deck = deck_repo.create("Test")
        with pytest.raises(ValueError):
            deck_repo.rename(deck.id, "  ")

    def test_delete(self, deck_repo):
        deck = deck_repo.create("Temp")
        deck_repo.delete(deck.id)
        assert deck_repo.get_by_id(deck.id) is None

    def test_stats_with_no_cards(self, deck_repo):
        deck = deck_repo.create("Empty")
        all_decks = deck_repo.get_all()
        d = next(x for x in all_decks if x.id == deck.id)
        assert d.total_cards == 0
        assert d.due_today == 0
        assert d.mastered == 0
