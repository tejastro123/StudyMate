"""
ui/timer_ui.py
==============
Focus Timer UI for StudyMate.

Features:
- Pomodoro mode (25/5/15 min) and Custom mode
- Custom QPainter circular countdown arc
- Session counter (🍅 x4 = long break)
- Fullscreen distraction-free mode (hides taskbar via ctypes)
- Windows notification + optional tick sound at end of session
- Daily focus log bar chart (matplotlib, last 7 days)
- Subject tag input per session
"""

import ctypes
import logging
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QFrame, QDialog,
    QSizePolicy, QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

import modules.focus_timer as ft_logic

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────── Circular Timer ──

class CircularTimer(QWidget):
    """
    Custom QPainter widget that draws a circular progress arc.

    remaining_seconds / total_seconds determines the arc extent.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._remaining = 0
        self._total = 1
        self._phase = "work"  # 'work' | 'short_break' | 'long_break'
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_time(self, remaining: int, total: int):
        self._remaining = remaining
        self._total = max(total, 1)
        self.update()

    def set_phase(self, phase: str):
        self._phase = phase
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 20
        x = (w - size) // 2
        y = (h - size) // 2

        # Background circle
        painter.setPen(QPen(QColor("#35355A"), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(x, y, size, size, 0, 360 * 16)

        # Progress arc
        fraction = self._remaining / self._total
        span = int(fraction * 360 * 16)

        phase_colours = {
            "work": "#6C63FF",
            "short_break": "#50FA7B",
            "long_break": "#FFB86C",
        }
        color = QColor(phase_colours.get(self._phase, "#6C63FF"))
        pen = QPen(color, 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(x, y, size, size, 90 * 16, span)

        # Time text
        mins = self._remaining // 60
        secs = self._remaining % 60
        time_str = f"{mins:02d}:{secs:02d}"
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        painter.drawText(x, y, size, size, Qt.AlignmentFlag.AlignCenter, time_str)

        painter.end()


# ─────────────────────────────────────────────────── Fullscreen Widget ──

class FullscreenTimer(QWidget):
    """Distraction-free fullscreen overlay."""
    stop_requested = pyqtSignal()

    def __init__(self, subject: str, phase: str, parent=None):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #0F0F1A;")
        self.showFullScreen()
        self._hide_taskbar()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        subject_lbl = QLabel(f"Studying: {subject}")
        subject_lbl.setFont(QFont("Segoe UI", 16))
        subject_lbl.setStyleSheet("color: #9090B0;")
        subject_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subject_lbl)

        self._timer_widget = CircularTimer()
        self._timer_widget.setFixedSize(300, 300)
        self._timer_widget.set_phase(phase)
        layout.addWidget(self._timer_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        stop_btn = QPushButton("■  Stop & Exit Fullscreen")
        stop_btn.setObjectName("dangerBtn")
        stop_btn.setFixedWidth(240)
        stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(stop_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_time(self, remaining: int, total: int):
        self._timer_widget.set_time(remaining, total)

    def _on_stop(self):
        self._restore_taskbar()
        self.stop_requested.emit()
        self.close()

    def _hide_taskbar(self):
        try:
            SW_HIDE = 0
            hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
            ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
        except Exception as exc:
            logger.warning("Could not hide taskbar: %s", exc)

    def _restore_taskbar(self):
        try:
            SW_SHOW = 5
            hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
        except Exception as exc:
            logger.warning("Could not restore taskbar: %s", exc)

    def closeEvent(self, event):
        self._restore_taskbar()
        super().closeEvent(event)


# ─────────────────────────────────────────────────── Chart Helper ──

def build_daily_chart() -> QWidget:
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        data = ft_logic.get_daily_totals(7)

        fig = Figure(figsize=(6, 3), facecolor="#2A2A3E")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#2A2A3E")

        labels = [d["day"][-5:] for d in data]  # MM-DD
        values = [d["total_minutes"] / 60 for d in data]

        ax.bar(labels, values, color="#6C63FF", width=0.55)
        ax.set_ylabel("Hours", color="#9090B0")
        ax.tick_params(colors="#9090B0")
        for spine in ax.spines.values():
            spine.set_edgecolor("#35355A")
        ax.set_title("Focus Hours (last 7 days)", color="#E0E0E0", fontsize=11)
        fig.tight_layout()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background-color: #2A2A3E; border-radius: 12px;")
        return canvas
    except Exception as exc:
        lbl = QLabel(f"Chart unavailable: {exc}")
        lbl.setObjectName("mutedLabel")
        return lbl


# ─────────────────────────────────────────────────── Main Page ──

class TimerPage(QWidget):
    """Focus Timer page with Pomodoro & custom modes."""

    def __init__(self, cfg: dict = None, save_config_fn=None):
        super().__init__()
        self._cfg = cfg or {}
        self._save_config = save_config_fn

        # Pomodoro state
        self._pomodoro_count = 0       # sessions since last long break
        self._current_phase = "work"
        self._session_type = "pomodoro"
        self._running = False
        self._remaining = 0
        self._total_seconds = 0
        self._work_start_epoch: float = 0.0  # wall-clock start of current work phase

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        self._fullscreen_widget: FullscreenTimer | None = None

        self._setup_ui()
        self._apply_pomodoro_defaults()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Title + mode selector
        hdr = QHBoxLayout()
        title = QLabel("⏱️  Focus Timer")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        hdr.addStretch()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Pomodoro", "Custom"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        hdr.addWidget(self._mode_combo)
        layout.addLayout(hdr)

        # Subject input
        subj_row = QHBoxLayout()
        subj_row.addWidget(QLabel("Studying:"))
        self._subject_input = QLineEdit()
        self._subject_input.setPlaceholderText("e.g. Physics — Chapter 5")
        subj_row.addWidget(self._subject_input, stretch=1)
        layout.addLayout(subj_row)

        # ── Config panel (pomodoro vs custom) ──────────────────────────
        self._config_stack = QStackedWidget()

        # Pomodoro config
        pom_widget = QWidget()
        pom_layout = QHBoxLayout(pom_widget)
        pom_layout.setContentsMargins(0, 0, 0, 0)
        pom_layout.setSpacing(20)
        self._pom_work = self._labeled_spin("Work (min)", 1, 120)
        self._pom_short = self._labeled_spin("Short break (min)", 1, 60)
        self._pom_long = self._labeled_spin("Long break (min)", 1, 60)
        pom_layout.addLayout(self._pom_work[0])
        pom_layout.addLayout(self._pom_short[0])
        pom_layout.addLayout(self._pom_long[0])
        pom_layout.addStretch()
        self._config_stack.addWidget(pom_widget)

        # Custom config
        custom_widget = QWidget()
        custom_layout = QHBoxLayout(custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(20)
        self._custom_work = self._labeled_spin("Duration (min)", 1, 300)
        self._custom_break = self._labeled_spin("Break (min)", 0, 120)
        custom_layout.addLayout(self._custom_work[0])
        custom_layout.addLayout(self._custom_break[0])
        custom_layout.addStretch()
        self._config_stack.addWidget(custom_widget)

        layout.addWidget(self._config_stack)

        # ── Phase indicator ──────────────────────────────────────────
        self._phase_lbl = QLabel("🍅 Session 1 of 4  |  Work")
        self._phase_lbl.setObjectName("sectionTitle")
        self._phase_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._phase_lbl)

        # ── Circular timer ───────────────────────────────────────────
        self._circle = CircularTimer()
        self._circle.setFixedSize(280, 280)
        layout.addWidget(self._circle, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Control buttons ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self._start_btn = QPushButton("▶  Start")
        self._start_btn.setFixedWidth(130)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)

        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.setObjectName("secondaryBtn")
        self._pause_btn.setFixedWidth(130)
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause)
        btn_row.addWidget(self._pause_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("dangerBtn")
        self._stop_btn.setFixedWidth(130)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)

        self._fullscreen_btn = QPushButton("⛶  Fullscreen")
        self._fullscreen_btn.setObjectName("secondaryBtn")
        self._fullscreen_btn.setFixedWidth(130)
        self._fullscreen_btn.clicked.connect(self._on_fullscreen)
        btn_row.addWidget(self._fullscreen_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Ambient audio ────────────────────────────────────────────
        audio_row = QHBoxLayout()
        audio_row.addWidget(QLabel("🎧 Ambient Sound:"))
        self._sound_combo = QComboBox()
        self._sound_combo.addItems(["None", "Lo-Fi Beats", "Rain", "Cafe"])
        self._sound_combo.currentTextChanged.connect(self._on_sound_changed)
        audio_row.addWidget(self._sound_combo)
        audio_row.addStretch()
        
        self._player = None
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._player = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._audio_output.setVolume(0.5)
            self._player.setAudioOutput(self._audio_output)
            # Infinite looping
            self._player.setLoops(QMediaPlayer.Loops.Infinite)
        except ImportError:
            logger.warning("PyQt6.QtMultimedia not installed. Sounds disabled.")
            self._sound_combo.setEnabled(False)
            self._sound_combo.setToolTip("PyQt6-QtMultimedia library missing")
            
        layout.addLayout(audio_row)

        # ── Stats + chart ────────────────────────────────────────────
        stats_row = QHBoxLayout()
        self._today_lbl = QLabel("Focus today: 0m")
        self._today_lbl.setObjectName("mutedLabel")
        stats_row.addWidget(self._today_lbl)
        stats_row.addStretch()

        chart_btn = QPushButton("📊 View Daily Log")
        chart_btn.setObjectName("secondaryBtn")
        chart_btn.clicked.connect(self._on_show_chart)
        stats_row.addWidget(chart_btn)
        layout.addLayout(stats_row)

        layout.addStretch()
        self._refresh_today_label()

    def _labeled_spin(self, label: str, mn: int, mx: int) -> tuple:
        container = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("mutedLabel")
        spin = QSpinBox()
        spin.setRange(mn, mx)
        spin.setFixedWidth(90)
        container.addWidget(lbl)
        container.addWidget(spin)
        return container, spin

    def _apply_pomodoro_defaults(self):
        self._pom_work[1].setValue(self._cfg.get("pomodoro_work", 25))
        self._pom_short[1].setValue(self._cfg.get("pomodoro_short_break", 5))
        self._pom_long[1].setValue(self._cfg.get("pomodoro_long_break", 15))
        self._custom_work[1].setValue(45)
        self._custom_break[1].setValue(10)

    def _on_mode_changed(self, mode: str):
        self._config_stack.setCurrentIndex(0 if mode == "Pomodoro" else 1)
        self._session_type = "pomodoro" if mode == "Pomodoro" else "custom"
        self._reset_display()

    def _on_sound_changed(self, sound_mode: str):
        if not self._player:
            return
        
        from PyQt6.QtCore import QUrl
        import os
        
        self._player.stop()
        if sound_mode == "None":
            return
            
        file_map = {
            "Lo-Fi Beats": "lofi.mp3",
            "Rain": "rain.mp3",
            "Cafe": "cafe.mp3"
        }
        filename = file_map.get(sound_mode)
        if not filename:
            return
            
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", filename))
        if os.path.exists(path):
            self._player.setSource(QUrl.fromLocalFile(path))
        else:
            fallbacks = {
                "Lo-Fi Beats": "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
                "Rain": "https://cdn.pixabay.com/audio/2021/08/09/audio_dc39bde80a.mp3",
                "Cafe": "https://cdn.pixabay.com/audio/2022/03/15/audio_10e057da5e.mp3"
            }
            url = fallbacks.get(sound_mode)
            if url:
                self._player.setSource(QUrl(url))
                
        if self._running:
            self._player.play()

    def _on_start(self):
        if self._running:
            return
        self._running = True
        self._current_phase = "work"
        self._pomodoro_count += 1

        if self._session_type == "pomodoro":
            work_mins = self._pom_work[1].value()
        else:
            work_mins = self._custom_work[1].value()

        self._total_seconds = work_mins * 60
        self._remaining = self._total_seconds
        self._work_start_epoch = __import__('time').time()

        self._circle.set_phase("work")
        self._circle.set_time(self._remaining, self._total_seconds)
        self._update_phase_label()
        
        if self._player and self._sound_combo.currentText() != "None":
            self._player.play()

        self._start_btn.setEnabled(False)
        self._pause_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self._timer.start(1000)

    def _on_pause(self):
        if self._timer.isActive():
            self._timer.stop()
            self._pause_btn.setText("▶  Resume")
            if self._player:
                self._player.pause()
        else:
            self._timer.start(1000)
            self._pause_btn.setText("⏸  Pause")
            if self._player and self._sound_combo.currentText() != "None":
                self._player.play()

    def _on_stop(self):
        """Stop the current session early and record it as incomplete."""
        self._timer.stop()
        if self._player:
            self._player.stop()
        if self._running and self._current_phase == "work" and self._work_start_epoch > 0:
            import time as _time
            elapsed_secs = int(_time.time() - self._work_start_epoch)
            elapsed_mins = max(1, elapsed_secs // 60)
            subject = self._subject_input.text().strip() or "General Study"
            ft_logic.record_session(subject, elapsed_mins, self._session_type, completed=0)
        self._running = False
        self._work_start_epoch = 0.0
        self._reset_display()
        self._refresh_today_label()

    def _tick(self):
        self._remaining -= 1
        self._circle.set_time(self._remaining, self._total_seconds)
        if self._fullscreen_widget:
            self._fullscreen_widget.update_time(self._remaining, self._total_seconds)
        if self._remaining <= 0:
            self._timer.stop()
            if self._player:
                self._player.stop()
            self._on_phase_complete()

    def _on_phase_complete(self):
        subject = self._subject_input.text().strip() or "General Study"

        if self._current_phase == "work":
            # Record completed work session
            work_mins = self._total_seconds // 60
            ft_logic.record_session(subject, work_mins, self._session_type, completed=1)
            self._work_start_epoch = 0.0
            self._refresh_today_label()
            self._notify("\u2705 Work session complete!", f"Time for a break \u2014 great job, {subject}!")

            # Determine next phase
            if self._session_type == "pomodoro":
                if self._pomodoro_count % 4 == 0:
                    self._start_break("long_break")
                else:
                    self._start_break("short_break")
            else:
                self._start_break("short_break")
        else:
            # Break over → ready for next work session
            self._notify("⏱️ Break over!", "Ready to focus again?")
            self._current_phase = "work"
            self._running = False
            self._reset_display()

    def _start_break(self, phase: str):
        self._current_phase = phase
        if self._session_type == "pomodoro":
            mins = self._pom_long[1].value() if phase == "long_break" else self._pom_short[1].value()
        else:
            mins = self._custom_break[1].value() or 5

        self._total_seconds = mins * 60
        self._remaining = self._total_seconds
        self._circle.set_phase(phase)
        self._update_phase_label()
        self._timer.start(1000)

    def _update_phase_label(self):
        phase_names = {"work": "Work 🍅", "short_break": "Short Break ☕", "long_break": "Long Break 🛌"}
        pname = phase_names.get(self._current_phase, "")
        count_info = f"Session {self._pomodoro_count}  |  " if self._session_type == "pomodoro" else ""
        self._phase_lbl.setText(f"{count_info}{pname}")

    def _reset_display(self):
        work_mins = (self._pom_work[1].value()
                     if self._session_type == "pomodoro"
                     else self._custom_work[1].value())
        self._total_seconds = work_mins * 60
        self._remaining = self._total_seconds
        self._circle.set_phase("work")
        self._circle.set_time(self._remaining, self._total_seconds)
        self._phase_lbl.setText("Ready")
        self._start_btn.setEnabled(True)
        self._pause_btn.setEnabled(False)
        self._pause_btn.setText("⏸  Pause")
        self._stop_btn.setEnabled(False)

    def _refresh_today_label(self):
        mins = ft_logic.get_today_total_minutes()
        if mins >= 60:
            self._today_lbl.setText(f"Focus today: {mins//60}h {mins%60}m")
        else:
            self._today_lbl.setText(f"Focus today: {mins}m")

    def _notify(self, title: str, msg: str):
        try:
            from plyer import notification
            notification.notify(title=title, message=msg, app_name="StudyMate", timeout=8)
        except Exception as exc:
            logger.warning("Notification failed: %s", exc)

    def _on_fullscreen(self):
        subject = self._subject_input.text().strip() or "General Study"
        fs = FullscreenTimer(subject, self._current_phase)
        fs.stop_requested.connect(self._on_fullscreen_stop)
        fs.update_time(self._remaining, self._total_seconds)
        self._fullscreen_widget = fs

    def _on_fullscreen_stop(self):
        """Called when user exits fullscreen – stop the timer but DON'T double-record."""
        self._fullscreen_widget = None
        self._timer.stop()
        self._running = False
        self._work_start_epoch = 0.0
        self._reset_display()
        self._refresh_today_label()

    def _on_show_chart(self):
        chart = build_daily_chart()
        dlg = QDialog(self)
        dlg.setWindowTitle("Daily Focus Log")
        dlg.setMinimumSize(680, 360)
        lay = QVBoxLayout(dlg)
        lay.addWidget(chart)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)
        dlg.exec()
