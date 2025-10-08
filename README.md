# Activetrack

Activetrack is a small Flask application that pulls your Garmin data and gives you a simple personal dashboard. It fetches yesterday’s snapshot each night, stores the raw JSON in SQLite, and renders a tabbed history so you can flip through recent days.

## Features
- Garmin login helper that normalises daily metrics and recent activities
- SQLite storage with one row per day and automatic upsert on re-sync
- APScheduler job that runs every night at 01:00 (timezone configurable) to fetch the previous day
- Manual endpoints for seeding the last week or clearing cached data
- Lightweight UI with tabs for each stored snapshot

## Requirements
- Python 3.13 (per `pyproject.toml`)
- Poetry for dependency management
- Garmin account credentials with wellness access

## Setup
1. Install dependencies
   ```bash
   poetry install
   ```
2. Create a `.env` file (see below) in the project root.
3. Run the development server
   ```bash
   poetry run flask --app app run --debug
   ```

## Environment variables
```
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-password
FLASK_DEBUG=1             # 1 for local dev, 0 for production
ACTIVETRACK_DB_PATH=data/activetrack.db
SCHEDULER_TIMEZONE=Europe/Berlin   # optional, defaults to UTC
```

## Useful endpoints
- `GET /` – render the dashboard (falls back to live Garmin fetch on cold start)
- `POST /sync` – fetch yesterday and store it immediately
- `POST /seed-week` – log in once, fetch the last seven days, and store each snapshot (backs off if Garmin throttles)
- `DELETE /snapshots` – clear the database

## How the scheduler works
- APScheduler is initialised inside `create_app()`
- The job `nightly_garmin_sync` runs at 01:00 in the configured timezone and calls `run_sync()`
- `run_sync()` always targets `date.today() - timedelta(days=1)` so you get a complete day’s data

## Database
- SQLite database lives at `ACTIVETRACK_DB_PATH` (defaults to `data/activetrack.db`)
- Table: `daily_snapshots`
  - `snapshot_date` TEXT UNIQUE
  - `payload` JSON string containing the full Garmin snapshot
  - `created_at` timestamp with default `CURRENT_TIMESTAMP`
- Unique index ensures repeated syncs update the same row

## Development workflow
1. Start the server (`poetry run flask --app app run --debug`)
2. Trigger seeding if you need historical data (`curl -X POST http://localhost:5000/seed-week`)
3. Open `http://localhost:5000` to browse snapshots
4. When you are done testing, clear the DB with `curl -X DELETE http://localhost:5000/snapshots`

## Deployment notes
- In production run under Gunicorn (for example `gunicorn app:create_app()`)
- Keep `FLASK_DEBUG=0` and store secrets via environment variables or Docker secrets
- Mount the SQLite path as a persistent volume if you use Docker
- Reverse-proxy with HTTPS (nginx/Traefik) in front of the container
