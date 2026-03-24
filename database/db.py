"""
database/db.py
==============
Central SQLite database manager for StudyMate.

Responsibilities:
- Creates the database file in %APPDATA%/StudyMate/studymate.db
- Initialises all tables on first launch via CREATE TABLE IF NOT EXISTS
- Exposes get_connection() for every other module to use
- Handles lightweight schema migrations (adds missing columns gracefully)
"""

import sqlite3
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Resolve database path
# ──────────────────────────────────────────────────────────────────────────────
_APPDATA = os.getenv("APPDATA", str(Path.home()))
_DB_DIR = Path(_APPDATA) / "StudyMate"
_DB_PATH = _DB_DIR / "studymate.db"

# ──────────────────────────────────────────────────────────────────────────────
# DDL Statements
# ──────────────────────────────────────────────────────────────────────────────
_DDL_STATEMENTS = [
    # --- Flashcards ---
    """
    CREATE TABLE IF NOT EXISTS decks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        subject     TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flashcards (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        deck_id        INTEGER REFERENCES decks(id) ON DELETE CASCADE,
        front          TEXT NOT NULL,
        back           TEXT NOT NULL,
        difficulty     TEXT DEFAULT 'new',
        ease_factor    REAL DEFAULT 2.5,
        interval_days  INTEGER DEFAULT 1,
        due_date       DATE,
        review_count   INTEGER DEFAULT 0,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Quizzes ---
    """
    CREATE TABLE IF NOT EXISTS quizzes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        subject    TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id        INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
        question_text  TEXT NOT NULL,
        q_type         TEXT NOT NULL,
        option_a       TEXT,
        option_b       TEXT,
        option_c       TEXT,
        option_d       TEXT,
        correct_answer TEXT NOT NULL,
        explanation    TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id      INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
        score        INTEGER,
        total        INTEGER,
        pct          INTEGER DEFAULT 0,
        time_seconds INTEGER DEFAULT 0,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Timetable ---
    """
    CREATE TABLE IF NOT EXISTS timetable_events (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        title         TEXT NOT NULL,
        subject       TEXT,
        event_type    TEXT,
        day_of_week   INTEGER,
        start_time    TEXT,
        end_time      TEXT,
        color         TEXT DEFAULT '#6C63FF',
        is_recurring  INTEGER DEFAULT 0,
        specific_date DATE,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Focus Sessions ---
    """
    CREATE TABLE IF NOT EXISTS focus_sessions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        subject          TEXT,
        duration_minutes INTEGER,
        session_type     TEXT,
        completed        INTEGER DEFAULT 1,
        started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- AI Chat ---
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role       TEXT,
        content    TEXT,
        timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Activity Log ---
    """
    CREATE TABLE IF NOT EXISTS activity_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        action      TEXT NOT NULL,
        module      TEXT,
        logged_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- Gamification ---
    """
    CREATE TABLE IF NOT EXISTS study_activity (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        DATE UNIQUE NOT NULL,
        xp          INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0
    )
    """,
]

def _ensure_db_directory() -> None:
    """Create the application data directory if it does not exist."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug("Database directory ensured: %s", _DB_DIR)


def _run_migrations() -> None:
    """Run Alembic migrations programmatically to upgrade the schema."""
    from alembic.config import Config
    from alembic import command
    import sys

    # Determine if running in a PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent

    ini_path = base_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    
    # Needs to know where the script location is (migrations folder)
    alembic_cfg.set_main_option("script_location", str(base_dir / "migrations"))

    logger.info("Running Alembic DB migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations complete.")
    except Exception as exc:
        logger.error("Failed to run migrations: %s", exc)


def initialise_database() -> None:
    """
    Create the database file and apply all DDL statements if new,
    then execute Alembic migrations.
    """
    _ensure_db_directory()
    logger.info("Initialising database at: %s", _DB_PATH)
    
    # We still run initial DDL so the DB is created if it does not exist,
    # but we rely on Alembic to stamp and upgrade.
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Check if this is a brand new DB
    is_new = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchone() is None
    
    for statement in _DDL_STATEMENTS:
        cursor.execute(statement)
    conn.commit()
    conn.close()
    
    # Run the Alembic migrations
    _run_migrations()
    
    # If the database was new, we might need to stamp it to head so Alembic 
    # doesn't try to recreate tables that _DDL_STATEMENTS just created.
    # Actually, Alembic's command.upgrade will just be a no-op if no new migrations,
    # but if alembic_version doesn't exist, it might fail. Let's just stamp it.
    if is_new:
        from alembic.config import Config
        from alembic import command
        import sys
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parent.parent

        alembic_cfg = Config(str(base_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(base_dir / "migrations"))
        command.stamp(alembic_cfg, "head")

    logger.info("Database initialisation complete.")


def get_connection() -> sqlite3.Connection:
    """
    Return a new SQLite connection to the StudyMate database.

    The connection uses ``sqlite3.Row`` as the row factory so that rows
    can be accessed by column name as well as by index.
    """
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def log_activity(action: str, module: str = "") -> None:
    """Append a record to the activity_log table."""
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO activity_log (action, module) VALUES (?, ?)",
            (action, module),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as exc:
        logger.error("Failed to log activity: %s", exc)
