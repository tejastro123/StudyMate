"""
ui/dashboard_ui.py
==================
Dashboard page for StudyMate.

Displays:
- Summary stat cards (decks, quizzes today, timetable events, focus time)
- A random motivational quote
- Recent activity feed (last 5 entries)
- Quick-access buttons to each module
"""

import logging
import random
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from database.db import get_connection

logger = logging.getLogger(__name__)

QUOTES = [
    "The secret of getting ahead is getting started. – Mark Twain",
    "Don't watch the clock; do what it does. Keep going. – Sam Levenson",
    "Education is the most powerful weapon you can use. – Nelson Mandela",
    "The beautiful thing about learning is nobody can take it away. – B.B. King",
    "An investment in knowledge pays the best interest. – Benjamin Franklin",
    "The more that you read, the more things you will know. – Dr. Seuss",
    "Learning is a treasure that will follow its owner everywhere. – Chinese Proverb",
    "Study hard what interests you the most in the most undisciplined way. – Richard Feynman",
    "I have no special talents. I am only passionately curious. – Albert Einstein",
    "Success is the sum of small efforts repeated day in and day out. – Robert Collier",
    "A mind is a fire to be kindled, not a vessel to be filled. – Plutarch",
    "The expert in anything was once a beginner. – Helen Hayes",
    "Develop a passion for learning. If you do, you will never cease to grow. – Anthony J. D'Angelo",
    "Education is not preparation for life; education is life itself. – John Dewey",
    "The more I read, the more I acquire, the more certain I am that I know nothing. – Voltaire",
    "Real learning comes about when the competitive spirit has ceased. – Jiddu Krishnamurti",
    "Mistakes are the portals of discovery. – James Joyce",
    "Hardships often prepare ordinary people for an extraordinary destiny. – C.S. Lewis",
    "Push yourself because no one else is going to do it for you.",
    "Great things never come from comfort zones.",
]


class StatCard(QFrame):
    """Single statistic card widget."""

    def __init__(self, icon: str, value: str, label: str, color: str = "#6C63FF"):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 22))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("statValue")
        self._value_lbl.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(self._value_lbl)

        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def set_value(self, value: str):
        self._value_lbl.setText(value)


class ActivityItem(QWidget):
    """A single row in the recent-activity feed."""

    def __init__(self, action: str, module: str, timestamp: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        mod_lbl = QLabel(f"[{module}]")
        mod_lbl.setObjectName("accentLabel")
        mod_lbl.setFixedWidth(100)
        layout.addWidget(mod_lbl)

        act_lbl = QLabel(action)
        act_lbl.setWordWrap(True)
        layout.addWidget(act_lbl, stretch=1)

        ts_lbl = QLabel(timestamp[:16] if timestamp else "")
        ts_lbl.setObjectName("mutedLabel")
        ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(ts_lbl)


class DashboardPage(QScrollArea):
    """
    Dashboard page – summary stats, quote, activity feed, quick links.

    Parameters
    ----------
    navigate_fn : callable
        Function accepting a page name string (from MainWindow.navigate_to).
    """

    def __init__(self, navigate_fn=None):
        super().__init__()
        self._navigate = navigate_fn
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.setWidget(container)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(24)

        self._build_header()
        self._build_stats()
        self._build_quote()
        self._build_quick_access()
        self._build_activity()

        # Refresh data every 60 s
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(60_000)

        self.refresh()

    # ──────────────────────────────────────────────────────── Build ──
    def _build_header(self):
        row = QHBoxLayout()
        title = QLabel("🏠  Dashboard")
        title.setObjectName("pageTitle")
        row.addWidget(title)
        row.addStretch()

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedWidth(110)
        refresh_btn.clicked.connect(self.refresh)
        row.addWidget(refresh_btn)
        self._layout.addLayout(row)

    def _build_stats(self):
        section = QLabel("Overview")
        section.setObjectName("sectionTitle")
        self._layout.addWidget(section)

        grid = QGridLayout()
        grid.setSpacing(16)

        self._card_decks = StatCard("📇", "0", "Flashcard Decks", "#6C63FF")
        self._card_quizzes = StatCard("📝", "0", "Quizzes Today", "#50FA7B")
        self._card_events = StatCard("📅", "0", "Events Today", "#FFB86C")
        self._card_focus = StatCard("⏱️", "0m", "Focus Time Today", "#FF79C6")

        grid.addWidget(self._card_decks, 0, 0)
        grid.addWidget(self._card_quizzes, 0, 1)
        grid.addWidget(self._card_events, 0, 2)
        grid.addWidget(self._card_focus, 0, 3)

        self._layout.addLayout(grid)

    def _build_quote(self):
        frame = QFrame()
        frame.setObjectName("card")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(20, 16, 20, 16)

        header = QLabel("💡  Daily Motivation")
        header.setObjectName("sectionTitle")
        fl.addWidget(header)

        self._quote_lbl = QLabel(random.choice(QUOTES))
        self._quote_lbl.setWordWrap(True)
        self._quote_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        self._quote_lbl.setStyleSheet("color: #C0C0D8; font-style: italic;")
        fl.addWidget(self._quote_lbl)

        self._layout.addWidget(frame)

    def _build_quick_access(self):
        section = QLabel("Quick Access")
        section.setObjectName("sectionTitle")
        self._layout.addWidget(section)

        row = QHBoxLayout()
        row.setSpacing(12)

        modules = [
            ("📇 Flashcards", "Flashcards", "#6C63FF"),
            ("📝 Quizzes", "Quizzes", "#50FA7B"),
            ("📅 Timetable", "Timetable", "#FFB86C"),
            ("⏱️ Focus Timer", "Focus Timer", "#FF79C6"),
            ("🤖 AI Assistant", "AI Assistant", "#8BE9FD"),
        ]

        for label, page, color in modules:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"background-color: {color}20; color: {color}; "
                f"border: 1px solid {color}50; border-radius: 10px; "
                f"padding: 10px 16px; font-weight: 600;"
            )
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _, p=page: self._navigate(p) if self._navigate else None)
            row.addWidget(btn)

        self._layout.addLayout(row)

    def _build_activity(self):
        section = QLabel("Recent Activity")
        section.setObjectName("sectionTitle")
        self._layout.addWidget(section)

        frame = QFrame()
        frame.setObjectName("card")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(0)
        self._activity_layout = fl
        self._activity_frame = frame
        self._layout.addWidget(frame)
        self._layout.addStretch()

    # ──────────────────────────────────────────────────────── Data ──
    def refresh(self):
        """Reload all stats from the database."""
        try:
            self._refresh_stats()
            self._refresh_activity()
        except Exception as exc:
            logger.error("Dashboard refresh error: %s", exc)

    def _refresh_stats(self):
        conn = get_connection()
        today = date.today().isoformat()

        # Decks count
        row = conn.execute("SELECT COUNT(*) FROM decks").fetchone()
        self._card_decks.set_value(str(row[0]))

        # Quizzes today
        row = conn.execute(
            "SELECT COUNT(*) FROM quiz_attempts WHERE DATE(attempted_at) = ?", (today,)
        ).fetchone()
        self._card_quizzes.set_value(str(row[0]))

        # Events today (recurring + specific_date)
        today_weekday = date.today().weekday()  # 0=Mon
        row = conn.execute(
            """SELECT COUNT(*) FROM timetable_events
               WHERE is_recurring = 1 AND day_of_week = ?
               OR (is_recurring = 0 AND specific_date = ?)""",
            (today_weekday, today),
        ).fetchone()
        self._card_events.set_value(str(row[0]))

        # Focus time today (minutes)
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) FROM focus_sessions WHERE DATE(started_at) = ?",
            (today,),
        ).fetchone()
        mins = int(row[0])
        if mins >= 60:
            self._card_focus.set_value(f"{mins//60}h {mins%60}m")
        else:
            self._card_focus.set_value(f"{mins}m")

        conn.close()

    def _refresh_activity(self):
        # Clear previous items
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        conn = get_connection()
        rows = conn.execute(
            "SELECT action, module, logged_at FROM activity_log ORDER BY logged_at DESC LIMIT 5"
        ).fetchall()
        conn.close()

        if not rows:
            lbl = QLabel("No recent activity yet. Start studying! 🚀")
            lbl.setObjectName("mutedLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setContentsMargins(0, 16, 0, 16)
            self._activity_layout.addWidget(lbl)
            return

        for i, row in enumerate(rows):
            item = ActivityItem(row["action"], row["module"] or "App", row["logged_at"] or "")
            self._activity_layout.addWidget(item)
            if i < len(rows) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                self._activity_layout.addWidget(sep)
