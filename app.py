from flask import Flask, jsonify, render_template

from db import get_connection
from activetrack import fetch_overview


def ensure_database() -> None:
    """Create the placeholder table if needed."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                payload JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_app() -> Flask:
    ensure_database()

    app = Flask(__name__)

    @app.get("/health")
    def healthcheck() -> tuple[dict[str, str], int]:
        """for verify the container is alive."""
        return jsonify(status="ok"), 200

    @app.get("/")
    def index() -> str:
        try:
            overview = fetch_overview()
        except Exception as error:
            return (
                render_template(
                    "index.html",
                    full_name="Activetrack",
                    daily_metrics=[],
                    activity_groups={},
                    error_message=str(error),
                ),
                500,
            )

        return render_template(
            "index.html",
            full_name=overview["full_name"],
            daily_metrics=overview["daily_metrics"],
            activity_groups=overview["activity_groups"],
            error_message=None,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
