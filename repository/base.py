"""repository/base.py — Abstract base repository."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
import sqlite3

T = TypeVar("T")

ConnectionFactory = sqlite3.Connection  # or Callable[[], Connection]


class BaseRepository(ABC, Generic[T]):
    """
    Base class for all repositories.

    Subclasses receive a *connection factory* callable so that each
    operation uses a fresh connection (keeps SQLite thread-safe) and
    tests can inject an in-memory DB.
    """

    def __init__(self, conn_factory) -> None:
        """
        Parameters
        ----------
        conn_factory: callable returning sqlite3.Connection
            e.g. ``database.db.get_connection``
        """
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        """Open a connection and enable row_factory."""
        conn = self._conn_factory()
        conn.row_factory = sqlite3.Row
        return conn

    def mark_dirty(self, table: str, local_id: int):
        """Mark a row as dirty so the sync service knows to push it."""
        conn = self._conn()
        conn.execute(
            f"UPDATE {table} SET is_dirty = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (local_id,)
        )
        conn.commit()
        conn.close()

    def get_by_remote_id(self, table: str, remote_id: str) -> Optional[dict]:
        """Fetch a single row by its remote UUID."""
        conn = self._conn()
        row = conn.execute(f"SELECT * FROM {table} WHERE remote_id = ?", (remote_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
