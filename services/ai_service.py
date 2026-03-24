"""
services/ai_service.py
=======================
Business logic for the AI Study Assistant.

Owns:
- Session / message lifecycle (via ChatRepository)
- Claude API call with system prompt
- Markdown → HTML conversion
- Clipboard-based "Summarize notes" helper
"""
from __future__ import annotations
import logging
import re

from repository.chat_repo import ChatRepository
from models.chat import ChatSession, ChatMessage
from database.db import log_activity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are StudyMate AI, a helpful academic assistant for students. "
    "You explain concepts clearly, create practice questions on demand, "
    "summarize notes, and provide study tips. Always be encouraging and concise."
)


class AIService:

    def __init__(self, repo: ChatRepository) -> None:
        self._repo = repo

    # ── Sessions ─────────────────────────────────────────────────────────────

    def get_all_sessions(self) -> list[ChatSession]:
        return self._repo.get_all_sessions()

    def create_session(self, title: str = "New Chat") -> ChatSession:
        session = self._repo.create_session(title)
        log_activity(f"Started AI chat: {title}", "AI Assistant")
        return session

    def delete_session(self, session_id: int) -> None:
        self._repo.delete_session(session_id)

    # ── Messages ─────────────────────────────────────────────────────────────

    def get_messages(self, session_id: int) -> list[ChatMessage]:
        return self._repo.get_messages(session_id)

    # ── Claude API ───────────────────────────────────────────────────────────

    def send(
        self,
        api_key: str,
        session_id: int,
        user_text: str,
        history: list[ChatMessage],
    ) -> str:
        """
        Send a message to Claude and return the assistant reply.

        Both messages are persisted to DB before returning.

        Raises anthropic.APIError on network / auth failures.
        """
        import anthropic

        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": user_text})

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text

        # Persist both turns
        self._repo.save_message(session_id, "user", user_text)
        self._repo.save_message(session_id, "assistant", reply)

        return reply

    # ── Formatting ───────────────────────────────────────────────────────────

    @staticmethod
    def markdown_to_html(text: str) -> str:
        """
        Lightweight Markdown → HTML for QLabel RichText display.
        Handles: headers, **bold**, *italic*, `code`, newlines.
        """
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        text = re.sub(
            r"`(.+?)`",
            r'<code style="background:#35355A;padding:1px 4px;border-radius:4px;">\1</code>',
            text,
        )
        text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
        text = text.replace("\n", "<br>")
        return text

    # ── Document Parsing & Generation ──────────────────────────────────────────

    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract all raw text from a local PDF file using PyMuPDF."""
        import fitz  # PyMuPDF
        text_blocks = []
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text_blocks.append(page.get_text())
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_path}: {e}")
            raise ValueError(f"Could not read PDF file: {e}")
        return "\n".join(text_blocks)

    def generate_deck_from_text(self, api_key: str, text: str, max_cards: int = 15) -> list[dict[str, str]]:
        """
        Send document text to Claude and ask it to generate a Quiz/Flashcard deck.
        Returns a list of dictionaries with 'front' and 'back' keys.
        """
        import anthropic
        import json

        gen_prompt = (
            f"You are an expert tutor. Please read the provided document fragment and extract up to {max_cards} "
            "key-value flashcards that cover the most important concepts.\n"
            "You MUST reply with ONLY a raw, valid JSON array of objects. Do not include markdown code blocks (like ```json), "
            "do not include introductory or concluding text, just the raw JSON array. "
            "Each object must have exactly two string keys: 'front' and 'back'.\n"
            "Example: [{\"front\": \"What is mitochondria?\", \"back\": \"Powerhouse of the cell\"}]"
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            system=gen_prompt,
            messages=[{"role": "user", "content": f"Document text:\n\n{text[:40000]}"}], # truncate if too huge
        )

        reply = response.content[0].text.strip()
        
        # Strip potential markdown formatting if Claude disobeys
        if reply.startswith("```json"):
            reply = reply[7:]
        if reply.startswith("```"):
            reply = reply[3:]
        if reply.endswith("```"):
            reply = reply[:-3]
            
        try:
            cards = json.loads(reply.strip())
            if not isinstance(cards, list):
                raise ValueError("Claude didn't return a JSON array.")
            return cards
        except Exception as e:
            logger.error(f"Failed to parse Claude deck response: {e}\nResponse was:\n{reply}")
            raise ValueError("AI failed to format the flashcards correctly. Please try again.")
