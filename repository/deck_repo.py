"""repository/deck_repo.py — Deck persistence."""
from __future__ import annotations
from .base import BaseRepository
from models.deck import Deck


class DeckRepository(BaseRepository[Deck]):
    """All database operations that touch the ``decks`` table."""

    # ── Read ────────────────────────────────────────────────────────────────

    def get_all(self) -> list[Deck]:
        """Return all decks with computed stats (total, due_today, mastered)."""
        conn = self._conn()
        today = __import__("datetime").date.today().isoformat()
        rows = conn.execute(
            """
            SELECT
                d.id, d.name, d.subject, d.created_at,
                COUNT(f.id)                                          AS total_cards,
                SUM(CASE WHEN f.due_date <= ? THEN 1 ELSE 0 END)    AS due_today,
                SUM(CASE WHEN f.ease_factor >= 2.5
                          AND f.difficulty = 'easy' THEN 1 ELSE 0 END) AS mastered
            FROM decks d
            LEFT JOIN flashcards f ON f.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """,
            (today,),
        ).fetchall()
        conn.close()
        return [self._row_to_deck(r) for r in rows]

    def get_by_id(self, deck_id: int) -> Deck | None:
        conn = self._conn()
        today = __import__("datetime").date.today().isoformat()
        row = conn.execute(
            """
            SELECT
                d.id, d.name, d.subject, d.created_at,
                COUNT(f.id)                                          AS total_cards,
                SUM(CASE WHEN f.due_date <= ? THEN 1 ELSE 0 END)    AS due_today,
                SUM(CASE WHEN f.ease_factor >= 2.5
                          AND f.difficulty = 'easy' THEN 1 ELSE 0 END) AS mastered
            FROM decks d
            LEFT JOIN flashcards f ON f.deck_id = d.id
            WHERE d.id = ?
            GROUP BY d.id
            """,
            (today, deck_id),
        ).fetchone()
        conn.close()
        return self._row_to_deck(row) if row else None

    # ── Write ───────────────────────────────────────────────────────────────

    def create(self, name: str, subject: str = "") -> Deck:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO decks (name, subject) VALUES (?, ?)", (name, subject)
        )
        deck_id = cur.lastrowid
        conn.commit()
        conn.close()
        return Deck(id=deck_id, name=name, subject=subject)

    def rename(self, deck_id: int, new_name: str) -> None:
        if not new_name.strip():
            raise ValueError("Deck name cannot be empty.")
        conn = self._conn()
        conn.execute("UPDATE decks SET name = ? WHERE id = ?", (new_name, deck_id))
        conn.commit()
        conn.close()

    def delete(self, deck_id: int) -> None:
        """Delete deck and all its flashcards (CASCADE)."""
        conn = self._conn()
        conn.execute("DELETE FROM flashcards WHERE deck_id = ?", (deck_id,))
        conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        conn.commit()
        conn.close()

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_deck(row) -> Deck:
        return Deck(
            id=row["id"],
            name=row["name"],
            subject=row["subject"] or "",
            created_at=row["created_at"] or "",
            total_cards=row["total_cards"] or 0,
            due_today=row["due_today"] or 0,
            mastered=row["mastered"] or 0,
        )
