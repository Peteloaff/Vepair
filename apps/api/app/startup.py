"""Container entrypoint (`python -m app.startup`): apply pending migrations only if the database is
behind, then serve.

`alembic upgrade head` imports alembic, SQLAlchemy and the whole model layer and loads every
migration script just to discover there is nothing to do, which is seconds of waiting on every
cold start of the service. Here one small query compares the database's current revision with the
head revision recorded in the image at build time (see the Dockerfile). Any doubt -- no recorded
head, no alembic_version table, a connection error, a mismatch -- falls back to the real
`alembic upgrade head`, so a pending migration is never skipped by mistake.

Deliberately imports nothing from the rest of the app, so this step stays cheap."""

import os
import subprocess
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD_FILE = os.path.join(_APP_ROOT, "alembic_head")


def recorded_head() -> str | None:
    try:
        with open(HEAD_FILE, encoding="utf-8") as f:
            value = f.read().strip()
    except OSError:
        return None
    # One revision id per head; more than one means the migrations have forked and the real
    # upgrade (which refuses to run on a fork) should decide what happens.
    return value if value and len(value.split()) == 1 else None


def database_at_head() -> bool:
    head = recorded_head()
    if head is None:
        return False
    try:
        import psycopg

        url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(url, connect_timeout=10) as conn:
            rows = conn.execute("select version_num from alembic_version").fetchall()
    except Exception:
        return False
    return [row[0] for row in rows] == [head]


def main() -> None:
    if database_at_head():
        print("Database is already at the latest migration; skipping alembic.", flush=True)
    else:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    port = os.environ.get("PORT", "8000")
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port],
    )


if __name__ == "__main__":
    main()
