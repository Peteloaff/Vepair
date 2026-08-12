import inspect
import time

import psycopg
import pytest

from app.database import engine


def test_engine_configured_with_connect_timeout() -> None:
    """Guards against the health check hanging when Postgres is unreachable.

    Without an explicit connect_timeout, a dead/unreachable DB host can leave the health
    endpoint hanging far longer than a liveness check should ever take.
    """
    cparams = inspect.getclosurevars(engine.pool._creator).nonlocals["cparams"]
    assert cparams.get("connect_timeout") == 3


def test_unreachable_host_fails_within_timeout() -> None:
    """A connection attempt to a closed port must fail fast, not hang."""
    start = time.monotonic()
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect("postgresql://vepair:vepair@127.0.0.1:5999/vepair", connect_timeout=3)
    elapsed = time.monotonic() - start
    assert elapsed < 10, f"connection attempt took {elapsed:.1f}s, expected a fast failure"
