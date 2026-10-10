"""Opt-in integration tests: use only the dedicated local levia_test database."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import DBAPIError

from app.auth import current_user
from app.core.config import Settings
from app.database import check_runtime_role, make_engine
from app.main import create_app
from app.security import consume_limit

ADMIN_URL = os.environ.get("LEVIA_TEST_ADMIN_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL de teste não configurado")


@pytest.fixture(scope="module")
def database():
    url = make_url(ADMIN_URL)
    if url.host not in ("127.0.0.1", "localhost") or url.database != "levia_test":
        pytest.fail("Testes exigem o banco local exclusivo levia_test")
    if os.environ.get("LEVIA_TEST_ALLOW_RESET") != "1":
        pytest.fail("Defina LEVIA_TEST_ALLOW_RESET=1 apenas no banco descartável")
    admin = create_engine(url, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(
            text("""DO $$ DECLARE role_name text; BEGIN
          FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname=role_name) THEN
              EXECUTE format('CREATE ROLE %I NOLOGIN', role_name);
            END IF;
          END LOOP;
        END $$""")
        )
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    os.environ["LEVIA_MIGRATION_DATABASE_URL"] = ADMIN_URL
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    password = uuid4().hex  # disposable, isolated test role only
    with admin.begin() as connection:
        raw = connection.connection.driver_connection
        raw.execute(sql.SQL("ALTER ROLE levia_app LOGIN PASSWORD {}").format(sql.Literal(password)))
    runtime_url = url.set(username="levia_app", password=password).render_as_string(
        hide_password=False
    )
    engine = make_engine(runtime_url)
    check_runtime_role(engine)
    yield SimpleNamespace(admin=admin, engine=engine, url=SecretStr(runtime_url))
    engine.dispose()
    admin.dispose()
    os.environ.pop("LEVIA_MIGRATION_DATABASE_URL", None)


def client_for(database, user, limit=600):
    settings = Settings(
        _env_file=None,
        database_url=database.url,
        rate_limit_secret="unit-test-only-" + "x" * 32,
        rate_limit_per_minute=limit,
    )
    app = create_app(settings)
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def sample_profile(name="Ana"):
    return {
        "name": name,
        "studio_name": "Studio " + name,
        "phone": "65999999999",
        "specialties": ["Unhas", "Cílios"],
        "working_periods": [
            {"weekday": 0, "starts_at": "09:00", "ends_at": "12:00"},
            {"weekday": 0, "starts_at": "13:00", "ends_at": "18:00"},
        ],
    }


def test_api_persists_and_scopes_profiles(database):
    alice, bob = uuid4(), uuid4()
    with client_for(database, alice) as a, client_for(database, bob) as b:
        assert a.get("/api/v1/me").status_code == 404
        saved = a.put("/api/v1/me", json=sample_profile())
        assert saved.status_code == 200, saved.text
        alice_id = saved.json()["id"]
        assert b.get("/api/v1/me").status_code == 404
        assert b.put("/api/v1/me", json=sample_profile("Bia")).status_code == 200
        assert a.get("/api/v1/me").json()["name"] == "Ana"
        assert b.get("/api/v1/me").json()["name"] == "Bia"
        assert len(a.get("/api/v1/me").json()["working_periods"]) == 2
        assert (
            b.put("/api/v1/me", json={**sample_profile(), "owner_id": str(alice)}).status_code
            == 422
        )
        assert b.get(f"/api/v1/me/{alice_id}").status_code == 404
        updated = a.put("/api/v1/me", json=sample_profile("Ana Nova"))
        assert updated.json()["id"] == alice_id
        assert a.get("/api/v1/me").json()["name"] == "Ana Nova"


def test_rls_blocks_cross_tenant_sql_and_resets_pool_context(database):
    alice, bob = uuid4(), uuid4()
    with client_for(database, alice) as a:
        tenant = a.put("/api/v1/me", json=sample_profile()).json()["id"]
    with database.engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM levia.professionals")) == 0
        connection.execute(text("SELECT set_config('levia.user_id', :id, true)"), {"id": str(bob)})
        assert (
            connection.scalar(
                text("SELECT count(*) FROM levia.professionals WHERE id=:id"), {"id": tenant}
            )
            == 0
        )
        assert (
            connection.scalar(
                text("SELECT count(*) FROM levia.working_periods WHERE tenant_id=:id"),
                {"id": tenant},
            )
            == 0
        )
        changed = connection.execute(
            text("UPDATE levia.professionals SET name='Intruso' WHERE id=:id"), {"id": tenant}
        )
        assert changed.rowcount == 0
        deleted = connection.execute(
            text("DELETE FROM levia.working_periods WHERE tenant_id=:id"), {"id": tenant}
        )
        assert deleted.rowcount == 0
    with pytest.raises(DBAPIError), database.engine.begin() as connection:
        connection.execute(text("SELECT set_config('levia.user_id', :id, true)"), {"id": str(bob)})
        connection.execute(
            text("""INSERT INTO levia.working_periods
            (id, tenant_id, weekday, starts_at, ends_at) VALUES (:id, :tenant, 1, '09:00', '10:00')"""),
            {"id": str(uuid4()), "tenant": tenant},
        )
    with database.engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM levia.professionals")) == 0


def test_runtime_rejects_admin_role(database):
    with pytest.raises(RuntimeError):
        check_runtime_role(database.admin)


def test_supabase_api_roles_have_no_schema_access(database):
    with database.admin.connect() as connection:
        for role in ("anon", "authenticated", "service_role"):
            assert not connection.scalar(
                text("SELECT has_schema_privilege(:role, 'levia', 'USAGE')"), {"role": role}
            )


def test_http_rate_limit_cannot_be_bypassed_with_forwarded_header(database):
    app = create_app(
        Settings(
            _env_file=None,
            database_url=database.url,
            rate_limit_secret=uuid4().hex,
            rate_limit_per_minute=1,
        )
    )
    app.dependency_overrides[current_user] = lambda: uuid4()
    with TestClient(app) as client:
        assert client.get("/api/v1/me").status_code == 404
        response = client.get("/api/v1/me", headers={"X-Forwarded-For": "8.8.8.8"})
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"


def test_owner_identity_is_immutable_for_runtime_role(database):
    user = uuid4()
    with client_for(database, user) as client:
        tenant = client.put("/api/v1/me", json=sample_profile()).json()["id"]
    with pytest.raises(DBAPIError), database.engine.begin() as connection:
        connection.execute(text("SELECT set_config('levia.user_id', :id, true)"), {"id": str(user)})
        connection.execute(
            text("UPDATE levia.professionals SET owner_id=:other WHERE id=:tenant"),
            {"other": str(uuid4()), "tenant": tenant},
        )


def test_shared_rate_counter_is_atomic(database):
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(
            pool.map(lambda _: consume_limit(database.engine, "test-secret", key, 5), range(15))
        )
    assert sum(results) == 5


def test_authenticated_response_reports_database_timing_without_identity(database):
    user = uuid4()
    with client_for(database, user) as client:
        client.put("/api/v1/me", json=sample_profile())
        response = client.get("/api/v1/me", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    timing = response.headers["server-timing"]
    for metric in ("app", "ip_limit", "user_limit", "db_connect", "tenant_context", "sql"):
        assert metric + ";dur=" in timing
    assert str(user) not in timing
    assert "Server-Timing" in response.headers["access-control-expose-headers"]


def test_concurrent_onboarding_does_not_duplicate_profiles(database):
    user = uuid4()

    def save(_):
        with client_for(database, user) as client:
            return client.put("/api/v1/me", json=sample_profile())

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(save, range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert len({r.json()["id"] for r in responses}) == 1
    with client_for(database, user) as client:
        assert len(client.get("/api/v1/me").json()["working_periods"]) == 2


def test_profile_validation_is_atomic(database):
    with client_for(database, uuid4()) as client:
        assert client.put("/api/v1/me", json=sample_profile()).status_code == 200
        invalid = sample_profile("Outro")
        invalid["working_periods"].append({"weekday": 0, "starts_at": "11:00", "ends_at": "14:00"})
        assert client.put("/api/v1/me", json=invalid).status_code == 422
        assert client.get("/api/v1/me").json()["name"] == "Ana"


def test_logo_persists_is_isolated_and_profile_save_preserves_it(database):
    source = BytesIO()
    Image.new("RGBA", (24, 24), "red").save(source, format="PNG")
    with client_for(database, uuid4()) as a, client_for(database, uuid4()) as b:
        a.put("/api/v1/me", json=sample_profile())
        b.put("/api/v1/me", json=sample_profile("Bia"))
        result = a.put("/api/v1/me/logo", content=source.getvalue())
        assert result.status_code == 200, result.text
        logo = result.json()["logo"]
        assert logo.startswith("data:image/png;base64,")
        assert a.get("/api/v1/me").json()["logo"] == logo
        assert b.get("/api/v1/me").json()["logo"] is None
        assert b.delete("/api/v1/me/logo").status_code == 200
        assert a.put("/api/v1/me", json=sample_profile("Novo nome")).json()["logo"] == logo
        assert a.put("/api/v1/me/logo", content=b"invalid").status_code == 422
        assert a.get("/api/v1/me").json()["logo"] == logo
        assert a.put("/api/v1/me/logo", content=b"x" * (2 * 1024 * 1024 + 1)).status_code == 413
        assert a.delete("/api/v1/me/logo").json()["logo"] is None
        assert a.get("/api/v1/me").json()["logo"] is None


def test_catalog_and_availability_are_tenant_scoped(database):
    alice, bob = uuid4(), uuid4()
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    profile = sample_profile()
    profile["timezone"] = "America/Cuiaba"
    profile["working_periods"] = [
        {"weekday": day.weekday(), "starts_at": "09:00", "ends_at": "12:00"}
    ]
    payload = {"name": "Manicure", "price_cents": 3500, "duration_minutes": 45, "return_days": 14}
    with client_for(database, alice) as a, client_for(database, bob) as b:
        tenant = a.put("/api/v1/me", json=profile).json()["id"]
        foreign = b.put("/api/v1/me", json=profile).json()["id"]
        first = a.post("/api/v1/me/services", json=payload)
        assert first.status_code == 201, first.text
        first_id = first.json()["id"]
        second_id = a.post("/api/v1/me/services", json={**payload, "name": "Pedicure"}).json()["id"]
        assert a.get("/api/v1/me/services?limit=1").json()["total"] == 2
        assert b.get("/api/v1/me/services").json()["items"] == []
        assert b.put(f"/api/v1/me/services/{first_id}", json=payload).status_code == 404
        assert (
            a.post("/api/v1/me/services", json={**payload, "price_cents": 1.5}).status_code == 422
        )
        assert (
            a.post("/api/v1/me/services", json={**payload, "tenant_id": foreign}).status_code == 422
        )
        assert a.get("/api/v1/me/service-suggestions").json()
        query = {"day": str(day), "service_ids": [first_id, second_id]}
        result = a.post("/api/v1/me/availability", json=query)
        assert result.status_code == 200, result.text
        assert result.json()["duration_minutes"] == 90
        assert result.json()["price_cents"] == 7000
        assert len(result.json()["slots"]) == 7
        assert b.post("/api/v1/me/availability", json=query).status_code == 404
        assert (
            a.post(
                "/api/v1/me/availability", json={**query, "service_ids": [first_id, first_id]}
            ).status_code
            == 422
        )
        assert (
            a.post(
                "/api/v1/me/availability", json={**query, "day": str(day + timedelta(days=100))}
            ).status_code
            == 422
        )
        with database.admin.begin() as connection:
            for owner, cancelled in [(tenant, False), (tenant, True), (foreign, False)]:
                start = datetime.combine(day, datetime.min.time(), UTC) + timedelta(
                    hours=14 if not cancelled and owner == tenant else 13
                )
                connection.execute(
                    text("""INSERT INTO levia.occupancies
                    (id, tenant_id, starts_at, ends_at, kind, cancelled)
                    VALUES (:id, :tenant, :start, :end, 'block', :cancelled)"""),
                    {
                        "id": uuid4(),
                        "tenant": owner,
                        "start": start,
                        "end": start + timedelta(minutes=30),
                        "cancelled": cancelled,
                    },
                )
        available = a.post("/api/v1/me/availability", json=query).json()["slots"]
        assert len(available) == 1
        assert datetime.fromisoformat(available[0]["starts_at"]).hour == 14
        assert datetime.fromisoformat(available[0]["starts_at"]).minute == 30
        assert (
            a.put(f"/api/v1/me/services/{first_id}", json={**payload, "active": False}).status_code
            == 200
        )
        assert a.post("/api/v1/me/availability", json=query).status_code == 404
        assert a.get("/api/v1/me/services?active_only=true").json()["total"] == 1
        with database.engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('levia.user_id', :id, true)"), {"id": str(bob)}
            )
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM levia.services WHERE tenant_id=:id"), {"id": tenant}
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM levia.occupancies WHERE tenant_id=:id"),
                    {"id": tenant},
                )
                == 0
            )
