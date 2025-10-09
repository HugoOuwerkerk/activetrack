"""Utility helpers for interacting with the local SQLite database."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator, Optional

from dotenv import load_dotenv


load_dotenv()

DEFAULT_DB_PATH = Path("data/activetrack.db")
DB_PATH = Path(os.getenv("ACTIVETRACK_DB_PATH") or DEFAULT_DB_PATH).expanduser()


def get_connection() -> sqlite3.Connection:
    """
    Return a connection to the SQLite database, creating directories if needed.
    """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Context manager that yields a connection and commits on success.

    usage:

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


def fetch_latest_snapshot() -> Optional[sqlite3.Row]:
    """Return the most recent snapshot row, or ``None`` when missing."""

    with db_session() as connection:
        row = connection.execute(
            """
            SELECT snapshot_date, payload
            FROM daily_snapshots
            ORDER BY snapshot_date DESC
            LIMIT 1
            """
        ).fetchone()
    return row

def fetch_snapshots(limit: int | None = None) -> list[sqlite3.Row]:
    """Return a list of stored snapshots, most recent first."""
    query = (
        "SELECT snapshot_date, payload FROM daily_snapshots "
        "ORDER BY snapshot_date DESC"
    )
    if limit is not None:
        query += " LIMIT ?"

    with db_session() as connection:
        return connection.execute(query, (limit,) if limit is not None else ()).fetchall()


def delete_all_snapshots() -> None:
    """Remove every stored snapshot."""
    with db_session() as connection:
        connection.execute("DELETE FROM daily_snapshots")
