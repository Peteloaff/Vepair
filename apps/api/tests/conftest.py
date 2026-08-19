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
def signed_up_coach(client, db_session):
    """Signs up a fresh coach account (Stage 12 Phase II) and returns (tokens_json, auth_headers).
    A coach account is a coach account from creation — see app.models.CoachProfile.

    Also activates the new Organization's coach_pro subscription (post-Stage-12 Part 2) so every
    existing test that uses this fixture to exercise coach *functionality* keeps working
    unchanged -- a fresh signup's org otherwise starts is_coach_pro_active=False (no free coach
    tier). Tests of the coach_pro gate itself (test_coach_auth.py) sign up their own account
    directly instead of using this fixture, precisely so they see the unactivated state."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.models import CoachProfile, Organization

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

    coach = db_session.query(CoachProfile).filter_by(user_id=body["user"]["id"]).one()
    org = db_session.query(Organization).filter_by(id=coach.organization_id).one()
    org.is_coach_pro_active = True
    org.coach_pro_period_start = datetime.now(UTC)
    org.coach_pro_period_end = datetime.now(UTC) + timedelta(days=365)
    db_session.commit()

    return {"email": email, "password": password, **body}, headers
