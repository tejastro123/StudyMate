"""models/chat.py — Chat Session and Message domain models."""
from __future__ import annotations
from dataclasses import dataclass, field

VALID_ROLES = frozenset({"user", "assistant"})


@dataclass
class ChatSession:
    """A named conversation thread with the AI assistant."""
    id: int
    title: str = "New Chat"
    created_at: str = ""
    remote_id: str = ""


@dataclass
class ChatMessage:
    """A single message in a chat session."""
    id: int
    session_id: int
    role: str           # 'user' | 'assistant'
    content: str
    timestamp: str = ""
    remote_id: str = ""

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(f"role must be 'user' or 'assistant', got {self.role!r}")
        if not self.content.strip():
            raise ValueError("Message content cannot be empty.")

    @property
    def is_user(self) -> bool:
        return self.role == "user"
