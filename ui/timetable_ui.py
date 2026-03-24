"""
ui/timetable_ui.py
==================
Timetable / Schedule Tracker UI for StudyMate.

Features:
- Weekly grid view (Mon–Sun, 6 AM–10 PM, 30-min slots)
- Click-to-add events, colour-coded by subject
- Today's column highlighted
- Upcoming events sidebar
- Windows notification 5 min before an event (plyer)
- Export week as PNG screenshot
- Recurring and one-off events
"""

import logging
from datetime import date, datetime, time as dtime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QLineEdit, QComboBox, QCheckBox, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QMessageBox,
    QColorDialog, QTimeEdit, QCalendarWidget,
)
from PyQt6.QtCore import (
    Qt, QTimer, QTime, pyqtSignal,
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap

import modules.timetable as tt_logic

logger = logging.getLogger(__name__)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = list(range(6, 23))  # 6 AM to 10 PM
EVENT_TYPES = ["class", "study", "break", "exam"]
TYPE_COLOURS = {
    "class": "#6C63FF",
    "study": "#50FA7B",
    "break": "#FFB86C",
    "exam": "#FF5555",
}


# ──────────────────────────────────────────────── Add/Edit Dialog ──

class EventDialog(QDialog):
    """Add or edit a timetable event."""

    def __init__(self, parent=None, event: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Event" if event is None else "Edit Event")
        self.setFixedSize(420, 400)
        self._color = (event or {}).get("color", "#6C63FF")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Title"))
        self._title = QLineEdit((event or {}).get("title", ""))
        self._title.setPlaceholderText("e.g. Physics Lecture")
        layout.addWidget(self._title)

        layout.addWidget(QLabel("Subject"))
        self._subject = QLineEdit((event or {}).get("subject", ""))
        self._subject.setPlaceholderText("e.g. Physics")
        layout.addWidget(self._subject)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Type:"))
        self._type = QComboBox()
        self._type.addItems(EVENT_TYPES)
        if event:
            idx = EVENT_TYPES.index(event["event_type"]) if event.get("event_type") in EVENT_TYPES else 0
            self._type.setCurrentIndex(idx)
        self._type.currentTextChanged.connect(self._on_type_changed)
        row1.addWidget(self._type)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Day:"))
        self._day = QComboBox()
        self._day.addItems(DAYS)
        if event:
            self._day.setCurrentIndex(event.get("day_of_week", 0))
        row2.addWidget(self._day)
        row2.addStretch()
        layout.addLayout(row2)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Start:"))
        self._start = QTimeEdit()
        self._start.setDisplayFormat("HH:mm")
        if event and event.get("start_time"):
            h, m = map(int, event["start_time"].split(":"))
            self._start.setTime(QTime(h, m))
        else:
            self._start.setTime(QTime(9, 0))
        time_row.addWidget(self._start)

        time_row.addWidget(QLabel("End:"))
        self._end = QTimeEdit()
        self._end.setDisplayFormat("HH:mm")
        if event and event.get("end_time"):
            h, m = map(int, event["end_time"].split(":"))
            self._end.setTime(QTime(h, m))
        else:
            self._end.setTime(QTime(10, 0))
        time_row.addWidget(self._end)
        layout.addLayout(time_row)

        self._recurring_chk = QCheckBox("Recurring (every week)")
        self._recurring_chk.setChecked(bool((event or {}).get("is_recurring", True)))
        self._recurring_chk.stateChanged.connect(self._on_recurring_change)
        layout.addWidget(self._recurring_chk)

        self._date_row = QHBoxLayout()
        self._date_row.addWidget(QLabel("Date:"))
        self._date_edit = QCalendarWidget()
        self._date_edit.setVisible(False)
        layout.addLayout(self._date_row)
        layout.addWidget(self._date_edit)

        # Colour picker
        colour_row = QHBoxLayout()
        colour_row.addWidget(QLabel("Colour:"))
        self._colour_btn = QPushButton()
        self._colour_btn.setFixedSize(32, 28)
        self._colour_btn.setStyleSheet(f"background-color: {self._color}; border-radius: 6px; border: none;")
        self._colour_btn.clicked.connect(self._pick_colour)
        colour_row.addWidget(self._colour_btn)
        colour_row.addStretch()
        layout.addLayout(colour_row)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self._on_save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _on_type_changed(self, t: str):
        self._color = TYPE_COLOURS.get(t, self._color)
        self._colour_btn.setStyleSheet(
            f"background-color: {self._color}; border-radius: 6px; border: none;"
        )

    def _on_recurring_change(self, state):
        self._date_edit.setVisible(not bool(state))

    def _pick_colour(self):
        col = QColorDialog.getColor(QColor(self._color), self, "Pick Event Colour")
        if col.isValid():
            self._color = col.name()
            self._colour_btn.setStyleSheet(
                f"background-color: {self._color}; border-radius: 6px; border: none;"
            )

    def _on_save(self):
        if self._title.text().strip():
            self.accept()

    @property
    def event_data(self) -> dict:
        specific_date = ""
        if not self._recurring_chk.isChecked():
            qdate = self._date_edit.selectedDate()
            specific_date = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        return {
            "title": self._title.text().strip(),
            "subject": self._subject.text().strip(),
            "event_type": self._type.currentText(),
            "day_of_week": self._day.currentIndex(),
            "start_time": self._start.time().toString("HH:mm"),
            "end_time": self._end.time().toString("HH:mm"),
            "color": self._color,
            "is_recurring": 1 if self._recurring_chk.isChecked() else 0,
            "specific_date": specific_date,
        }


# ──────────────────────────────────────────────── Event Block ──

class EventBlock(QFrame):
    """A clickable coloured block representing one event in the grid."""
    clicked = pyqtSignal(dict)

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        self._event = event
        color = event.get("color", "#6C63FF")
        self.setStyleSheet(
            f"background-color: {color}33; border-left: 3px solid {color}; "
            f"border-radius: 6px; padding: 2px 6px;"
        )
        self.setToolTip(
            f"{event['title']}\n{event['start_time']} – {event['end_time']}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)

        title_lbl = QLabel(event["title"])
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        time_lbl = QLabel(f"{event['start_time']} – {event['end_time']}")
        time_lbl.setStyleSheet("color: #9090B0; font-size: 10px; border: none; background: transparent;")
        layout.addWidget(time_lbl)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit(self._event)


# ──────────────────────────────────────────────── Weekly Grid ──

class WeeklyGrid(QScrollArea):
    """Scrollable weekly timetable grid (Mon–Sun, 6 AM–10 PM)."""
    slot_clicked = pyqtSignal(int, str)   # day_of_week, time_string "HH:MM"
    event_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._inner = QWidget()
        self.setWidget(self._inner)
        self._grid = QGridLayout(self._inner)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(1)
        self._build_headers()
        self._build_time_slots()

    def _build_headers(self):
        today_dow = date.today().weekday()
        # Empty top-left corner
        corner = QLabel("")
        corner.setFixedWidth(56)
        self._grid.addWidget(corner, 0, 0)

        for col, day in enumerate(DAYS, start=1):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            if col - 1 == today_dow:
                lbl.setStyleSheet(
                    "background-color: #6C63FF33; color: #6C63FF; "
                    "border-radius: 8px; padding: 4px;"
                )
            else:
                lbl.setStyleSheet("color: #9090B0; padding: 4px;")
            self._grid.addWidget(lbl, 0, col)

    def _build_time_slots(self):
        today_dow = date.today().weekday()
        for row_idx, hour in enumerate(HOURS):
            time_str = f"{hour:02d}:00"
            time_lbl = QLabel(time_str)
            time_lbl.setFixedWidth(56)
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            time_lbl.setStyleSheet("color: #9090B0; font-size: 11px; padding-right: 6px; padding-top: 4px;")
            self._grid.addWidget(time_lbl, row_idx + 1, 0)

            for col_idx, _ in enumerate(DAYS):
                slot = QFrame()
                slot.setFixedHeight(52)
                slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                if col_idx == today_dow:
                    slot.setStyleSheet(
                        "background-color: #6C63FF0A; border-bottom: 1px solid #35355A;"
                    )
                else:
                    slot.setStyleSheet("border-bottom: 1px solid #2A2A3E;")
                slot.setCursor(Qt.CursorShape.PointingHandCursor)
                slot.mousePressEvent = lambda e, d=col_idx, t=time_str: self.slot_clicked.emit(d, t)
                self._grid.addWidget(slot, row_idx + 1, col_idx + 1)

    def load_events(self, events: list[dict]):
        """Overlay event blocks on the grid."""
        # Remove old event blocks
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            if item and isinstance(item.widget(), EventBlock):
                item.widget().deleteLater()
                self._grid.removeItem(item)

        for event in events:
            try:
                start_h = int(event["start_time"][:2])
                row = start_h - 6 + 1  # offset by header row and start hour
                if row < 1 or row > len(HOURS):
                    continue
                col = event["day_of_week"] + 1
                blk = EventBlock(event)
                blk.clicked.connect(self.event_clicked.emit)
                self._grid.addWidget(blk, row, col)
            except Exception as exc:
                logger.warning("Failed to render event %s: %s", event.get("id"), exc)


# ──────────────────────────────────────────────── Main Page ──

class TimetablePage(QWidget):
    """Main Timetable page."""

    def __init__(self):
        super().__init__()
        self._notification_timer = QTimer()
        self._notification_timer.timeout.connect(self._check_notifications)
        self._notification_timer.start(60_000)  # check every minute
        self._setup_ui()
        self._load_events()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left: grid
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 16, 12, 16)
        left_layout.setSpacing(12)

        # Page title + controls
        hdr = QHBoxLayout()
        title = QLabel("📅  Timetable")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        hdr.addStretch()

        add_btn = QPushButton("+ Add Event")
        add_btn.clicked.connect(self._on_add_event)
        hdr.addWidget(add_btn)

        export_btn = QPushButton("📸 Export PNG")
        export_btn.setObjectName("secondaryBtn")
        export_btn.clicked.connect(self._on_export_png)
        hdr.addWidget(export_btn)
        left_layout.addLayout(hdr)

        self._grid = WeeklyGrid()
        self._grid.slot_clicked.connect(self._on_slot_clicked)
        self._grid.event_clicked.connect(self._on_event_clicked)
        left_layout.addWidget(self._grid, stretch=1)

        layout.addWidget(left, stretch=1)

        # Right: sidebar (upcoming events)
        right = QWidget()
        right.setObjectName("sidebar")
        right.setFixedWidth(240)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(8)

        today_lbl = QLabel(f"📅 Today — {date.today().strftime('%A, %b %d')}")
        today_lbl.setObjectName("sectionTitle")
        right_layout.addWidget(today_lbl)

        self._upcoming_layout = QVBoxLayout()
        self._upcoming_layout.setSpacing(6)
        right_layout.addLayout(self._upcoming_layout)
        right_layout.addStretch()

        layout.addWidget(right)

    def _load_events(self):
        events = tt_logic.get_all_events()
        self._grid.load_events(events)
        self._refresh_upcoming()

    def _refresh_upcoming(self):
        while self._upcoming_layout.count():
            item = self._upcoming_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        events = tt_logic.get_todays_events()[:5]
        if not events:
            lbl = QLabel("No events today 🎉")
            lbl.setObjectName("mutedLabel")
            self._upcoming_layout.addWidget(lbl)
            return

        for ev in events:
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)

            color = ev.get("color", "#6C63FF")
            title_lbl = QLabel(ev["title"])
            title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            title_lbl.setStyleSheet(f"color: {color};")
            cl.addWidget(title_lbl)

            time_lbl = QLabel(f"{ev['start_time']} – {ev['end_time']}")
            time_lbl.setObjectName("mutedLabel")
            cl.addWidget(time_lbl)

            self._upcoming_layout.addWidget(card)

    def _on_slot_clicked(self, day: int, time_str: str):
        dlg = EventDialog(self)
        dlg._day.setCurrentIndex(day)
        h, m = map(int, time_str.split(":"))
        dlg._start.setTime(QTime(h, m))
        dlg._end.setTime(QTime(h + 1, m))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.event_data
            tt_logic.add_event(**d)
            self._load_events()

    def _on_add_event(self):
        dlg = EventDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.event_data
            tt_logic.add_event(**d)
            self._load_events()

    def _on_event_clicked(self, event: dict):
        menu_dlg = QDialog(self)
        menu_dlg.setWindowTitle(event["title"])
        menu_dlg.setFixedSize(280, 160)
        lay = QVBoxLayout(menu_dlg)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        info = QLabel(f"{event['start_time']} – {event['end_time']}\nType: {event.get('event_type','')}")
        info.setObjectName("mutedLabel")
        lay.addWidget(info)

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(lambda: self._edit_event(event, menu_dlg))
        lay.addWidget(edit_btn)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(lambda: self._delete_event(event["id"], menu_dlg))
        lay.addWidget(del_btn)

        menu_dlg.exec()

    def _edit_event(self, event: dict, parent_dlg: QDialog):
        parent_dlg.accept()
        dlg = EventDialog(self, event=event)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.event_data
            tt_logic.update_event(event["id"], **d)
            self._load_events()

    def _delete_event(self, event_id: int, parent_dlg: QDialog):
        parent_dlg.accept()
        tt_logic.delete_event(event_id)
        self._load_events()

    def _on_export_png(self):
        pixmap = self._grid.grab()
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Timetable", "timetable.png", "PNG Images (*.png)"
        )
        if path:
            pixmap.save(path, "PNG")
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")

    def _check_notifications(self):
        """Fire a system notification for events starting in ~5 minutes."""
        upcoming = tt_logic.get_upcoming_events(window_minutes=6)
        for ev in upcoming:
            try:
                from plyer import notification
                notification.notify(
                    title=f"📅 Starting soon: {ev['title']}",
                    message=f"{ev['start_time']} – {ev['end_time']}  |  {ev.get('subject','')}",
                    app_name="StudyMate",
                    timeout=8,
                )
            except Exception as exc:
                logger.warning("Notification failed: %s", exc)
