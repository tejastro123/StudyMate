"""
services/quiz_service.py
========================
Business logic for quizzes.

Owns:
- Quiz / question CRUD
- CSV import with validation
- AI question generation
- Score calculation helpers
"""
from __future__ import annotations
import csv
import io
import logging

from repository.quiz_repo import QuizRepository
from models.quiz import Quiz
from models.question import Question
from database.db import log_activity

logger = logging.getLogger(__name__)

_CSV_REQUIRED = {"question", "correct_answer"}


class QuizService:
    """Orchestrates quiz and question operations."""

    def __init__(self, repo: QuizRepository) -> None:
        self._repo = repo

    # ── Quizzes ──────────────────────────────────────────────────────────────

    def get_all(self) -> list[Quiz]:
        return self._repo.get_all()

    def create(self, title: str, subject: str = "") -> Quiz:
        quiz = self._repo.create(title, subject)
        log_activity(f"Created quiz '{title}'", "Quiz")
        return quiz

    def delete(self, quiz_id: int) -> None:
        self._repo.delete(quiz_id)
        log_activity(f"Deleted quiz #{quiz_id}", "Quiz")

    def record_attempt(self, quiz_id: int, score: int, total: int, time_seconds: int) -> None:
        self._repo.record_attempt(quiz_id, score, total, time_seconds)
        pct = round(100 * score / total) if total else 0
        log_activity(f"Quiz #{quiz_id}: scored {score}/{total} ({pct}%)", "Quiz")

    def get_attempts_for_chart(self) -> list[dict]:
        return self._repo.get_attempts_for_chart()

    # ── Questions ────────────────────────────────────────────────────────────

    def get_questions(self, quiz_id: int) -> list[Question]:
        return self._repo.get_questions(quiz_id)

    def add_question(
        self,
        quiz_id: int,
        question_text: str,
        q_type: str,
        correct_answer: str,
        option_a: str = "",
        option_b: str = "",
        option_c: str = "",
        option_d: str = "",
        explanation: str = "",
    ) -> Question:
        return self._repo.add_question(
            quiz_id, question_text, q_type, correct_answer,
            option_a, option_b, option_c, option_d, explanation,
        )

    def delete_question(self, question_id: int) -> None:
        self._repo.delete_question(question_id)

    # ── CSV Import ───────────────────────────────────────────────────────────

    def import_from_csv(self, quiz_id: int, filepath: str) -> tuple[int, list[str]]:
        """
        Import questions from a CSV file.

        Expected columns (case-insensitive):
            question, q_type, correct_answer, option_a, option_b,
            option_c, option_d, explanation

        Returns (count_imported, list_of_error_messages).
        """
        imported = 0
        errors: list[str] = []
        try:
            with open(filepath, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                headers = {h.strip().lower() for h in (reader.fieldnames or [])}
                if not _CSV_REQUIRED.issubset(headers):
                    missing = _CSV_REQUIRED - headers
                    return 0, [f"Missing required columns: {missing}"]

                for i, row in enumerate(reader, start=2):
                    try:
                        self._repo.add_question(
                            quiz_id=quiz_id,
                            question_text=row.get("question", "").strip(),
                            q_type=row.get("q_type", "short").strip().lower() or "short",
                            correct_answer=row.get("correct_answer", "").strip(),
                            option_a=row.get("option_a", "").strip(),
                            option_b=row.get("option_b", "").strip(),
                            option_c=row.get("option_c", "").strip(),
                            option_d=row.get("option_d", "").strip(),
                            explanation=row.get("explanation", "").strip(),
                        )
                        imported += 1
                    except Exception as exc:
                        errors.append(f"Row {i}: {exc}")
        except OSError as exc:
            errors.append(f"Could not open file: {exc}")
        log_activity(f"CSV import: {imported} questions into quiz #{quiz_id}", "Quiz")
        return imported, errors

    # ── AI Generation ────────────────────────────────────────────────────────

    def generate_with_ai(
        self,
        api_key: str,
        topic: str,
        count: int,
        q_type: str,
    ) -> list[dict]:
        """
        Ask Claude to generate questions.  Returns raw dicts so the caller
        can review before saving.  Does NOT persist to DB.

        Raises anthropic.APIError on failure.
        """
        import anthropic, json, re

        type_instructions = {
            "mcq": "Generate MCQ questions with 4 options (A, B, C, D) and a correct_answer matching one option exactly.",
            "truefalse": "Generate True/False questions where correct_answer is exactly 'True' or 'False'.",
            "short": "Generate short-answer questions with a concise correct_answer.",
        }

        prompt = (
            f"Generate {count} {type_instructions.get(q_type, '')} questions about: {topic}.\n\n"
            "Return ONLY a valid JSON array. Each element must have:\n"
            '{"question": "...", "correct_answer": "...", "option_a": "", "option_b": "", '
            '"option_c": "", "option_d": "", "explanation": "..."}\n'
            "For non-MCQ types, leave option_a through option_d as empty strings."
        )

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        # Extract JSON array even if wrapped in markdown code fences
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise ValueError("AI returned no valid JSON array.")
        questions: list[dict] = json.loads(match.group())
        logger.info("AI generated %d questions for topic '%s'", len(questions), topic)
        return questions
