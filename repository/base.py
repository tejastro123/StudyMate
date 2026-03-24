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
