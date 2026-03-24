"""repository/flashcard_repo.py — Flashcard persistence."""
from __future__ import annotations
from datetime import date
from .base import BaseRepository
from models.flashcard import Flashcard


class FlashcardRepository(BaseRepository[Flashcard]):

    # ── Read ────────────────────────────────────────────────────────────────

    def get_for_deck(self, deck_id: int) -> list[Flashcard]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE deck_id = ? ORDER BY created_at",
            (deck_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_card(r) for r in rows]

    def get_due(self, deck_id: int) -> list[Flashcard]:
        """Return cards due today or overdue, ordered by due_date ASC."""
        today = date.today().isoformat()
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT * FROM flashcards
            WHERE deck_id = ?
              AND (due_date IS NULL OR due_date <= ?)
            ORDER BY due_date ASC NULLS FIRST
            """,
            (deck_id, today),
        ).fetchall()
        conn.close()
        return [self._row_to_card(r) for r in rows]

    def get_by_id(self, card_id: int) -> Flashcard | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM flashcards WHERE id = ?", (card_id,)
        ).fetchone()
        conn.close()
        return self._row_to_card(row) if row else None

    # ── Write ───────────────────────────────────────────────────────────────

    def create(self, deck_id: int, front: str, back: str) -> Flashcard:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO flashcards (deck_id, front, back, is_dirty) VALUES (?, ?, ?, 1)",
            (deck_id, front, back),
        )
        card_id = cur.lastrowid
        conn.commit()
        conn.close()
        return Flashcard(id=card_id, deck_id=deck_id, front=front, back=back, is_dirty=1)

    def update(self, card_id: int, front: str, back: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE flashcards SET front = ?, back = ?, is_dirty = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (front, back, card_id),
        )
        conn.commit()
        conn.close()

    def update_review(
        self,
        card_id: int,
        difficulty: str,
        ease_factor: float,
        interval_days: int,
        due_date: str,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """
            UPDATE flashcards
            SET difficulty = ?, ease_factor = ?, interval_days = ?,
                due_date = ?, review_count = review_count + 1,
                is_dirty = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (difficulty, ease_factor, interval_days, due_date, card_id),
        )
        conn.commit()
        conn.close()

    def delete(self, card_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
        conn.commit()
        conn.close()

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_card(row) -> Flashcard:
        return Flashcard(
            id=row["id"],
            deck_id=row["deck_id"],
            front=row["front"],
            back=row["back"],
            difficulty=row["difficulty"] or "new",
            ease_factor=float(row["ease_factor"] or 2.5),
            interval_days=int(row["interval_days"] or 1),
            due_date=row["due_date"] or "",
            created_at=row["created_at"] or "",
            review_count=int(row["review_count"] or 0),
            remote_id=row["remote_id"] or "",
        )
