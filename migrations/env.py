"""
migrations/env.py
==================
Alembic environment configuration for StudyMate SQLite database.

Uses the same APPDATA-based DB path as database/db.py so migrations
always target the correct file regardless of working directory.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override URL with resolved APPDATA path (handles Windows env expansion)
_appdata = os.getenv("APPDATA", str(Path.home()))
_db_url = f"sqlite:///{_appdata}/StudyMate/studymate.db"
config.set_main_option("sqlalchemy.url", _db_url)

# ── Logging ───────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # We use raw DDL migrations (not SQLAlchemy ORM models)


def run_migrations_offline() -> None:
    """Run migrations via SQL script output (offline mode)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
