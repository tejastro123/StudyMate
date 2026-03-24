"""
ui/quiz_ui.py
=============
Quiz module UI for StudyMate.

Features:
- Quiz list panel with create/delete actions
- Question management (add MCQ/TF/Short, CSV import, AI generation)
- Timed quiz runner (30s or 60s per question)
- Score + review screen
- History bar chart via matplotlib
"""

import logging
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QDialog,
    QLineEdit, QTextEdit, QMessageBox, QComboBox, QSpinBox,
    QFileDialog, QRadioButton, QButtonGroup, QProgressBar,
    QScrollArea, QSizePolicy, QStackedWidget, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

import modules.quiz as quiz_logic

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────── Dialogs ──

class CreateQuizDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Quiz")
        self.setFixedSize(360, 180)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Quiz Title"))
        self._title = QLineEdit()
        self._title.setPlaceholderText("e.g. Photosynthesis Quiz")
        layout.addWidget(self._title)

        layout.addWidget(QLabel("Subject (optional)"))
        self._subject = QLineEdit()
        self._subject.setPlaceholderText("e.g. Biology")
        layout.addWidget(self._subject)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Create")
        ok.clicked.connect(lambda: self.accept() if self._title.text().strip() else None)
        row.addWidget(cancel)
        row.addWidget(ok)
        layout.addLayout(row)

    @property
    def title(self): return self._title.text().strip()
    @property
    def subject(self): return self._subject.text().strip()


class AddQuestionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Question")
        self.setFixedSize(480, 400)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Type selector
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(["MCQ (4 options)", "True / False", "Short Answer"])
        self._type_combo.currentIndexChanged.connect(self._on_type_change)
        type_row.addWidget(self._type_combo)
        type_row.addStretch()
        layout.addLayout(type_row)

        layout.addWidget(QLabel("Question"))
        self._question = QTextEdit()
        self._question.setFixedHeight(70)
        layout.addWidget(self._question)

        # MCQ options
        self._mcq_frame = QFrame()
        mcq_layout = QGridLayout(self._mcq_frame)
        mcq_layout.setContentsMargins(0, 0, 0, 0)
        mcq_layout.setSpacing(6)
        self._opt_a = QLineEdit(); self._opt_a.setPlaceholderText("Option A")
        self._opt_b = QLineEdit(); self._opt_b.setPlaceholderText("Option B")
        self._opt_c = QLineEdit(); self._opt_c.setPlaceholderText("Option C")
        self._opt_d = QLineEdit(); self._opt_d.setPlaceholderText("Option D")
        mcq_layout.addWidget(QLabel("A:"), 0, 0); mcq_layout.addWidget(self._opt_a, 0, 1)
        mcq_layout.addWidget(QLabel("B:"), 1, 0); mcq_layout.addWidget(self._opt_b, 1, 1)
        mcq_layout.addWidget(QLabel("C:"), 2, 0); mcq_layout.addWidget(self._opt_c, 2, 1)
        mcq_layout.addWidget(QLabel("D:"), 3, 0); mcq_layout.addWidget(self._opt_d, 3, 1)
        layout.addWidget(self._mcq_frame)

        layout.addWidget(QLabel("Correct Answer"))
        self._correct = QLineEdit()
        self._correct.setPlaceholderText("For MCQ: full option text. For T/F: True or False")
        layout.addWidget(self._correct)

        layout.addWidget(QLabel("Explanation (optional)"))
        self._explanation = QLineEdit()
        layout.addWidget(self._explanation)

        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Add Question")
        save.clicked.connect(self._on_save)
        row.addWidget(cancel)
        row.addWidget(save)
        layout.addLayout(row)

    def _on_type_change(self, idx):
        self._mcq_frame.setVisible(idx == 0)
        if idx == 1:  # True/False
            self._correct.setPlaceholderText("True  or  False")
        elif idx == 2:
            self._correct.setPlaceholderText("Enter the expected short answer")

    def _on_save(self):
        if self._question.toPlainText().strip() and self._correct.text().strip():
            self.accept()

    @property
    def question_text(self): return self._question.toPlainText().strip()
    @property
    def q_type(self):
        idx = self._type_combo.currentIndex()
        return ["mcq", "truefalse", "short"][idx]
    @property
    def option_a(self): return self._opt_a.text().strip()
    @property
    def option_b(self): return self._opt_b.text().strip()
    @property
    def option_c(self): return self._opt_c.text().strip()
    @property
    def option_d(self): return self._opt_d.text().strip()
    @property
    def correct_answer(self): return self._correct.text().strip()
    @property
    def explanation(self): return self._explanation.text().strip()


class AIGenerateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Questions with AI")
        self.setFixedSize(400, 240)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("Topic"))
        self._topic = QLineEdit()
        self._topic.setPlaceholderText("e.g. The French Revolution")
        layout.addWidget(self._topic)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Number of questions:"))
        self._count = QSpinBox()
        self._count.setRange(2, 20)
        self._count.setValue(5)
        row1.addWidget(self._count)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Type:"))
        self._type = QComboBox()
        self._type.addItems(["MCQ", "True/False", "Short Answer"])
        row2.addWidget(self._type)
        row2.addStretch()
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Generate")
        ok.clicked.connect(lambda: self.accept() if self._topic.text().strip() else None)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    @property
    def topic(self): return self._topic.text().strip()
    @property
    def count(self): return self._count.value()
    @property
    def q_type(self):
        return ["mcq", "truefalse", "short"][self._type.currentIndex()]


# ──────────────────────────────────────────────── Quiz Runner ──

class QuizRunner(QWidget):
    """Runs a quiz session, question by question with optional timer."""

    finished = pyqtSignal(int, int, int)  # score, total, time_taken_seconds

    def __init__(self, questions: list[dict], time_per_q: int = 0, parent=None):
        super().__init__(parent)
        self._questions = questions
        self._time_per_q = time_per_q  # 0 = no limit
        self._current = 0
        self._score = 0
        self._start_time = time.time()
        self._q_start = time.time()
        self._results: list[dict] = []
        self._selected: str = ""

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._time_left = time_per_q

        self._build_ui()
        self._show_question()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        self._q_num_lbl = QLabel()
        self._q_num_lbl.setObjectName("sectionTitle")
        hdr.addWidget(self._q_num_lbl)
        hdr.addStretch()
        self._timer_lbl = QLabel()
        self._timer_lbl.setObjectName("accentLabel")
        self._timer_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        hdr.addWidget(self._timer_lbl)
        layout.addLayout(hdr)

        self._progress = QProgressBar()
        layout.addWidget(self._progress)

        # Question
        self._question_lbl = QLabel()
        self._question_lbl.setWordWrap(True)
        self._question_lbl.setFont(QFont("Segoe UI", 15))
        self._question_lbl.setContentsMargins(0, 12, 0, 12)
        layout.addWidget(self._question_lbl)

        # Options container
        self._options_container = QWidget()
        self._options_layout = QVBoxLayout(self._options_container)
        self._options_layout.setSpacing(8)
        layout.addWidget(self._options_container, stretch=1)

        # Short answer
        self._short_input = QLineEdit()
        self._short_input.setPlaceholderText("Type your answer here…")
        self._short_input.setVisible(False)
        layout.addWidget(self._short_input)

        # Action
        self._submit_btn = QPushButton("Submit Answer →")
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

        self._option_buttons: list[QPushButton] = []

    def _clear_options(self):
        while self._options_layout.count():
            item = self._options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._option_buttons.clear()

    def _show_question(self):
        if self._current >= len(self._questions):
            self._finish()
            return

        q = self._questions[self._current]
        self._clear_options()
        self._short_input.setVisible(False)
        self._short_input.clear()
        self._selected = ""
        self._q_start = time.time()

        total = len(self._questions)
        self._q_num_lbl.setText(f"Question {self._current + 1} of {total}")
        self._progress.setMaximum(total)
        self._progress.setValue(self._current)
        self._question_lbl.setText(q["question_text"])

        if q["q_type"] == "mcq":
            for label_char, opt_key in [("A", "option_a"), ("B", "option_b"),
                                         ("C", "option_c"), ("D", "option_d")]:
                text = q.get(opt_key, "")
                if not text:
                    continue
                btn = QPushButton(f"  {label_char}.  {text}")
                btn.setObjectName("secondaryBtn")
                btn.setCheckable(True)
                btn.clicked.connect(lambda _, b=btn, t=text: self._select_option(b, t))
                self._options_layout.addWidget(btn)
                self._option_buttons.append(btn)

        elif q["q_type"] == "truefalse":
            for opt in ["True", "False"]:
                btn = QPushButton(opt)
                btn.setObjectName("secondaryBtn")
                btn.setCheckable(True)
                btn.clicked.connect(lambda _, b=btn, t=opt: self._select_option(b, t))
                self._options_layout.addWidget(btn)
                self._option_buttons.append(btn)

        else:  # short
            self._short_input.setVisible(True)

        # Timer
        if self._time_per_q > 0:
            self._time_left = self._time_per_q
            self._timer.start(1000)
            self._timer_lbl.setText(f"⏱ {self._time_left}s")
        else:
            self._timer_lbl.setText("")

    def _select_option(self, clicked_btn: QPushButton, text: str):
        self._selected = text
        for btn in self._option_buttons:
            btn.setChecked(btn is clicked_btn)

    def _tick(self):
        self._time_left -= 1
        self._timer_lbl.setText(f"⏱ {self._time_left}s")
        if self._time_left <= 0:
            self._timer.stop()
            self._on_submit()

    def _on_submit(self):
        self._timer.stop()
        q = self._questions[self._current]
        if q["q_type"] == "short":
            self._selected = self._short_input.text().strip()

        correct = q["correct_answer"]
        is_correct = self._selected.strip().lower() == correct.strip().lower()
        if is_correct:
            self._score += 1

        self._results.append({
            "question": q["question_text"],
            "your_answer": self._selected,
            "correct": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

        self._current += 1
        self._show_question()

    def _finish(self):
        total_time = int(time.time() - self._start_time)
        self.finished.emit(self._score, len(self._questions), total_time)

    @property
    def results(self):
        return self._results


# ──────────────────────────────────────────────── Score Screen ──

class ScoreScreen(QWidget):
    restart = pyqtSignal()

    def __init__(self, score: int, total: int, time_taken: int, results: list[dict], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        pct = round(100 * score / total) if total else 0
        emoji = "🎉" if pct >= 80 else "👍" if pct >= 50 else "😕"

        header = QLabel(f"{emoji}  Quiz Complete!")
        header.setObjectName("pageTitle")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        score_lbl = QLabel(f"{score} / {total}  ({pct}%)")
        score_lbl.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        score_lbl.setStyleSheet("color: #6C63FF;")
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(score_lbl)

        time_lbl = QLabel(f"Time taken: {time_taken // 60}m {time_taken % 60}s")
        time_lbl.setObjectName("mutedLabel")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(time_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        review_lbl = QLabel("Review")
        review_lbl.setObjectName("sectionTitle")
        layout.addWidget(review_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(8)
        for r in results:
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            icon = "✅" if r["is_correct"] else "❌"
            q_lbl = QLabel(f"{icon}  {r['question']}")
            q_lbl.setWordWrap(True)
            q_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
            cl.addWidget(q_lbl)
            ans_lbl = QLabel(f"Your answer: {r['your_answer'] or '(no answer)'}  |  Correct: {r['correct']}")
            ans_lbl.setObjectName("mutedLabel")
            cl.addWidget(ans_lbl)
            if r.get("explanation"):
                exp_lbl = QLabel(f"💡 {r['explanation']}")
                exp_lbl.setWordWrap(True)
                exp_lbl.setStyleSheet("color: #FFB86C;")
                cl.addWidget(exp_lbl)
            inner_layout.addWidget(card)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        done_btn = QPushButton("← Back to Quizzes")
        done_btn.clicked.connect(self.restart.emit)
        layout.addWidget(done_btn)


# ──────────────────────────────────────────────── History Chart ──

def build_history_chart_widget() -> QWidget:
    """Return a QWidget containing a matplotlib bar chart of quiz history."""
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        attempts = quiz_logic.get_all_attempts_for_chart()
        fig = Figure(figsize=(6, 3), facecolor="#2A2A3E")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#2A2A3E")

        labels = [f"{a['title'][:12]}…" if len(a['title']) > 12 else a['title'] for a in attempts]
        scores = [a["pct"] or 0 for a in attempts]

        colors = ["#50FA7B" if s >= 80 else "#FFB86C" if s >= 50 else "#FF5555" for s in scores]
        bars = ax.bar(range(len(labels)), scores, color=colors, width=0.6)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", color="#9090B0", fontsize=9)
        ax.set_ylim(0, 110)
        ax.set_ylabel("Score %", color="#9090B0")
        ax.tick_params(axis="y", colors="#9090B0")
        for spine in ax.spines.values():
            spine.set_edgecolor("#35355A")
        ax.set_title("Quiz History (recent)", color="#E0E0E0", fontsize=11)
        fig.tight_layout()

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background-color: #2A2A3E; border-radius: 12px;")
        return canvas
    except Exception as exc:
        logger.warning("Could not build chart: %s", exc)
        lbl = QLabel(f"Chart unavailable: {exc}")
        lbl.setObjectName("mutedLabel")
        return lbl


# ──────────────────────────────────────────────── Main Page ──

class QuizPage(QWidget):
    """Top-level Quiz module page."""

    def __init__(self):
        super().__init__()
        self._selected_quiz_id: int | None = None
        self._quizzes: list[dict] = []
        self._runner: QuizRunner | None = None
        self._setup_ui()
        self._load_quizzes()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack)

        # Page 0 – management
        mgmt = QWidget()
        mgmt_layout = QHBoxLayout(mgmt)
        mgmt_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_quiz_list_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([280, 700])
        mgmt_layout.addWidget(splitter)

        self._stack.addWidget(mgmt)
        self._mgmt_widget = mgmt

    def _build_quiz_list_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("sidebar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("📝 Quizzes")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        add_btn = QPushButton("+ New Quiz")
        add_btn.clicked.connect(self._on_create_quiz)
        layout.addWidget(add_btn)

        self._quiz_list = QListWidget()
        self._quiz_list.currentItemChanged.connect(self._on_quiz_selected)
        layout.addWidget(self._quiz_list, stretch=1)

        del_btn = QPushButton("🗑 Delete Quiz")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._on_delete_quiz)
        layout.addWidget(del_btn)

        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        self._quiz_title_lbl = QLabel("Select a quiz")
        self._quiz_title_lbl.setObjectName("pageTitle")
        hdr.addWidget(self._quiz_title_lbl)
        hdr.addStretch()

        self._start_btn = QPushButton("▶ Start Quiz")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start_quiz)
        hdr.addWidget(self._start_btn)
        layout.addLayout(hdr)

        # Timer option row
        timer_row = QHBoxLayout()
        timer_row.addWidget(QLabel("Time per question:"))
        self._timer_combo = QComboBox()
        self._timer_combo.addItems(["No limit", "30 seconds", "60 seconds"])
        timer_row.addWidget(self._timer_combo)
        timer_row.addStretch()

        add_q_btn = QPushButton("+ Add Question")
        add_q_btn.clicked.connect(self._on_add_question)
        timer_row.addWidget(add_q_btn)

        csv_btn = QPushButton("📂 Import CSV")
        csv_btn.setObjectName("secondaryBtn")
        csv_btn.clicked.connect(self._on_import_csv)
        timer_row.addWidget(csv_btn)

        ai_btn = QPushButton("🤖 AI Generate")
        ai_btn.setObjectName("secondaryBtn")
        ai_btn.clicked.connect(self._on_ai_generate)
        timer_row.addWidget(ai_btn)
        layout.addLayout(timer_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._q_list = QListWidget()
        self._q_list.setAlternatingRowColors(True)
        layout.addWidget(self._q_list, stretch=1)

        del_q_row = QHBoxLayout()
        del_q_btn = QPushButton("🗑 Delete Question")
        del_q_btn.setObjectName("dangerBtn")
        del_q_btn.clicked.connect(self._on_delete_question)
        del_q_row.addStretch()
        del_q_row.addWidget(del_q_btn)
        layout.addLayout(del_q_row)

        # History chart (collapsible)
        chart_toggle = QPushButton("📊 Show Quiz History Chart")
        chart_toggle.setObjectName("secondaryBtn")
        chart_toggle.clicked.connect(self._on_show_chart)
        layout.addWidget(chart_toggle)

        return panel

    # ──────────────────────────────────────────── Quiz list ──
    def _load_quizzes(self):
        self._quiz_list.clear()
        self._quizzes = quiz_logic.get_all_quizzes()
        for quiz in self._quizzes:
            label = f"📝 {quiz['title']}  ({quiz['question_count']} Q)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, quiz)
            self._quiz_list.addItem(item)

    def _on_quiz_selected(self, item):
        if not item:
            return
        quiz = item.data(Qt.ItemDataRole.UserRole)
        self._selected_quiz_id = quiz["id"]
        self._quiz_title_lbl.setText(quiz["title"])
        self._start_btn.setEnabled(True)
        self._load_questions()

    def _on_create_quiz(self):
        dlg = CreateQuizDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            quiz_logic.create_quiz(dlg.title, dlg.subject)
            self._load_quizzes()

    def _on_delete_quiz(self):
        if not self._selected_quiz_id:
            return
        reply = QMessageBox.question(
            self, "Delete Quiz", "Delete this quiz and all questions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            quiz_logic.delete_quiz(self._selected_quiz_id)
            self._selected_quiz_id = None
            self._quiz_title_lbl.setText("Select a quiz")
            self._start_btn.setEnabled(False)
            self._q_list.clear()
            self._load_quizzes()

    # ──────────────────────────────────────────── Questions ──
    def _load_questions(self):
        self._q_list.clear()
        if not self._selected_quiz_id:
            return
        for q in quiz_logic.get_questions(self._selected_quiz_id):
            type_tag = {"mcq": "MCQ", "truefalse": "T/F", "short": "Short"}.get(q["q_type"], "?")
            label = f"[{type_tag}]  {q['question_text'][:70]}…" if len(q["question_text"]) > 70 else f"[{type_tag}]  {q['question_text']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, q)
            self._q_list.addItem(item)

    def _on_add_question(self):
        if not self._selected_quiz_id:
            QMessageBox.information(self, "No Quiz", "Please select a quiz first.")
            return
        dlg = AddQuestionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            quiz_logic.add_question(
                self._selected_quiz_id, dlg.question_text, dlg.q_type,
                dlg.correct_answer, dlg.option_a, dlg.option_b, dlg.option_c, dlg.option_d,
                dlg.explanation,
            )
            self._load_questions()
            self._load_quizzes()

    def _on_delete_question(self):
        item = self._q_list.currentItem()
        if not item:
            return
        q = item.data(Qt.ItemDataRole.UserRole)
        quiz_logic.delete_question(q["id"])
        self._load_questions()
        self._load_quizzes()

    def _on_import_csv(self):
        if not self._selected_quiz_id:
            QMessageBox.information(self, "No Quiz", "Select a quiz first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        count, errors = quiz_logic.import_from_csv(self._selected_quiz_id, path)
        msg = f"Imported {count} question(s)."
        if errors:
            msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Import Result", msg)
        self._load_questions()
        self._load_quizzes()

    def _on_ai_generate(self):
        if not self._selected_quiz_id:
            QMessageBox.information(self, "No Quiz", "Select a quiz first.")
            return
        from main import load_config
        cfg = load_config()
        if not cfg.get("api_key"):
            QMessageBox.warning(self, "No API Key", "Please set your Anthropic API key in Settings.")
            return
        dlg = AIGenerateDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            questions = quiz_logic.generate_questions_with_ai(
                cfg["api_key"], dlg.topic, dlg.count, dlg.q_type
            )
            for q in questions:
                quiz_logic.add_question(
                    self._selected_quiz_id,
                    q.get("question", ""),
                    dlg.q_type,
                    q.get("correct_answer", ""),
                    q.get("option_a", ""), q.get("option_b", ""),
                    q.get("option_c", ""), q.get("option_d", ""),
                    q.get("explanation", ""),
                )
            QMessageBox.information(self, "AI Generate", f"Generated {len(questions)} question(s)!")
            self._load_questions()
            self._load_quizzes()
        except Exception as exc:
            QMessageBox.critical(self, "AI Error", str(exc))

    # ──────────────────────────────────────────── Quiz Runner ──
    def _on_start_quiz(self):
        if not self._selected_quiz_id:
            return
        questions = quiz_logic.get_questions(self._selected_quiz_id)
        if not questions:
            QMessageBox.information(self, "No Questions", "Add some questions first.")
            return
        time_map = {"No limit": 0, "30 seconds": 30, "60 seconds": 60}
        time_per_q = time_map.get(self._timer_combo.currentText(), 0)

        self._runner = QuizRunner(questions, time_per_q)
        self._runner.finished.connect(self._on_quiz_finished)
        self._stack.addWidget(self._runner)
        self._stack.setCurrentWidget(self._runner)

    def _on_quiz_finished(self, score: int, total: int, time_taken: int):
        if self._selected_quiz_id:
            quiz_logic.record_attempt(self._selected_quiz_id, score, total, time_taken)
        results = self._runner.results if self._runner else []
        score_screen = ScoreScreen(score, total, time_taken, results)
        score_screen.restart.connect(self._back_to_mgmt)
        self._stack.addWidget(score_screen)
        self._stack.setCurrentWidget(score_screen)

    def _back_to_mgmt(self):
        # Remove all extra widgets
        while self._stack.count() > 1:
            w = self._stack.widget(1)
            self._stack.removeWidget(w)
            w.deleteLater()
        self._stack.setCurrentWidget(self._mgmt_widget)
        self._load_quizzes()

    def _on_show_chart(self):
        chart = build_history_chart_widget()
        dlg = QDialog(self)
        dlg.setWindowTitle("Quiz History")
        dlg.setMinimumSize(700, 350)
        lay = QVBoxLayout(dlg)
        lay.addWidget(chart)
        ok = QPushButton("Close")
        ok.clicked.connect(dlg.accept)
        lay.addWidget(ok)
        dlg.exec()
