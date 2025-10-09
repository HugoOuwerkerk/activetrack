import json
import os
from datetime import date
from flask import Flask, jsonify, render_template
from flask_apscheduler import APScheduler
from activetrack.db import delete_all_snapshots, fetch_snapshots, get_connection
from activetrack import fetch_overview
from activetrack.sync import run as run_sync, seed_range


scheduler = APScheduler()

def ensure_database() -> None:
    """Create the placeholder table if needed."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL UNIQUE,
                payload JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_snapshots_date
            ON daily_snapshots(snapshot_date)
            """
        )


def create_app() -> Flask:
    ensure_database()

    app = Flask(__name__)
    app.config.update(
        DEBUG=os.getenv("FLASK_DEBUG", "0") == "1",
        SCHEDULER_TIMEZONE=os.getenv("SCHEDULER_TIMEZONE") or "UTC",
    )

    scheduler.init_app(app)
    if not scheduler.get_job("nightly_garmin_sync"):
        scheduler.add_job(
            id="nightly_garmin_sync",
            func=run_sync,
            trigger="cron",
            hour=1,
            minute=0,
        )
    if not scheduler.running:
        scheduler.start()

    @app.get("/")
    def index() -> str:
        rows = fetch_snapshots()
        snapshots = []

        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except (TypeError, json.JSONDecodeError):
                continue

            snapshots.append(
                {
                    "snapshot_date": row["snapshot_date"],
                    "full_name": payload.get("full_name", "Activetrack"),
                    "daily_metrics": payload.get("daily_metrics", []),
                    "activity_groups": payload.get("activity_groups", {}),
                }
            )

        if snapshots:
            latest = snapshots[0]

            return render_template(
                "index.html",
                full_name=latest["full_name"],
                daily_metrics=latest["daily_metrics"],
                activity_groups=latest["activity_groups"],
                error_message=None,
                snapshots=snapshots,
            )

        try:
            overview = fetch_overview()
            live_snapshot = {
                "snapshot_date": date.today().isoformat(),
                "full_name": overview["full_name"],
                "daily_metrics": overview["daily_metrics"],
                "activity_groups": overview["activity_groups"],
            }
            return render_template(
                "index.html",
                full_name=overview["full_name"],
                daily_metrics=overview["daily_metrics"],
                activity_groups=overview["activity_groups"],
                error_message="Showing live data — no cached snapshots yet.",
                snapshots=[live_snapshot],
            )
        except Exception as error:  # pragma: no cover - surface error to UI
            return (
                render_template(
                    "index.html",
                    full_name="Activetrack",
                    daily_metrics=[],
                    activity_groups={},
                    error_message=str(error),
                    snapshots=[],
                ),
                500,
            )



    @app.post("/sync")
    def sync_now() -> tuple[dict[str, str], int]:
        run_sync()
        return jsonify(status="ok"), 200

    @app.post("/seed-week")
    def seed_week() -> tuple[dict[str, str], int]:
        seed_range(days=7)
        return jsonify(status="seeded"), 200

    @app.delete("/snapshots")
    def clear_snapshots() -> tuple[dict[str, str], int]:
        delete_all_snapshots()
        return jsonify(status="cleared"), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
