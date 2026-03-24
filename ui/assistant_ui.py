"""
ui/assistant_ui.py
==================
AI Study Assistant UI for StudyMate.

Features:
- Chat interface with message bubbles (user right, AI left)
- Quick action buttons (Explain, Quiz me, Summarize, Tips)
- Markdown rendering in AI responses
- Copy button on each AI message
- Loading spinner during API call
- Session history sidebar
- API key warning if not configured
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QSizePolicy, QSplitter, QProgressBar,
    QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QClipboard

import modules.ai_assistant as ai_logic

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────── Worker Thread ──

class AIWorker(QThread):
    """Run the Claude API call in a background thread to keep UI responsive."""
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, session_id: int, user_text: str, history: list[dict]):
        super().__init__()
        self._api_key = api_key
        self._session_id = session_id
        self._user_text = user_text
        self._history = history

    def run(self):
        try:
            reply = ai_logic.send_message(
                self._api_key, self._session_id, self._user_text, self._history
            )
            self.result.emit(reply)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────── Message Bubble ──

class MessageBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self._role = role
        is_user = role == "user"

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(8)

        if is_user:
            outer.addStretch()

        bubble = QFrame()
        bubble.setObjectName("card")
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        bubble.setMaximumWidth(680)

        blay = QVBoxLayout(bubble)
        blay.setContentsMargins(12, 10, 12, 10)
        blay.setSpacing(6)

        # Role label
        role_lbl = QLabel("You" if is_user else "🤖 StudyMate AI")
        role_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        role_lbl.setStyleSheet("color: #6C63FF;" if is_user else "color: #50FA7B;")
        blay.addWidget(role_lbl)

        # Content
        content_lbl = QLabel()
        content_lbl.setWordWrap(True)
        content_lbl.setTextFormat(Qt.TextFormat.RichText)
        content_lbl.setOpenExternalLinks(False)
        if is_user:
            content_lbl.setText(content)
        else:
            content_lbl.setText(ai_logic.markdown_to_html(content))
        content_lbl.setFont(QFont("Segoe UI", 13))
        blay.addWidget(content_lbl)

        # Copy button for AI messages
        if not is_user:
            copy_btn = QPushButton("📋 Copy")
            copy_btn.setObjectName("iconBtn")
            copy_btn.setFixedWidth(70)
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(content))
            blay.addWidget(copy_btn, alignment=Qt.AlignmentFlag.AlignRight)

        if is_user:
            bubble.setStyleSheet(
                "background-color: #3730A3; border-radius: 12px; border: none;"
            )
        else:
            bubble.setStyleSheet(
                "background-color: #2A2A3E; border-radius: 12px; border: 1px solid #35355A;"
            )

        outer.addWidget(bubble)

        if not is_user:
            outer.addStretch()


# ─────────────────────────────────────────────────── Chat Area ──

class ChatArea(QScrollArea):
    """Scrollable area containing message bubbles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()
        self.setWidget(self._container)

    def add_message(self, role: str, content: str):
        bubble = MessageBubble(role, content)
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def clear_messages(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_history(self, messages: list[dict]):
        self.clear_messages()
        for msg in messages:
            self.add_message(msg["role"], msg["content"])


# ─────────────────────────────────────────────────── Main Page ──

class AssistantPage(QWidget):
    """AI Study Assistant main page."""

    def __init__(self, cfg: dict = None, save_config_fn=None):
        super().__init__()
        self._cfg = cfg or {}
        self._save_config = save_config_fn
        self._session_id: int | None = None
        self._history: list[dict] = []
        self._worker: AIWorker | None = None
        self._setup_ui()
        self._load_sessions()
        self._new_session()

    def _setup_ui(self):
        # Single root layout – splitter fills the whole widget
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: session history ──────────────────────────────────
        left = QWidget()
        left.setObjectName("sidebar")
        left.setFixedWidth(220)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 16, 12, 16)
        left_layout.setSpacing(8)

        sessions_title = QLabel("💬 Conversations")
        sessions_title.setObjectName("sectionTitle")
        left_layout.addWidget(sessions_title)

        new_chat_btn = QPushButton("+ New Chat")
        new_chat_btn.clicked.connect(self._new_session)
        left_layout.addWidget(new_chat_btn)

        self._session_list = QListWidget()
        self._session_list.currentItemChanged.connect(self._on_session_selected)
        left_layout.addWidget(self._session_list, stretch=1)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._on_delete_session)
        left_layout.addWidget(del_btn)

        splitter.addWidget(left)

        # ── Right: chat panel ──────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("🤖  AI Study Assistant")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        right_layout.addLayout(hdr)

        # API key warning
        self._api_warning = QLabel(
            "⚠️  No API key configured. Go to Settings to add your Anthropic API key."
        )
        self._api_warning.setStyleSheet("color: #FFB86C; font-size: 12px; padding: 6px;")
        self._api_warning.setVisible(not bool(self._cfg.get("api_key")))
        right_layout.addWidget(self._api_warning)

        # Quick actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        quick_actions = [
            ("📖 Explain a concept", "Explain this concept clearly with examples: "),
            ("❓ Quiz me", "Give me 5 quiz questions on this topic: "),
            ("📝 Summarize my notes", self._get_clipboard_prefix),
            ("💡 Give study tips", "Give me 5 practical study tips for students."),
        ]
        for label, prompt_or_fn in quick_actions:
            btn = QPushButton(label)
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda _, p=prompt_or_fn: self._on_quick_action(p))
            actions_row.addWidget(btn)
        right_layout.addLayout(actions_row)

        # Chat area
        self._chat_area = ChatArea()
        right_layout.addWidget(self._chat_area, stretch=1)

        # Loading indicator
        self._loading_bar = QProgressBar()
        self._loading_bar.setRange(0, 0)  # indeterminate
        self._loading_bar.setFixedHeight(4)
        self._loading_bar.setVisible(False)
        right_layout.addWidget(self._loading_bar)

        # Input area
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._input = QTextEdit()
        self._input.setFixedHeight(72)
        self._input.setPlaceholderText("Ask anything… (Shift+Enter for new line, Enter to send)")
        self._input.installEventFilter(self)
        input_row.addWidget(self._input, stretch=1)

        mic_btn = QPushButton("🎤")
        mic_btn.setObjectName("secondaryBtn")
        mic_btn.setFixedSize(48, 72)
        mic_btn.setToolTip("Speak your question (requires microphone)")
        mic_btn.clicked.connect(self._on_voice_input)
        input_row.addWidget(mic_btn)

        send_btn = QPushButton("Send ➤")
        send_btn.setFixedSize(90, 72)
        send_btn.clicked.connect(self._on_send)
        input_row.addWidget(send_btn)
        right_layout.addLayout(input_row)

        splitter.addWidget(right)
        splitter.setSizes([220, 900])

        root_layout.addWidget(splitter)

    # ──────────────────────────────────────────────── Event filter ──
    def eventFilter(self, source, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if source is self._input and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if (key_event.key() == Qt.Key.Key_Return and
                    not (key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
                self._on_send()
                return True
        return super().eventFilter(source, event)

    # ──────────────────────────────────────────────── Sessions ──
    def _load_sessions(self):
        self._session_list.blockSignals(True)
        self._session_list.clear()
        for sess in ai_logic.get_all_sessions():
            item = QListWidgetItem(sess["title"] or "Chat")
            item.setData(Qt.ItemDataRole.UserRole, sess)
            self._session_list.addItem(item)
        self._session_list.blockSignals(False)

    def _new_session(self):
        session_id = ai_logic.create_session("New Chat")
        self._session_id = session_id
        self._history = []
        self._chat_area.clear_messages()
        # Show a welcome message
        self._chat_area.add_message(
            "assistant",
            "👋 Hi! I'm **StudyMate AI**. I can:\n\n"
            "- 📖 Explain any concept\n"
            "- ❓ Quiz you on a topic\n"
            "- 📝 Summarize your notes\n"
            "- 💡 Give study tips\n\n"
            "What would you like to do today?",
        )
        self._load_sessions()

    def _on_session_selected(self, item: QListWidgetItem):
        if not item:
            return
        sess = item.data(Qt.ItemDataRole.UserRole)
        self._session_id = sess["id"]
        messages = ai_logic.get_messages(self._session_id)
        self._history = [{"role": m["role"], "content": m["content"]} for m in messages]
        self._chat_area.load_history(messages)

    def _on_delete_session(self):
        if not self._session_id:
            return
        ai_logic.delete_session(self._session_id)
        self._session_id = None
        self._history = []
        self._chat_area.clear_messages()
        self._load_sessions()
        self._new_session()

    # ──────────────────────────────────────────────── Messaging ──
    def _get_clipboard_prefix(self) -> str:
        clipboard_text = QApplication.clipboard().text()
        if clipboard_text.strip():
            return f"Please summarize these notes:\n\n{clipboard_text}"
        return "Summarize key study notes on: "

    def _on_quick_action(self, prompt_or_fn):
        if callable(prompt_or_fn):
            prompt = prompt_or_fn()
        else:
            prompt = prompt_or_fn
        self._input.setPlainText(prompt)
        self._input.setFocus()

    def _on_voice_input(self):
        """Listen to the user's microphone and fill the input box with the transcription."""
        from services.audio_service import listen_once, is_stt_available
        from PyQt6.QtWidgets import QMessageBox
        if not is_stt_available():
            QMessageBox.information(
                self,
                "Microphone Unavailable",
                "Speech-to-text requires PyAudio (a system audio library).\n\n"
                "To enable it, install the Microsoft C++ Build Tools and then run:\n"
                "  pip install pyaudio",
            )
            return
        # Listen in a background thread to avoid freezing the UI
        import threading
        def _listen():
            result = listen_once(timeout=7)
            if result:
                self._input.setPlainText(result)
        threading.Thread(target=_listen, daemon=True).start()

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        if not self._cfg.get("api_key"):
            self._api_warning.setVisible(True)
            return

        self._input.clear()
        self._chat_area.add_message("user", text)
        self._set_loading(True)

        if not self._session_id:
            self._session_id = ai_logic.create_session(text[:40])
            self._load_sessions()

        self._worker = AIWorker(
            self._cfg["api_key"], self._session_id, text, list(self._history)
        )
        self._worker.result.connect(self._on_ai_reply)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()

    def _on_ai_reply(self, reply: str):
        self._set_loading(False)
        # Rebuild full history from DB to stay perfectly in sync
        if self._session_id:
            msgs = ai_logic.get_messages(self._session_id)
            self._history = [{"role": m["role"], "content": m["content"]} for m in msgs]
        self._chat_area.add_message("assistant", reply)

    def _on_ai_error(self, error: str):
        self._set_loading(False)
        friendly = (
            "❌ Could not reach the AI. Please check your API key and internet connection.\n\n"
            f"Details: {error}"
        )
        self._chat_area.add_message("assistant", friendly)

    def _set_loading(self, loading: bool):
        self._loading_bar.setVisible(loading)
        self._input.setEnabled(not loading)
