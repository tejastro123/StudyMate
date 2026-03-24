"""
modules/ai_assistant.py  (Phase 2 shim)
=========================================
Backward-compatible shim over AIService + ChatRepository.
"""
from __future__ import annotations
from database.db import get_connection
from repository.chat_repo import ChatRepository
from services.ai_service import AIService

_svc = AIService(ChatRepository(get_connection))


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(title: str = "New Chat") -> int:
    return _svc.create_session(title).id

def get_all_sessions() -> list[dict]:
    return [s.__dict__ for s in _svc.get_all_sessions()]

def delete_session(session_id: int) -> None:
    _svc.delete_session(session_id)


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(session_id: int, role: str, content: str) -> int:
    msg = _svc._repo.save_message(session_id, role, content)
    return msg.id

def get_messages(session_id: int) -> list[dict]:
    return [m.__dict__ for m in _svc.get_messages(session_id)]


# ── API ───────────────────────────────────────────────────────────────────────

def send_message(
    api_key: str,
    session_id: int,
    user_text: str,
    conversation_history: list[dict],
) -> str:
    from models.chat import ChatMessage
    history = [
        ChatMessage(id=0, session_id=session_id, role=m["role"], content=m["content"])
        for m in conversation_history
    ]
    return _svc.send(api_key, session_id, user_text, history)

def markdown_to_html(text: str) -> str:
    return AIService.markdown_to_html(text)
