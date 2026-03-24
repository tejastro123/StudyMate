# StudyMate 📚 v1.1.0

A **premium, modular, and cloud-synced study platform** for students. StudyMate transforms from a simple productivity tool into an industry-scale application featuring **AI Document Analysis**, **Multi-Device Synchronization**, **Voice Control**, and **Gamified Learning**.

---

## 🚀 Key Features

| Module | New Industry Features |
| :--- | :--- |
| ☁️ **Cloud Sync** | **Offline-First** syncing via Supabase. Data is stored locally in SQLite and synced in the background. |
| 📄 **AI PDF Engine** | Drag-and-drop PDFs (syllabi, readings) to instantly generate **AI Flashcard Decks** or Quizzes. |
| 🎮 **Gamification** | GitHub-style **Study Heatmap**, XP system, and Study Streaks track your daily improvement. |
| 🔊 **Audio Review** | **Text-to-Speech (TTS)** for hands-free flashcard study and **Speech-to-Text (STT)** for AI Assistant control. |
| 🤖 **AI Assistant** | Advanced Claude-powered conversational study buddy with full Markdown & PDF context. |
| ⏱️ **Focus Timer** | Integrated **Ambient Soundscapes** (Lo-Fi, Rain, Cafe) and fullscreen distraction-free mode. |
| 📅 **Calendar & ICS** | Weekly planner with **ICS export** support for Google Calendar and Outlook. |

---

## 🛠️ Technology Stack

- **Core**: Python 3.14+, PyQt6
- **Database**: SQLite (Local) + Supabase (Cloud Sync)
- **Migrations**: Alembic
- **AI**: Anthropic Claude API (messages, document processing)
- **Security**: OS Keyring (Windows Credential Manager) for API Keys and Session Tokens
- **Audio**: `pyttsx3` (TTS), `SpeechRecognition` (STT), `PyQt6-QtMultimedia` (Ambient)
- **PDF**: `PyMuPDF` (Fitz)

---

## 🏁 Setup & Installation

### 1. Prerequisites

- **Python 3.12+**
- **Microsoft C++ Build Tools** (Required for Speech Recognition/STT libraries)

### 2. Installation

```bash
git clone https://github.com/tejastro123/StudyMate.git
cd StudyMate
pip install -r requirements.txt
```

### 3. Run

```bash
python main.py
```

---

## ⚙️ Configuration (Cloud Sync & AI)

1. **AI Assistant**: Get an API key from [Anthropic](https://console.anthropic.com) and add it in **Settings**.
2. **Cloud Sync**: Create a free project on [Supabase](https://supabase.com).
   - Enable **Auth** (Email/Password).
   - Enable **Database** (PostgreSQL/PostgREST).
   - Provide your Project URL and Anon Key in **Settings -> Cloud Sync**.
   - Your credentials are saved **securely** in the Windows Keyring.

---

## 📂 Project Architecture

StudyMate uses a **Modular Service-Based Architecture** (Shim Layer) for scalability:

- `repository/`: Data layer (SQLite operations, sync tracking).
- `services/`: Logic layer (AI processing, Supabase Sync, Audio Manager).
- `models/`: Domain dataclasses and validation.
- `ui/`: PyQt6 presentation layer.
- `database/`: Schema definitions and Alembic migrations.

---

## 📦 Distribution & Build

StudyMate uses **GitHub Actions** to automate production builds. Creating a Git tag (e.g., `v1.1.0`) triggers:

1. **PyInstaller** bundling (Portable EXE).
2. **Inno Setup** compilation (Standalone Windows Installer).
3. Automatic **GitHub Release** creation.

To build manually:

```bash
pyinstaller StudyMate.spec
```

---

## 📜 License

MIT © 2026 StudyMate Team.
