"""
ui/main_window.py
=================
Main application window for StudyMate.

Contains the collapsible sidebar navigation and a QStackedWidget that
holds one page per module. A QPropertyAnimation drives the sidebar
expand / collapse transition.
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QSizePolicy, QFrame,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QSize,
)
from PyQt6.QtGui import QFont, QIcon

logger = logging.getLogger(__name__)

SIDEBAR_EXPANDED = 220
SIDEBAR_COLLAPSED = 64


class NavButton(QPushButton):
    """A sidebar navigation button with emoji icon and text label."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_text = icon
        self._label_text = label
        self._expanded = True
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_text()

    def _update_text(self):
        if self._expanded:
            self.setText(f"  {self._icon_text}  {self._label_text}")
        else:
            self.setText(f"{self._icon_text}")
        self.setToolTip(self._label_text)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._update_text()


class MainWindow(QMainWindow):
    """
    Top-level application window.

    Sidebar (left) + stacked content area (right).
    Pages are injected via register_page() after construction.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StudyMate 📚")
        self.setMinimumSize(1024, 680)
        self._sidebar_expanded = True
        self._nav_buttons: list[NavButton] = []
        self._pages: dict[str, QWidget] = {}
        self._setup_ui()

    # ──────────────────────────────────────────────────────── UI setup ──
    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")
        root_layout.addWidget(self._stack, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_EXPANDED)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("sidebarHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 16, 8, 16)

        self._app_title = QLabel("StudyMate")
        self._app_title.setObjectName("appTitle")
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self._app_title.setFont(font)
        h_layout.addWidget(self._app_title)
        h_layout.addStretch()

        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setObjectName("collapseBtn")
        self._collapse_btn.setFixedSize(28, 28)
        self._collapse_btn.clicked.connect(self._toggle_sidebar)
        h_layout.addWidget(self._collapse_btn)

        sidebar_layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep)

        # Nav buttons
        nav_items = [
            ("🏠", "Dashboard"),
            ("📇", "Flashcards"),
            ("📝", "Quizzes"),
            ("📅", "Timetable"),
            ("⏱️", "Focus Timer"),
            ("🤖", "AI Assistant"),
            ("⚙️", "Settings"),
        ]

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(2)

        for icon, label in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda checked, lbl=label: self._on_nav_clicked(lbl))
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_container)
        sidebar_layout.addStretch()

        # Version label
        ver = QLabel("v1.0.0")
        ver.setObjectName("mutedLabel")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setContentsMargins(0, 0, 0, 12)
        sidebar_layout.addWidget(ver)

        return sidebar

    # ──────────────────────────────────────────────────────── Pages ──
    def register_page(self, name: str, widget: QWidget):
        """Add a page widget to the stack and map it to a sidebar nav name."""
        self._pages[name] = widget
        self._stack.addWidget(widget)
        logger.debug("Registered page: %s", name)

    def navigate_to(self, name: str):
        """Switch to the page identified by *name*."""
        widget = self._pages.get(name)
        if widget is None:
            logger.warning("Page not found: %s", name)
            return
        self._stack.setCurrentWidget(widget)
        for btn in self._nav_buttons:
            btn.setChecked(btn._label_text == name)
            btn.setProperty("active", btn._label_text == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        logger.debug("Navigated to: %s", name)

    def _on_nav_clicked(self, label: str):
        self.navigate_to(label)

    # ──────────────────────────────────────────────────────── Sidebar animation ──
    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        target_width = SIDEBAR_EXPANDED if self._sidebar_expanded else SIDEBAR_COLLAPSED

        self._anim = QPropertyAnimation(self._sidebar, b"minimumWidth")
        self._anim.setDuration(250)
        self._anim.setStartValue(self._sidebar.width())
        self._anim.setEndValue(target_width)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self._anim.start()

        anim2 = QPropertyAnimation(self._sidebar, b"maximumWidth")
        anim2.setDuration(250)
        anim2.setStartValue(self._sidebar.width())
        anim2.setEndValue(target_width)
        anim2.setEasingCurve(QEasingCurve.Type.InOutQuart)
        anim2.start()
        self._anim2 = anim2  # keep reference

        # Update button labels / title visibility
        self._app_title.setVisible(self._sidebar_expanded)
        self._collapse_btn.setText("◀" if self._sidebar_expanded else "▶")
        for btn in self._nav_buttons:
            btn.set_expanded(self._sidebar_expanded)

    # ──────────────────────────────────────────────────────── Theme ──
    def apply_light_theme(self):
        for w in self.findChildren(QWidget):
            w.setProperty("theme", "light")
            w.style().unpolish(w)
            w.style().polish(w)

    def apply_dark_theme(self):
        for w in self.findChildren(QWidget):
            w.setProperty("theme", "")
            w.style().unpolish(w)
            w.style().polish(w)
