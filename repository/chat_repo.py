"""repository/chat_repo.py — Chat session and message persistence."""
from __future__ import annotations
from .base import BaseRepository
from models.chat import ChatSession, ChatMessage


class ChatRepository(BaseRepository[ChatSession]):

    # ── Sessions ─────────────────────────────────────────────────────────────

    def get_all_sessions(self) -> list[ChatSession]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM chat_sessions ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [self._row_to_session(r) for r in rows]

    def create_session(self, title: str = "New Chat") -> ChatSession:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO chat_sessions (title, is_dirty) VALUES (?, 1)", (title,)
        )
        s_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ChatSession(id=s_id, title=title, is_dirty=1)

    def delete_session(self, session_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def _row_to_session(row) -> ChatSession:
        return ChatSession(
            id=row["id"],
            title=row["title"] or "New Chat",
            created_at=row["created_at"] or "",
            remote_id=row["remote_id"] or "",
            is_dirty=row["is_dirty"],
            updated_at=row["updated_at"] or "",
        )

    @staticmethod
    def _row_to_message(row) -> ChatMessage:
        return ChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            timestamp=row["timestamp"] or "",
            remote_id=row["remote_id"] or "",
            is_dirty=row["is_dirty"],
            updated_at=row["updated_at"] or "",
        )

    # ── Messages ─────────────────────────────────────────────────────────────

    def get_messages(self, session_id: int) -> list[ChatMessage]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        conn.close()
        return [self._row_to_message(r) for r in rows]

    def save_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, is_dirty) VALUES (?, ?, ?, 1)",
            (session_id, role, content),
        )
        m_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ChatMessage(id=m_id, session_id=session_id, role=role, content=content, is_dirty=1)
