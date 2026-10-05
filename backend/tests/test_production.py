from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app


def production(**changes):
    values = {
        "_env_file": None,
        "environment": "production",
        "database_url": "postgresql+psycopg://levia_app:test-only@localhost/levia_test?sslmode=verify-full",
        "supabase_url": "https://auth.example.com",
        "rate_limit_secret": "test-only-" + "x" * 40,
        "public_web_url": "https://agenda.example.com",
        "allowed_hosts": ["agenda.example.com", "127.0.0.1"],
        "cors_origins": ["https://agenda.example.com"],
    }
    return Settings(**(values | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"allowed_hosts": ["*"]},
        {"allowed_hosts": []},
        {"cors_origins": ["https://agenda.example.com/path"]},
        {"cors_origins": []},
        {"public_web_url": "http://agenda.example.com"},
        {"migration_database_url": "postgresql+psycopg://localhost/levia_test"},
        {"database_url": "postgresql+psycopg://localhost/levia_test?sslmode=require"},
    ],
)
def test_reject_unsafe_production_configuration(changes):
    with pytest.raises(ValidationError):
        production(**changes)


def test_production_hides_schema_and_rejects_unknown_hosts():
    # No lifespan/DB connection: tests public HTTP configuration only.
    client = TestClient(create_app(production()), base_url="https://agenda.example.com")
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health", headers={"Host": "attacker.example.com"}).status_code == 400


def test_readiness_checks_database_and_hides_failure_details():
    app = create_app(Settings(_env_file=None))
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 503

    @contextmanager
    def connected():
        yield SimpleNamespace(execute=lambda query: 1)

    app.state.engine = SimpleNamespace(connect=connected)
    assert client.get("/api/v1/ready").json() == {"status": "ready"}

    def unavailable():
        raise OperationalError("SELECT 1", {}, Exception("private database details"))

    app.state.engine = SimpleNamespace(connect=unavailable)
    response = client.get("/api/v1/ready")
    assert response.status_code == 503 and response.json() == {"status": "unavailable"}
