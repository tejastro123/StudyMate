"""repository/quiz_repo.py — Quiz and Question persistence."""
from __future__ import annotations
from .base import BaseRepository
from models.quiz import Quiz
from models.question import Question


class QuizRepository(BaseRepository[Quiz]):

    # ── Quizzes ─────────────────────────────────────────────────────────────

    def get_all(self) -> list[Quiz]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT q.id, q.title, q.subject, q.created_at, q.remote_id,
                   COUNT(qu.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """
        ).fetchall()
        conn.close()
        return [self._row_to_quiz(r) for r in rows]

    def get_by_id(self, quiz_id: int) -> Quiz | None:
        conn = self._conn()
        row = conn.execute(
            """
            SELECT q.id, q.title, q.subject, q.created_at, q.remote_id,
                   COUNT(qu.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            WHERE q.id = ?
            GROUP BY q.id
            """,
            (quiz_id,),
        ).fetchone()
        conn.close()
        return self._row_to_quiz(row) if row else None

    def create(self, title: str, subject: str = "") -> Quiz:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO quizzes (title, subject, is_dirty) VALUES (?, ?, 1)", (title, subject)
        )
        quiz_id = cur.lastrowid
        conn.commit()
        conn.close()
        return Quiz(id=quiz_id, title=title, subject=subject, is_dirty=1)

    def delete(self, quiz_id: int) -> None:
        """Delete quiz, its questions, and all attempt records."""
        conn = self._conn()
        conn.execute("DELETE FROM quiz_attempts WHERE quiz_id = ?", (quiz_id,))
        conn.execute("DELETE FROM questions WHERE quiz_id = ?", (quiz_id,))
        conn.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
        conn.commit()
        conn.close()

    def record_attempt(
        self, quiz_id: int, score: int, total: int, time_seconds: int
    ) -> None:
        pct = round(100 * score / total) if total else 0
        conn = self._conn()
        conn.execute(
            "INSERT INTO quiz_attempts (quiz_id, score, total, pct, time_seconds) VALUES (?, ?, ?, ?, ?)",
            (quiz_id, score, total, pct, time_seconds),
        )
        conn.commit()
        conn.close()

    def get_attempts_for_chart(self) -> list[dict]:
        """Return recent attempts with quiz title for chart rendering."""
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT q.title, a.score, a.total, a.pct, a.attempted_at
            FROM quiz_attempts a
            JOIN quizzes q ON q.id = a.quiz_id
            ORDER BY a.attempted_at DESC
            LIMIT 30
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── Questions ────────────────────────────────────────────────────────────

    def get_questions(self, quiz_id: int) -> list[Question]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM questions WHERE quiz_id = ? ORDER BY created_at",
            (quiz_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_question(r) for r in rows]

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
        conn = self._conn()
        cur = conn.execute(
            """
            INSERT INTO questions
                (quiz_id, question_text, q_type, correct_answer,
                 option_a, option_b, option_c, option_d, explanation, is_dirty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (quiz_id, question_text, q_type, correct_answer,
             option_a, option_b, option_c, option_d, explanation),
        )
        q_id = cur.lastrowid
        conn.commit()
        conn.close()
        return Question(
            id=q_id, quiz_id=quiz_id, question_text=question_text,
            q_type=q_type, correct_answer=correct_answer,
            option_a=option_a, option_b=option_b,
            option_c=option_c, option_d=option_d,
            explanation=explanation, is_dirty=1
        )

    def delete_question(self, question_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        conn.close()

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_quiz(row) -> Quiz:
        return Quiz(
            id=row["id"],
            title=row["title"],
            subject=row["subject"] or "",
            created_at=row["created_at"] or "",
            remote_id=row["remote_id"] or "",
            question_count=row["question_count"] or 0,
        )

    @staticmethod
    def _row_to_question(row) -> Question:
        return Question(
            id=row["id"],
            quiz_id=row["quiz_id"],
            question_text=row["question_text"],
            q_type=row["q_type"],
            correct_answer=row["correct_answer"],
            option_a=row["option_a"] or "",
            option_b=row["option_b"] or "",
            option_c=row["option_c"] or "",
            option_d=row["option_d"] or "",
            explanation=row["explanation"] or "",
            created_at=row["created_at"] or "",
            remote_id=row["remote_id"] or "",
        )
