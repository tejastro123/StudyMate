"""
ui/flashcard_ui.py
==================
Flashcard module UI for StudyMate.

Features:
- Deck list with stats (total / due / mastered)
- Create, rename, delete decks
- Card management (add, edit, delete)
- Study mode with card-flip animation and spaced-repetition buttons
- Progress bar tracking session progress
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QDialog,
    QLineEdit, QTextEdit, QProgressBar, QMessageBox, QScrollArea,
    QSizePolicy, QGridLayout,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal,
)
from PyQt6.QtGui import QFont, QColor

import modules.flashcards as fc_logic

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────── Dialogs ──

class DeckDialog(QDialog):
    """Create or rename a deck."""

    def __init__(self, parent=None, name: str = "", subject: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Deck")
        self.setFixedSize(360, 200)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Deck Name"))
        self._name = QLineEdit(name)
        self._name.setPlaceholderText("e.g. Biology — Chapter 3")
        layout.addWidget(self._name)

        layout.addWidget(QLabel("Subject (optional)"))
        self._subject = QLineEdit(subject)
        self._subject.setPlaceholderText("e.g. Biology")
        layout.addWidget(self._subject)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self._on_save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _on_save(self):
        if self._name.text().strip():
            self.accept()

    @property
    def deck_name(self) -> str:
        return self._name.text().strip()

    @property
    def subject(self) -> str:
        return self._subject.text().strip()


class CardDialog(QDialog):
    """Add or edit a flashcard."""

    def __init__(self, parent=None, front: str = "", back: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Flashcard")
        self.setFixedSize(440, 300)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Front (Question)"))
        self._front = QTextEdit(front)
        self._front.setFixedHeight(90)
        self._front.setPlaceholderText("Enter the question or term…")
        layout.addWidget(self._front)

        layout.addWidget(QLabel("Back (Answer)"))
        self._back = QTextEdit(back)
        self._back.setFixedHeight(90)
        self._back.setPlaceholderText("Enter the answer or definition…")
        layout.addWidget(self._back)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Card")
        save.clicked.connect(self._on_save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _on_save(self):
        if self._front.toPlainText().strip() and self._back.toPlainText().strip():
            self.accept()

    @property
    def front(self) -> str:
        return self._front.toPlainText().strip()

    @property
    def back(self) -> str:
        return self._back.toPlainText().strip()


# ─────────────────────────────────────────────────── Flip Card Widget ──

class FlipCardWidget(QFrame):
    """
    A card that flips between front and back using QPropertyAnimation.
    """

    def __init__(self, front: str, back: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumSize(500, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._showing_front = True
        self._front_text = front
        self._back_text = back

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._badge = QLabel("QUESTION")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            "color: #6C63FF; font-size: 11px; font-weight: 700; letter-spacing: 2px;"
        )
        layout.addWidget(self._badge)

        from PyQt6.QtWidgets import QTextBrowser
        self._text_lbl = QTextBrowser()
        self._text_lbl.setOpenExternalLinks(True)
        self._text_lbl.setFrameShape(QFrame.Shape.NoFrame)
        self._text_lbl.setStyleSheet("background: transparent; font-size: 16px; font-family: 'Segoe UI';")
        self._set_markdown(front)
        # Prevent QTextBrowser from intercepting all clicks so the card can still flip:
        self._text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        layout.addWidget(self._text_lbl, stretch=1)

        hint = QLabel("Click to flip ↻")
        hint.setObjectName("mutedLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self._animate_flip()

    def _animate_flip(self):
        self._anim_out = QPropertyAnimation(self, b"geometry")
        geo = self.geometry()
        mid = QRect(geo.x() + geo.width() // 2, geo.y(), 0, geo.height())

        self._anim_out.setStartValue(geo)
        self._anim_out.setEndValue(mid)
        self._anim_out.setDuration(120)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InQuad)
        self._anim_out.finished.connect(self._switch_face)
        self._anim_out.start()

    def _set_markdown(self, text: str):
        try:
            import markdown
            html = markdown.markdown(text, extensions=["fenced_code", "tables"])
            # Wrap in minimal HTML to ensure centering and correct text colour
            wrapped = f"""
            <div style="text-align: center; color: #E0E0E0;">
                {html}
            </div>
            """
            self._text_lbl.setHtml(wrapped)
        except Exception as exc:
            logger.error("Markdown parse error: %s", exc)
            self._text_lbl.setPlainText(text)

    def _switch_face(self):
        self._showing_front = not self._showing_front
        if self._showing_front:
            self._set_markdown(self._front_text)
            self._badge.setText("QUESTION")
            self._badge.setStyleSheet(
                "color: #6C63FF; font-size: 11px; font-weight: 700; letter-spacing: 2px;"
            )
        else:
            self._set_markdown(self._back_text)
            self._badge.setText("ANSWER")
            self._badge.setStyleSheet(
                "color: #50FA7B; font-size: 11px; font-weight: 700; letter-spacing: 2px;"
            )

        geo = self.geometry()
        mid = QRect(geo.x() + geo.width() // 2, geo.y(), 0, geo.height())
        original = QRect(geo.x(), geo.y(), self.sizeHint().width() or 500, geo.height())

        self._anim_in = QPropertyAnimation(self, b"geometry")
        self._anim_in.setStartValue(mid)
        self._anim_in.setEndValue(original)
        self._anim_in.setDuration(120)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim_in.start()

    def reset_to_front(self):
        self._showing_front = True
        self._set_markdown(self._front_text)
        self._badge.setText("QUESTION")
        self._badge.setStyleSheet(
            "color: #6C63FF; font-size: 11px; font-weight: 700; letter-spacing: 2px;"
        )


# ─────────────────────────────────────────────────── Study Mode ──

class StudyModeWidget(QWidget):
    """Full study session for a single deck."""

    finished = pyqtSignal()

    def __init__(self, deck_id: int, deck_name: str, parent=None):
        super().__init__(parent)
        self._deck_id = deck_id
        self._deck_name = deck_name
        self._cards: list[dict] = []
        self._current_index = 0
        self._reviewed = 0
        self._hard_queue: list[dict] = []  # cards to revisit this session

        self._build_ui()
        self._load_cards()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("secondaryBtn")
        back_btn.clicked.connect(self.finished.emit)
        header.addWidget(back_btn)

        self._title_lbl = QLabel()
        self._title_lbl.setObjectName("pageTitle")
        header.addWidget(self._title_lbl, stretch=1)

        self._progress_lbl = QLabel()
        self._progress_lbl.setObjectName("mutedLabel")
        header.addWidget(self._progress_lbl)
        layout.addLayout(header)

        # Progress bar
        self._progress_bar = QProgressBar()
        layout.addWidget(self._progress_bar)

        # Card
        self._card_widget = FlipCardWidget("", "")
        layout.addWidget(self._card_widget, stretch=1)

        # Difficulty buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._easy_btn = QPushButton("✅  Easy")
        self._easy_btn.setObjectName("successBtn")
        self._easy_btn.clicked.connect(lambda: self._on_review("easy"))

        self._medium_btn = QPushButton("😐  Medium")
        self._medium_btn.setObjectName("warningBtn")
        self._medium_btn.clicked.connect(lambda: self._on_review("medium"))

        self._hard_btn = QPushButton("❌  Hard")
        self._hard_btn.setObjectName("dangerBtn")
        self._hard_btn.clicked.connect(lambda: self._on_review("hard"))

        btn_row.addWidget(self._easy_btn)
        btn_row.addWidget(self._medium_btn)
        btn_row.addWidget(self._hard_btn)
        layout.addLayout(btn_row)

        # TTS listen button
        tts_row = QHBoxLayout()
        tts_row.addStretch()
        self._listen_btn = QPushButton("🔊  Listen")
        self._listen_btn.setObjectName("secondaryBtn")
        self._listen_btn.setFixedWidth(120)
        self._listen_btn.setToolTip("Read this card aloud")
        self._listen_btn.clicked.connect(self._on_listen)
        tts_row.addWidget(self._listen_btn)
        layout.addLayout(tts_row)

    def _load_cards(self):
        self._cards = fc_logic.get_due_cards(self._deck_id)
        self._current_index = 0
        self._reviewed = 0
        self._hard_queue = []
        total = len(self._cards)
        self._title_lbl.setText(f"Studying: {self._deck_name}")
        self._progress_bar.setMaximum(max(total, 1))
        self._progress_bar.setValue(0)
        if self._cards:
            self._show_current_card()
        else:
            self._show_done()

    def _show_current_card(self):
        card = self._current_card()
        if card is None:
            self._show_done()
            return
        self._card_widget._front_text = card["front"]
        self._card_widget._back_text = card["back"]
        self._card_widget.reset_to_front()
        total = len(self._cards) + len(self._hard_queue)
        self._progress_lbl.setText(f"{self._reviewed} / {total} reviewed")
        self._progress_bar.setMaximum(max(total, 1))
        self._progress_bar.setValue(self._reviewed)

    def _current_card(self) -> dict | None:
        if self._current_index < len(self._cards):
            return self._cards[self._current_index]
        if self._hard_queue:
            return self._hard_queue.pop(0)
        return None

    def _on_review(self, difficulty: str):
        card = self._current_card()
        if card is None:
            return
        fc_logic.record_review(card["id"], difficulty)
        if difficulty == "hard":
            self._hard_queue.append(card)
        self._reviewed += 1
        self._current_index += 1
        self._show_current_card()

    def _show_done(self):
        self._card_widget._front_text = "🎉 Session Complete!"
        self._card_widget._back_text = f"Reviewed {self._reviewed} card(s). Great work!"
        self._card_widget.reset_to_front()
        self._progress_lbl.setText("Done!")
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._easy_btn.setEnabled(False)
        self._medium_btn.setEnabled(False)
        self._hard_btn.setEnabled(False)

    def _on_listen(self):
        """Speak the currently visible card side via TTS."""
        from services.audio_service import speak
        card_widget = self._card_widget
        if card_widget._showing_front:
            text = card_widget._front_text
        else:
            text = card_widget._back_text
        speak(text)


# ─────────────────────────────────────────────────── Main Page ──

class FlashcardPage(QWidget):
    """Main Flashcards page with deck list and card management."""

    def __init__(self, cfg: dict = None):
        super().__init__()
        self._cfg = cfg or {}
        self._selected_deck_id: int | None = None
        self._cards: list[dict] = []
        self._study_widget: StudyModeWidget | None = None
        self._setup_ui()
        self._load_decks()

    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Stack: management view vs study view
        from PyQt6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        self._main_layout.addWidget(self._stack)

        # Page 0 – management view
        self._mgmt_widget = QWidget()
        mgmt_layout = QHBoxLayout(self._mgmt_widget)
        mgmt_layout.setContentsMargins(0, 0, 0, 0)
        mgmt_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_deck_panel())
        splitter.addWidget(self._build_card_panel())
        splitter.setSizes([280, 700])
        mgmt_layout.addWidget(splitter)

        self._stack.addWidget(self._mgmt_widget)

    def _build_deck_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("sidebar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("📇 Decks")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ New Deck")
        add_btn.clicked.connect(self._on_add_deck)
        btn_row.addWidget(add_btn)

        gen_pdf_btn = QPushButton("📄 Gen from PDF")
        gen_pdf_btn.setObjectName("secondaryBtn")
        gen_pdf_btn.clicked.connect(self._on_gen_from_pdf)
        btn_row.addWidget(gen_pdf_btn)

        layout.addLayout(btn_row)

        self._deck_list = QListWidget()
        self._deck_list.setAlternatingRowColors(True)
        self._deck_list.currentItemChanged.connect(self._on_deck_selected)
        layout.addWidget(self._deck_list, stretch=1)

        action_row = QHBoxLayout()
        rename_btn = QPushButton("✏️ Rename")
        rename_btn.setObjectName("secondaryBtn")
        rename_btn.clicked.connect(self._on_rename_deck)
        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._on_delete_deck)
        action_row.addWidget(rename_btn)
        action_row.addWidget(del_btn)
        layout.addLayout(action_row)

        return panel

    def _build_card_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        self._deck_title_lbl = QLabel("Select a deck")
        self._deck_title_lbl.setObjectName("pageTitle")
        hdr.addWidget(self._deck_title_lbl)
        hdr.addStretch()

        self._study_btn = QPushButton("▶ Study")
        self._study_btn.setEnabled(False)
        self._study_btn.clicked.connect(self._on_study)
        hdr.addWidget(self._study_btn)

        add_card_btn = QPushButton("+ Add Card")
        add_card_btn.clicked.connect(self._on_add_card)
        hdr.addWidget(add_card_btn)
        layout.addLayout(hdr)

        # Stats row
        self._stats_lbl = QLabel("")
        self._stats_lbl.setObjectName("mutedLabel")
        layout.addWidget(self._stats_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Card list
        self._card_list = QListWidget()
        self._card_list.setAlternatingRowColors(True)
        layout.addWidget(self._card_list, stretch=1)

        # Card actions
        card_actions = QHBoxLayout()
        edit_btn = QPushButton("✏️ Edit Card")
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.clicked.connect(self._on_edit_card)
        del_card_btn = QPushButton("🗑 Delete Card")
        del_card_btn.setObjectName("dangerBtn")
        del_card_btn.clicked.connect(self._on_delete_card)
        card_actions.addStretch()
        card_actions.addWidget(edit_btn)
        card_actions.addWidget(del_card_btn)
        layout.addLayout(card_actions)

        return panel

    # ──────────────────────────────────────────────────────── Deck logic ──
    def _load_decks(self):
        self._deck_list.clear()
        for deck in fc_logic.get_all_decks():
            label = f"📇 {deck['name']}"
            if deck.get("subject"):
                label += f"  [{deck['subject']}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, deck)
            self._deck_list.addItem(item)

    def _on_deck_selected(self, item: QListWidgetItem):
        if item is None:
            return
        deck = item.data(Qt.ItemDataRole.UserRole)
        self._selected_deck_id = deck["id"]
        self._deck_title_lbl.setText(deck["name"])
        self._study_btn.setEnabled(True)
        self._stats_lbl.setText(
            f"Total: {deck['total_cards']}  |  Due today: {deck['due_today']}  |  Mastered: {deck['mastered']}"
        )
        self._load_cards()

    def _on_add_deck(self):
        dlg = DeckDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fc_logic.create_deck(dlg.deck_name, dlg.subject)
            self._load_decks()

    def _on_gen_from_pdf(self):
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QApplication
        from PyQt6.QtGui import QCursor
        from PyQt6.QtCore import Qt
        import keyring
        import modules.ai_assistant as ai_logic

        api_key = self._cfg.get("api_key")
        provider = self._cfg.get("ai_provider", "anthropic")
        local_model = self._cfg.get("ollama_model", "llama3")

        if provider == "anthropic" and not api_key:
            QMessageBox.warning(self, "No API Key", "Please set your Anthropic API key in Settings first.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Generate Deck", "", "PDF Files (*.pdf)")
        if not path:
            return

        deck_name, ok = QInputDialog.getText(self, "New Deck Name", "What should we name this AI-generated deck?", text="AI Deck")
        if not ok or not deck_name.strip():
            return

        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            import os
            QApplication.processEvents()
            text = ai_logic.extract_text_from_pdf(path)
            
            # Request deck from Claude or Ollama
            cards = ai_logic.generate_deck_from_text(
                api_key, text, max_cards=15, 
                provider=provider, local_model=local_model
            )
            
            # Create the deck and add cards
            QApplication.restoreOverrideCursor()
            deck_id = fc_logic.create_deck(deck_name.strip(), "AI Generated")
            for c in cards:
                fc_logic.add_card(deck_id, c["front"], c["back"])
            
            self._load_decks()
            QMessageBox.information(self, "Success", f"Successfully generated {len(cards)} flashcards from PDF!")
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Generation Failed", str(e))

    def _on_rename_deck(self):
        if self._selected_deck_id is None:
            return
        item = self._deck_list.currentItem()
        if not item:
            return
        deck = item.data(Qt.ItemDataRole.UserRole)
        dlg = DeckDialog(self, name=deck["name"], subject=deck.get("subject", ""))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fc_logic.rename_deck(self._selected_deck_id, dlg.deck_name)
            self._load_decks()

    def _on_delete_deck(self):
        if self._selected_deck_id is None:
            return
        reply = QMessageBox.question(
            self, "Delete Deck",
            "Delete this deck and all its cards? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            fc_logic.delete_deck(self._selected_deck_id)
            self._selected_deck_id = None
            self._deck_title_lbl.setText("Select a deck")
            self._study_btn.setEnabled(False)
            self._stats_lbl.setText("")
            self._card_list.clear()
            self._load_decks()

    # ──────────────────────────────────────────────────────── Card logic ──
    def _load_cards(self):
        self._card_list.clear()
        if self._selected_deck_id is None:
            return
        self._cards = fc_logic.get_cards_for_deck(self._selected_deck_id)
        for card in self._cards:
            diff_icons = {"new": "🆕", "easy": "✅", "medium": "😐", "hard": "❌"}
            icon = diff_icons.get(card.get("difficulty", "new"), "🆕")
            label = f"{icon}  {card['front'][:60]}{'…' if len(card['front']) > 60 else ''}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, card)
            self._card_list.addItem(item)

    def _on_add_card(self):
        if self._selected_deck_id is None:
            QMessageBox.information(self, "No Deck", "Please select or create a deck first.")
            return
        dlg = CardDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fc_logic.add_card(self._selected_deck_id, dlg.front, dlg.back)
            self._load_cards()
            self._load_decks()

    def _on_edit_card(self):
        item = self._card_list.currentItem()
        if not item:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        dlg = CardDialog(self, front=card["front"], back=card["back"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fc_logic.update_card(card["id"], dlg.front, dlg.back)
            self._load_cards()

    def _on_delete_card(self):
        item = self._card_list.currentItem()
        if not item:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Card", "Delete this flashcard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            fc_logic.delete_card(card["id"])
            self._load_cards()
            self._load_decks()

    # ──────────────────────────────────────────────────────── Study ──
    def _on_study(self):
        if self._selected_deck_id is None:
            return
        item = self._deck_list.currentItem()
        if not item:
            return
        deck = item.data(Qt.ItemDataRole.UserRole)
        study = StudyModeWidget(self._selected_deck_id, deck["name"])
        study.finished.connect(self._on_study_done)
        self._stack.addWidget(study)
        self._stack.setCurrentWidget(study)
        self._study_widget = study

    def _on_study_done(self):
        if self._study_widget:
            self._stack.setCurrentWidget(self._mgmt_widget)
            self._stack.removeWidget(self._study_widget)
            self._study_widget.deleteLater()
            self._study_widget = None
        self._load_decks()
        self._load_cards()
