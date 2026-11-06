"""The container entrypoint skips `alembic upgrade head` only when it is certain the database is
already at the head the image was built with; every other case must fall through to alembic."""

import sys
import types

import pytest

from app import startup


@pytest.fixture()
def head_file(tmp_path, monkeypatch):
    path = tmp_path / "alembic_head"
    monkeypatch.setattr(startup, "HEAD_FILE", str(path))
    return path


def _fake_psycopg(monkeypatch, rows=None, error=None):
    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql):
            return types.SimpleNamespace(fetchall=lambda: rows)

    def connect(url, connect_timeout):
        if error is not None:
            raise error
        connect.url = url
        return Conn()

    monkeypatch.setitem(sys.modules, "psycopg", types.SimpleNamespace(connect=connect))
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host:5432/db")
    return connect


def test_skips_alembic_when_the_database_is_at_the_recorded_head(head_file, monkeypatch) -> None:
    head_file.write_text("abc123\n")
    connect = _fake_psycopg(monkeypatch, rows=[("abc123",)])
    assert startup.database_at_head() is True
    assert connect.url == "postgresql://u:p@host:5432/db"  # SQLAlchemy's driver suffix removed


def test_runs_alembic_when_the_database_is_behind(head_file, monkeypatch) -> None:
    head_file.write_text("abc123\n")
    _fake_psycopg(monkeypatch, rows=[("older",)])
    assert startup.database_at_head() is False


def test_runs_alembic_when_the_database_cannot_be_read(head_file, monkeypatch) -> None:
    head_file.write_text("abc123\n")
    _fake_psycopg(monkeypatch, error=RuntimeError("no such table: alembic_version"))
    assert startup.database_at_head() is False


def test_runs_alembic_when_the_head_was_not_recorded(head_file, monkeypatch) -> None:
    _fake_psycopg(monkeypatch, rows=[("abc123",)])
    assert startup.database_at_head() is False  # no head file at all
    head_file.write_text("")
    assert startup.database_at_head() is False


def test_runs_alembic_when_the_migrations_have_forked(head_file, monkeypatch) -> None:
    head_file.write_text("abc123\ndef456\n")
    _fake_psycopg(monkeypatch, rows=[("abc123",)])
    assert startup.database_at_head() is False
