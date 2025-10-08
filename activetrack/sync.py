"""Helpers to fetch and store daily Garmin snapshots."""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from typing import Optional

from garminconnect import GarminConnectConnectionError

from .garmin import fetch_overview, fetch_overview_with_session, login_client
from .db import db_session


def _store_snapshot(snapshot_date: str, snapshot: dict[str, object]) -> None:
    """Store a snapshot for the given date, replacing any existing one."""
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO daily_snapshots (snapshot_date, payload)
            VALUES (?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET payload=excluded.payload
            """,
            (snapshot_date, json.dumps(snapshot)),
        )


def run(target_date: Optional[date | str] = None, activity_limit: int = 20) -> None:
    """Fetch and store a snapshot for the given date. Defaults to yesterday."""
    if target_date is None:
        target = date.today() - timedelta(days=1)
    elif isinstance(target_date, str):
        target = date.fromisoformat(target_date)
    else:
        target = target_date

    snapshot_date = target.isoformat()
    snapshot = fetch_overview(target_date=snapshot_date, activity_limit=activity_limit)
    _store_snapshot(snapshot_date, snapshot)


def seed_range(days: int = 7, activity_limit: int = 20) -> None:
    """Fetch and store snapshots for the past number of days."""
    api = login_client()
    try:
        for offset in range(1, days + 1):
            target = date.today() - timedelta(days=offset)
            snapshot_date = target.isoformat()
            try:
                snapshot = fetch_overview_with_session(api, snapshot_date, activity_limit)
            except GarminConnectConnectionError as error:
                if "429" in str(error):
                    time.sleep(60)
                    snapshot = fetch_overview_with_session(api, snapshot_date, activity_limit)
                else:
                    raise
            _store_snapshot(snapshot_date, snapshot)
            time.sleep(2)
    finally:
        try:
            api.logout()
        except Exception:
            pass
