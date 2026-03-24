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
        return [ChatSession(id=r["id"], title=r["title"] or "Chat", created_at=r["created_at"] or "") for r in rows]

    def create_session(self, title: str = "New Chat") -> ChatSession:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO chat_sessions (title) VALUES (?)", (title,)
        )
        session_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ChatSession(id=session_id, title=title)

    def delete_session(self, session_id: int) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

    # ── Messages ─────────────────────────────────────────────────────────────

    def get_messages(self, session_id: int) -> list[ChatMessage]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        conn.close()
        return [
            ChatMessage(
                id=r["id"], session_id=r["session_id"],
                role=r["role"], content=r["content"],
                timestamp=r["timestamp"] or "",
            )
            for r in rows
        ]

    def save_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ChatMessage(id=msg_id, session_id=session_id, role=role, content=content)
