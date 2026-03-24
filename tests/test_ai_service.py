"""tests/test_ai_service.py — AIService tests (API mocked)."""
import pytest
from models.chat import ChatMessage


class TestAIService:
    def test_create_session(self, ai_service):
        session = ai_service.create_session("Study Chat")
        assert session.id > 0
        assert session.title == "Study Chat"

    def test_get_all_sessions(self, ai_service):
        ai_service.create_session("Chat 1")
        ai_service.create_session("Chat 2")
        sessions = ai_service.get_all_sessions()
        assert len(sessions) == 2

    def test_delete_session(self, ai_service):
        session = ai_service.create_session("Temp")
        ai_service.delete_session(session.id)
        sessions = ai_service.get_all_sessions()
        assert not any(s.id == session.id for s in sessions)

    def test_get_messages_empty(self, ai_service):
        session = ai_service.create_session("Empty")
        messages = ai_service.get_messages(session.id)
        assert messages == []

    def test_send_persists_messages(self, ai_service, mocker):
        """Verify that send() saves both user and assistant messages."""
        session = ai_service.create_session("Mocked")

        # Mock anthropic.Anthropic so no real HTTP call is made
        mock_response = mocker.MagicMock()
        mock_response.content[0].text = "Paris"
        mock_client = mocker.MagicMock()
        mock_client.messages.create.return_value = mock_response
        mocker.patch("anthropic.Anthropic", return_value=mock_client)

        reply = ai_service.send("fake-key", session.id, "What is the capital of France?", [])
        assert reply == "Paris"

        messages = ai_service.get_messages(session.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Paris"

    def test_markdown_to_html_bold(self):
        from services.ai_service import AIService
        html = AIService.markdown_to_html("**hello**")
        assert "<b>hello</b>" in html

    def test_markdown_to_html_code(self):
        from services.ai_service import AIService
        html = AIService.markdown_to_html("`code`")
        assert "<code" in html
        assert "code" in html

    def test_markdown_to_html_escapes_html(self):
        from services.ai_service import AIService
        html = AIService.markdown_to_html("<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
