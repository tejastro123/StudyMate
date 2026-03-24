"""baseline schema

Revision ID: e12683b61c21
Revises: 
Create Date: 2026-03-24 01:33:19.474486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e12683b61c21'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Flashcards ---
    op.execute('''
    CREATE TABLE IF NOT EXISTS decks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        subject     TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    op.execute('''
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
    ''')
    # --- Quizzes ---
    op.execute('''
    CREATE TABLE IF NOT EXISTS quizzes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        subject    TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    op.execute('''
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
    ''')
    op.execute('''
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id      INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
        score        INTEGER,
        total        INTEGER,
        pct          INTEGER DEFAULT 0,
        time_seconds INTEGER DEFAULT 0,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # --- Timetable ---
    op.execute('''
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
    ''')
    # --- Focus Sessions ---
    op.execute('''
    CREATE TABLE IF NOT EXISTS focus_sessions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        subject          TEXT,
        duration_minutes INTEGER,
        session_type     TEXT,
        completed        INTEGER DEFAULT 1,
        started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # --- AI Chat ---
    op.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    op.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role       TEXT,
        content    TEXT,
        timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # --- Activity Log ---
    op.execute('''
    CREATE TABLE IF NOT EXISTS activity_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        action      TEXT NOT NULL,
        module      TEXT,
        logged_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('activity_log')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('focus_sessions')
    op.drop_table('timetable_events')
    op.drop_table('quiz_attempts')
    op.drop_table('questions')
    op.drop_table('quizzes')
    op.drop_table('flashcards')
    op.drop_table('decks')
