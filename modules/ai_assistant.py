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
    provider: str = "anthropic",
    local_model: str = "llama3"
) -> str:
    from models.chat import ChatMessage
    history = [
        ChatMessage(id=0, session_id=session_id, role=m["role"], content=m["content"])
        for m in conversation_history
    ]
    return _svc.send(api_key, session_id, user_text, history, provider=provider, local_model=local_model)

def markdown_to_html(text: str) -> str:
    return AIService.markdown_to_html(text)

def extract_text_from_pdf(pdf_path: str) -> str:
    return AIService.extract_text_from_pdf(pdf_path)

def generate_deck_from_text(api_key: str, text: str, max_cards: int = 15, provider: str = "anthropic", local_model: str = "llama3") -> list[dict[str, str]]:
    return _svc.generate_deck_from_text(api_key, text, max_cards, provider=provider, local_model=local_model)
