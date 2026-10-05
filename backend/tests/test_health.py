from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_does_not_claim_live_integrations():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "stage": "operations",
        "database_configured": False,
        "auth_configured": False,
    }


def test_unknown_business_endpoint_is_not_available():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.post("/api/v1/appointments", json={}).status_code == 404


def test_untrusted_origin_is_not_allowed():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.options(
            "/api/v1/health",
            headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
        )
    assert "access-control-allow-origin" not in response.headers
