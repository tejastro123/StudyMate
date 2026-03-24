"""tests/conftest.py
=================
Shared pytest fixtures for all test modules.

Design:
- In-memory SQLite, same schema as database/db.py via _DDL_STATEMENTS
- _NonClosingProxy: repositories call conn.close(); this makes it a no-op
  so the shared in-memory connection stays alive across the test
- log_activity is mocked globally to avoid touching the real DB
"""
import sqlite3
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import _DDL_STATEMENTS


# ── Non-closing connection proxy ─────────────────────────────────────────────

class _NonClosingProxy:
    """sqlite3.Connection wrapper that makes .close() a no-op in tests."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def close(self) -> None:
        pass  # intentional no-op

    def __getattr__(self, name):
        return getattr(self._conn, name)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_log_activity(mocker):
    """Prevent log_activity from opening the real DB during tests."""
    mocker.patch("database.db.log_activity", return_value=None)


@pytest.fixture
def mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    for stmt in _DDL_STATEMENTS:
        conn.execute(stmt)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def conn_factory(mem_conn):
    def _factory():
        proxy = _NonClosingProxy(mem_conn)
        proxy.row_factory = sqlite3.Row  # type: ignore[attr-defined]
        return proxy
    return _factory


# ── Repositories ─────────────────────────────────────────────────────────────

@pytest.fixture
def deck_repo(conn_factory):
    from repository.deck_repo import DeckRepository
    return DeckRepository(conn_factory)


@pytest.fixture
def card_repo(conn_factory):
    from repository.flashcard_repo import FlashcardRepository
    return FlashcardRepository(conn_factory)


@pytest.fixture
def quiz_repo(conn_factory):
    from repository.quiz_repo import QuizRepository
    return QuizRepository(conn_factory)


@pytest.fixture
def timetable_repo(conn_factory):
    from repository.timetable_repo import TimetableRepository
    return TimetableRepository(conn_factory)


@pytest.fixture
def focus_repo(conn_factory):
    from repository.focus_repo import FocusRepository
    return FocusRepository(conn_factory)


@pytest.fixture
def chat_repo(conn_factory):
    from repository.chat_repo import ChatRepository
    return ChatRepository(conn_factory)


# ── Services ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fc_service(deck_repo, card_repo):
    from services.flashcard_service import FlashcardService
    return FlashcardService(deck_repo, card_repo)


@pytest.fixture
def quiz_service(quiz_repo):
    from services.quiz_service import QuizService
    return QuizService(quiz_repo)


@pytest.fixture
def timetable_service(timetable_repo):
    from services.timetable_service import TimetableService
    return TimetableService(timetable_repo)


@pytest.fixture
def focus_service(focus_repo):
    from services.focus_service import FocusService
    return FocusService(focus_repo)


@pytest.fixture
def ai_service(chat_repo):
    from services.ai_service import AIService
    return AIService(chat_repo)
