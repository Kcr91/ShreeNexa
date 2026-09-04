"""Test CORS configuration on the FastAPI application (QA-08)."""

from app.main import app
from fastapi.testclient import TestClient


def test_cors_preflight_for_dev_frontend() -> None:
    client = TestClient(app)
    response = client.options(
        "/api/v1/dhan/token-health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_get_with_origin_sets_credentials_header() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/v1/dhan/token-health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
