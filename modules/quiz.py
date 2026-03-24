"""
modules/quiz.py  (Phase 2 shim)
================================
Backward-compatible shim over QuizService + QuizRepository.
"""
from __future__ import annotations
from database.db import get_connection
from repository.quiz_repo import QuizRepository
from services.quiz_service import QuizService

_repo = QuizRepository(get_connection)
_svc = QuizService(_repo)


# ── Quizzes ──────────────────────────────────────────────────────────────────

def get_all_quizzes() -> list[dict]:
    return [q.__dict__ for q in _svc.get_all()]

def create_quiz(title: str, subject: str = "") -> int:
    return _svc.create(title, subject).id

def delete_quiz(quiz_id: int) -> None:
    _svc.delete(quiz_id)


# ── Questions ─────────────────────────────────────────────────────────────────

def get_questions(quiz_id: int) -> list[dict]:
    return [q.__dict__ for q in _svc.get_questions(quiz_id)]

def add_question(
    quiz_id: int,
    question_text: str,
    q_type: str,
    correct_answer: str,
    option_a: str = "",
    option_b: str = "",
    option_c: str = "",
    option_d: str = "",
    explanation: str = "",
) -> int:
    return _svc.add_question(
        quiz_id, question_text, q_type, correct_answer,
        option_a, option_b, option_c, option_d, explanation,
    ).id

def delete_question(question_id: int) -> None:
    _svc.delete_question(question_id)


# ── Attempts ──────────────────────────────────────────────────────────────────

def record_attempt(quiz_id: int, score: int, total: int, time_taken: int) -> None:
    _svc.record_attempt(quiz_id, score, total, time_taken)

def get_all_attempts_for_chart() -> list[dict]:
    return _svc.get_attempts_for_chart()


# ── CSV / AI ──────────────────────────────────────────────────────────────────

def import_from_csv(quiz_id: int, file_path: str) -> tuple[int, list[str]]:
    return _svc.import_from_csv(quiz_id, file_path)

def generate_questions_with_ai(
    api_key: str, topic: str, count: int = 5, q_type: str = "mcq"
) -> list[dict]:
    return _svc.generate_with_ai(api_key, topic, count, q_type)
