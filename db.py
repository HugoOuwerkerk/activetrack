"""Utility helpers for interacting with the local SQLite database."""

from pathlib import Path
import sqlite3
from contextlib import contextmanager
from typing import Iterator


DB_PATH = Path("data/activetrack.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database, creating directories if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Context manager that yields a connection and commits on success.

    Typical usage patterns:

        # Writing a row
        with db_session() as conn:
            conn.execute(
                "INSERT INTO daily_snapshots (snapshot_date, payload) VALUES (?, ?)",
                ("2025-10-07", json_payload),
            )

        # Reading rows
        with db_session() as conn:
            rows = conn.execute(
                "SELECT snapshot_date, payload FROM daily_snapshots ORDER BY snapshot_date DESC"
            ).fetchall()
    """
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
