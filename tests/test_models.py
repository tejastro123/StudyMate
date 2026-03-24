"""tests/test_models.py — Domain model unit tests."""
import pytest
from models.deck import Deck
from models.flashcard import Flashcard
from models.quiz import Quiz
from models.question import Question
from models.timetable_event import TimetableEvent
from models.focus_session import FocusSession, DailyFocusStat
from models.chat import ChatSession, ChatMessage


# ── Deck ─────────────────────────────────────────────────────────────────────

class TestDeck:
    def test_valid_deck(self):
        d = Deck(id=1, name="Biology", subject="Science")
        assert d.name == "Biology"
        assert d.is_empty is True   # no cards
        assert d.mastery_pct == 0.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            Deck(id=1, name="   ")

    def test_mastery_pct(self):
        d = Deck(id=1, name="Bio", total_cards=10, mastered=5)
        assert d.mastery_pct == 50.0


# ── Flashcard ─────────────────────────────────────────────────────────────────

class TestFlashcard:
    def test_valid_flashcard(self):
        c = Flashcard(id=1, deck_id=1, front="Q", back="A")
        assert c.is_due is True      # no due_date → always due
        assert not c.is_mastered

    def test_invalid_difficulty_raises(self):
        with pytest.raises(ValueError):
            Flashcard(id=1, deck_id=1, front="Q", back="A", difficulty="impossible")

    def test_empty_front_raises(self):
        with pytest.raises(ValueError):
            Flashcard(id=1, deck_id=1, front="", back="A")

    def test_not_due(self):
        from datetime import date, timedelta
        future = (date.today() + timedelta(days=5)).isoformat()
        c = Flashcard(id=1, deck_id=1, front="Q", back="A", due_date=future)
        assert not c.is_due


# ── Question ─────────────────────────────────────────────────────────────────

class TestQuestion:
    def test_check_answer_case_insensitive(self):
        q = Question(id=1, quiz_id=1, question_text="Q?",
                     q_type="short", correct_answer="Paris")
        assert q.check_answer("paris")
        assert q.check_answer("PARIS")
        assert not q.check_answer("London")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            Question(id=1, quiz_id=1, question_text="Q?",
                     q_type="essay", correct_answer="A")

    def test_mcq_options(self):
        q = Question(id=1, quiz_id=1, question_text="Q?",
                     q_type="mcq", correct_answer="A",
                     option_a="A", option_b="B", option_c="", option_d="")
        assert q.mcq_options == ["A", "B"]


# ── TimetableEvent ────────────────────────────────────────────────────────────

class TestTimetableEvent:
    def test_duration(self):
        ev = TimetableEvent(
            id=1, title="Physics", subject="Physics",
            event_type="class", day_of_week=0,
            start_time="09:00", end_time="10:30",
        )
        assert ev.duration_minutes == 90
        assert ev.day_name == "Monday"

    def test_invalid_time_order_raises(self):
        with pytest.raises(ValueError):
            TimetableEvent(
                id=1, title="X", subject="X",
                event_type="class", day_of_week=0,
                start_time="10:00", end_time="09:00",
            )

    def test_invalid_day_raises(self):
        with pytest.raises(ValueError):
            TimetableEvent(
                id=1, title="X", subject="X",
                event_type="class", day_of_week=8,  # invalid
                start_time="09:00", end_time="10:00",
            )


# ── FocusSession ──────────────────────────────────────────────────────────────

class TestFocusSession:
    def test_valid(self):
        s = FocusSession(id=1, subject="Math", duration_minutes=25, session_type="pomodoro")
        assert s.duration_hours == pytest.approx(25 / 60, abs=0.01)

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError):
            FocusSession(id=1, subject="Math", duration_minutes=0, session_type="pomodoro")

    def test_daily_stat(self):
        stat = DailyFocusStat(date="2025-01-01", total_minutes=90)
        assert stat.total_hours == 1.5


# ── ChatMessage ───────────────────────────────────────────────────────────────

class TestChatMessage:
    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            ChatMessage(id=1, session_id=1, role="bot", content="Hi")

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            ChatMessage(id=1, session_id=1, role="user", content="   ")

    def test_is_user(self):
        m = ChatMessage(id=1, session_id=1, role="user", content="Hi")
        assert m.is_user
        m2 = ChatMessage(id=2, session_id=1, role="assistant", content="Hello")
        assert not m2.is_user
