FROM python:3.12-slim

WORKDIR /app

# This file must live at the repo ROOT (not inside apps/api) for two reasons: apps/api depends
# on the sibling packages/audio-engine package (vepair_audio_engine, not published to PyPI), so
# both must be in the build context; and `gcloud run deploy --source .` only auto-detects a
# Dockerfile-based build (vs. falling back to Buildpacks, which can't make sense of a monorepo
# with a Python backend and a Next.js frontend both present) when it finds a file literally
# named "Dockerfile" at the root of --source. Installs audio-engine first since it changes far
# less often than app code, keeping the Docker layer cache useful.
COPY packages/audio-engine /audio-engine
RUN pip install --no-cache-dir /audio-engine

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./

RUN pip install --no-cache-dir .

# Two things done once at build time so a cold start doesn't pay for them: the current migration
# head is recorded (app/startup.py compares it with the database to skip alembic when there is
# nothing to apply), and the app and migration code is compiled to bytecode instead of being
# compiled again by every new container.
RUN alembic heads | cut -d' ' -f1 > /app/alembic_head && python -m compileall -q app migrations

EXPOSE 8000

# Applies any pending migration against DATABASE_URL before the app starts serving traffic —
# previously this was only assumed to happen (see TECHNICAL_GUIDE.md), but nothing in the image
# actually ran it, so schema changes never reached production until run manually. app/startup.py
# runs `alembic upgrade head` only when the database is behind, then starts uvicorn.
CMD ["python", "-m", "app.startup"]
