import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import engine as app_engine
from app.database import get_db
from app.main import app


@pytest.fixture()
def db_session():
    """A session bound to a single connection/transaction, rolled back after the test.

    Uses SQLAlchemy's savepoint-based external-transaction pattern so that `db.commit()`
    calls inside route handlers don't escape the test's rollback boundary.
    """
    connection = app_engine.connect()
    trans = connection.begin()
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def signed_up_user(client):
    """Signs up a fresh user and returns (tokens_json, auth_headers)."""
    import uuid

    email = f"test_{uuid.uuid4().hex[:12]}@example.com"
    password = "correcthorse123"
    resp = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return {"email": email, "password": password, **body}, headers


@pytest.fixture()
def signed_up_coach(client):
    """Signs up a fresh coach account (Stage 12 Phase II) and returns (tokens_json, auth_headers).
    A coach account is a coach account from creation — see app.models.CoachProfile."""
    import uuid

    email = f"coach_{uuid.uuid4().hex[:12]}@example.com"
    password = "correcthorse123"
    resp = client.post(
        "/api/v1/auth/coach-signup",
        json={
            "email": email,
            "password": password,
            "display_name": "Test Coach",
            "studio_name": "Test Studio",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return {"email": email, "password": password, **body}, headers
