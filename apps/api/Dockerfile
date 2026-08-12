FROM python:3.12-slim

WORKDIR /app

# Build context is the monorepo ROOT (see docker-compose.yml / deploy instructions), not
# apps/api — apps/api depends on the sibling packages/audio-engine package (vepair_audio_engine,
# not published to PyPI), so both must be in the build context. Installed first since it changes
# far less often than app code, keeping the Docker layer cache useful.
COPY packages/audio-engine /audio-engine
RUN pip install --no-cache-dir /audio-engine

COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
