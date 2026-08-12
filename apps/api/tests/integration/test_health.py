from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_and_connected_db() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app_env"] == "development"


def test_health_response_includes_request_id_header() -> None:
    response = client.get("/api/v1/health")
    assert "X-Request-Id" in response.headers
