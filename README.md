# StudyMate 📚

A **production-ready student productivity desktop application** built with Python, PyQt6, and SQLite — featuring flashcards, quizzes, a weekly timetable, Pomodoro focus timer, and an AI study assistant powered by Anthropic Claude.

---

## Features

| Module | Highlights |
| 🏠 **Dashboard** | Live stats cards, motivational quote, recent activity, quick-access buttons |
| 📇 **Flashcards** | Decks + cards, flip animation, spaced-repetition (Easy/Medium/Hard) |
| 📝 **Quizzes** | MCQ / True-False / Short Answer, timed mode, CSV import, AI generation, bar chart history |
| 📅 **Timetable** | Weekly grid (Mon–Sun, 6 AM–10 PM), colour-coded events, recurring events, PNG export, plyer notifications |
| ⏱️ **Focus Timer** | Pomodoro & custom mode, custom QPainter circular arc, fullscreen mode (hides taskbar), daily focus chart |
| 🤖 **AI Assistant** | Claude-powered chat, quick actions, markdown rendering, session history |
| ⚙️ **Settings** | API key management, theme toggle, Pomodoro defaults, ZIP backup/restore, clear all data |

---

## Requirements

- **Python 3.11+**
- **Windows 10 / 11**

---

## Setup

### 1. Clone / Download

```bash
git clone <your-repo>
cd StudyMate/studymate
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

The database is automatically created at:

```bash
%APPDATA%\StudyMate\studymate.db
```

---

## AI Assistant Setup

1. Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.
2. Open StudyMate → **Settings** → paste your key into the **API Key** field → click **Save**.

Your key is stored locally in `%APPDATA%\StudyMate\config.json` and is never sent anywhere except the Anthropic API.

---

## Project Structure

```bash
studymate/
├── main.py                 # Entry point
├── requirements.txt
├── README.md
├── assets/icons/           # Emoji fallbacks used — no external icons needed
├── database/
│   ├── __init__.py
│   └── db.py               # SQLite manager (init, migrations, get_connection)
├── modules/
│   ├── flashcards.py       # Deck & card CRUD + spaced repetition
│   ├── quiz.py             # Quiz CRUD, CSV import, AI generation
│   ├── timetable.py        # Event CRUD + notification helpers
│   ├── focus_timer.py      # Session recording + daily stats
│   └── ai_assistant.py     # Claude API, session/message persistence, markdown→HTML
├── ui/
│   ├── main_window.py      # Sidebar + QStackedWidget shell
│   ├── dashboard_ui.py
│   ├── flashcard_ui.py     # Flip card animation + study mode
│   ├── quiz_ui.py          # Quiz runner + score screen + chart
│   ├── timetable_ui.py     # Weekly grid + slot-click event creation
│   ├── timer_ui.py         # QPainter circular timer + fullscreen overlay
│   ├── assistant_ui.py     # Chat bubbles + background API worker
│   └── settings_ui.py      # Config, theme, data management
└── styles/
    └── theme.qss           # Global dark theme (+ light mode override)
```

---

## Packaging (Windows EXE)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name StudyMate main.py
```

The resulting `StudyMate.exe` will be in the `dist/` folder.

> **Note:** You may need to add `--add-data "styles;styles"` to include the QSS file, and similarly for any additional assets.

---

## Data Backup & Restore

Go to **Settings → Data Management**:

- **Export Backup** — saves `studymate.db` + `config.json` as a `.zip` archive.
- **Import Backup** — restores from a `.zip` archive (restart required).

---

## Tech Stack

| Library | Version | Purpose |
| PyQt6 | ≥ 6.6 | UI framework |
| anthropic | ≥ 0.25 | Claude AI API |
| plyer | ≥ 2.1 | Windows notifications |
| matplotlib | ≥ 3.8 | Embedded bar charts |
| sqlite3 | built-in | Local database |

---

## License

MIT — free to use, modify, and distribute.
