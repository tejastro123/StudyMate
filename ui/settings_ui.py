"""
ui/settings_ui.py
=================
Settings page for StudyMate.

Features:
- Enter / update Anthropic API key (masked, saved to config.json)
- Dark / Light theme toggle
- Default Pomodoro durations
- Notification toggle
- Export all data as ZIP backup
- Import data from ZIP backup
- Clear all data (with confirmation)
- App version display
"""

import json
import logging
import os
import shutil
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QSpinBox, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

_APPDATA = os.getenv("APPDATA", str(Path.home()))
_SM_DIR = Path(_APPDATA) / "StudyMate"
_DB_PATH = _SM_DIR / "studymate.db"
_CONFIG_PATH = _SM_DIR / "config.json"


class SettingsPage(QScrollArea):
    """Settings page – theme, API key, Pomodoro defaults, data management."""

    theme_changed = pyqtSignal(str)  # 'dark' | 'light'

    def __init__(self, cfg: dict = None, save_config_fn=None, app=None):
        super().__init__()
        self._cfg = cfg or {}
        self._save_config = save_config_fn
        self._app = app
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        title = QLabel("⚙️  Settings")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addWidget(self._build_api_section())
        layout.addWidget(self._build_theme_section())
        layout.addWidget(self._build_pomodoro_section())
        layout.addWidget(self._build_notifications_section())
        layout.addWidget(self._build_data_section())
        layout.addWidget(self._build_about_section())
        layout.addStretch()

    # ──────────────────────────────────────────────── Sections ──
    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)
        lbl = QLabel(title)
        lbl.setObjectName("sectionTitle")
        lay.addWidget(lbl)
        return frame, lay

    def _build_api_section(self) -> QFrame:
        frame, lay = self._card("🔑 Anthropic API Key")
        lbl = QLabel("Your API key is stored locally in config.json and never transmitted.")
        lbl.setObjectName("mutedLabel")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        row = QHBoxLayout()
        self._api_key_input = QLineEdit(self._cfg.get("api_key", ""))
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("sk-ant-…")
        row.addWidget(self._api_key_input, stretch=1)

        toggle_btn = QPushButton("👁")
        toggle_btn.setObjectName("iconBtn")
        toggle_btn.setFixedWidth(36)
        toggle_btn.setCheckable(True)
        toggle_btn.toggled.connect(
            lambda checked: self._api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        row.addWidget(toggle_btn)
        lay.addLayout(row)

        save_btn = QPushButton("💾 Save API Key")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._on_save_api_key)
        lay.addWidget(save_btn)
        return frame

    def _build_theme_section(self) -> QFrame:
        frame, lay = self._card("🎨 Appearance")
        row = QHBoxLayout()
        row.addWidget(QLabel("Theme:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark", "Light"])
        self._theme_combo.setCurrentText(self._cfg.get("theme", "dark").capitalize())
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        row.addWidget(self._theme_combo)
        row.addStretch()
        lay.addLayout(row)
        return frame

    def _build_pomodoro_section(self) -> QFrame:
        frame, lay = self._card("⏱️ Default Pomodoro Durations")

        def spin_row(label: str, key: str, default: int) -> QSpinBox:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            spin = QSpinBox()
            spin.setRange(1, 120)
            spin.setValue(self._cfg.get(key, default))
            spin.setFixedWidth(80)
            spin.valueChanged.connect(lambda v, k=key: self._update_cfg(k, v))
            row.addWidget(spin)
            row.addStretch()
            lay.addLayout(row)
            return spin

        self._pom_work = spin_row("Work duration (min):", "pomodoro_work", 25)
        self._pom_short = spin_row("Short break (min):", "pomodoro_short_break", 5)
        self._pom_long = spin_row("Long break (min):", "pomodoro_long_break", 15)

        save_btn = QPushButton("💾 Save Pomodoro Settings")
        save_btn.setFixedWidth(200)
        save_btn.clicked.connect(self._on_save_pomodoro)
        lay.addWidget(save_btn)
        return frame

    def _build_notifications_section(self) -> QFrame:
        frame, lay = self._card("🔔 Notifications")
        self._notif_chk = QCheckBox("Enable system notifications (timetable & focus timer)")
        self._notif_chk.setChecked(self._cfg.get("notifications_enabled", True))
        self._notif_chk.stateChanged.connect(
            lambda state: self._update_cfg("notifications_enabled", bool(state))
        )
        lay.addWidget(self._notif_chk)

        save_btn = QPushButton("💾 Save")
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(lambda: self._save_config(self._cfg) if self._save_config else None)
        lay.addWidget(save_btn)
        return frame

    def _build_data_section(self) -> QFrame:
        frame, lay = self._card("🗄️ Data Management")

        row = QHBoxLayout()
        export_btn = QPushButton("📦 Export Backup (.zip)")
        export_btn.clicked.connect(self._on_export)
        row.addWidget(export_btn)

        import_btn = QPushButton("📥 Import Backup")
        import_btn.setObjectName("secondaryBtn")
        import_btn.clicked.connect(self._on_import)
        row.addWidget(import_btn)
        row.addStretch()
        lay.addLayout(row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        clear_lbl = QLabel("⚠️ Clear All Data — permanently deletes all your study data.")
        clear_lbl.setObjectName("mutedLabel")
        clear_lbl.setWordWrap(True)
        lay.addWidget(clear_lbl)

        clear_btn = QPushButton("🗑  Clear All Data")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.setFixedWidth(180)
        clear_btn.clicked.connect(self._on_clear_data)
        lay.addWidget(clear_btn)
        return frame

    def _build_about_section(self) -> QFrame:
        frame, lay = self._card("ℹ️ About")
        lay.addWidget(QLabel("StudyMate v1.0.0"))
        lay.addWidget(QLabel("Built with PyQt6 · SQLite · Anthropic Claude"))
        lay.addWidget(QLabel("Data stored in: " + str(_SM_DIR)))
        return frame

    # ──────────────────────────────────────────────── Handlers ──
    def _update_cfg(self, key: str, value):
        self._cfg[key] = value

    def _on_save_api_key(self):
        key = self._api_key_input.text().strip()
        self._cfg["api_key"] = key
        if self._save_config:
            self._save_config(self._cfg)
        QMessageBox.information(self, "Saved", "API key saved successfully.")

    def _on_theme_changed(self, theme_text: str):
        theme = theme_text.lower()
        self._cfg["theme"] = theme
        if self._save_config:
            self._save_config(self._cfg)
        self.theme_changed.emit(theme)

    def _on_save_pomodoro(self):
        if self._save_config:
            self._save_config(self._cfg)
        QMessageBox.information(self, "Saved", "Pomodoro settings saved.")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", "studymate_backup.zip", "ZIP Archive (*.zip)"
        )
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                if _DB_PATH.exists():
                    zf.write(_DB_PATH, "studymate.db")
                if _CONFIG_PATH.exists():
                    zf.write(_CONFIG_PATH, "config.json")
            QMessageBox.information(self, "Exported", f"Backup saved to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", "", "ZIP Archive (*.zip)"
        )
        if not path:
            return
        reply = QMessageBox.question(
            self, "Confirm Import",
            "This will overwrite your current database. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            _SM_DIR.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(_SM_DIR)
            QMessageBox.information(
                self, "Imported",
                "Data imported. Please restart StudyMate for changes to take effect."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))

    def _on_clear_data(self):
        reply = QMessageBox.warning(
            self,
            "Clear All Data",
            "This will permanently delete ALL your flashcards, quizzes, timetable, "
            "focus sessions, and chat history.\n\nThis action CANNOT be undone. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from database.db import get_connection
            conn = get_connection()
            tables = [
                "chat_messages", "chat_sessions", "focus_sessions",
                "timetable_events", "quiz_attempts", "questions", "quizzes",
                "flashcards", "decks", "activity_log",
            ]
            for table in tables:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Cleared", "All data has been deleted. The app will continue running with an empty database.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
