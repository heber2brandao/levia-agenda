from uuid import uuid4

import pytest
from sqlalchemy import text
from test_postgres import ADMIN_URL, client_for, sample_profile
from test_postgres import database as database  # noqa: F401

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL local não configurado")


def test_named_links_are_unique_stable_and_preserve_uuid_links(database):
    with client_for(database, uuid4()) as a, client_for(database, uuid4()) as b:
        data = {**sample_profile(), "studio_name": "Salão da Júlia"}
        first = a.put("/api/v1/me", json=data)
        assert first.status_code == 200, first.text
        first = first.json()
        second = b.put("/api/v1/me", json=data)
        assert second.status_code == 200, second.text
        second = second.json()
        assert first["public_slug"] == "salao-da-julia"
        assert second["public_slug"].startswith("salao-da-julia-")
        assert first["public_slug"] != second["public_slug"]
        for profile in (first, second):
            named = a.get(f"/api/v1/public/{profile['public_slug']}")
            legacy = a.get(f"/api/v1/public/{profile['id']}")
            assert named.status_code == legacy.status_code == 200
            assert named.json() == legacy.json()
            assert not {"owner_id", "phone", "email", "public_slug"} & named.json().keys()
        updated = a.put("/api/v1/me", json={**data, "studio_name": "Novo nome"})
        assert updated.status_code == 200
        assert updated.json()["public_slug"] == first["public_slug"]
        assert b.get("/api/v1/me").json()["id"] == second["id"]
        assert a.get("/api/v1/public/link-inexistente").status_code == 404
        with database.engine.begin() as connection:
            # Lookup context is transaction-local and must not leak from the pool.
            assert connection.scalar(text("SELECT count(*) FROM levia.professionals")) == 0
            connection.execute(text("SELECT set_config('levia.public_slug',:slug,true)"), {"slug": first["public_slug"]})
            assert connection.scalar(text("SELECT count(*) FROM levia.professionals")) == 1


def test_public_booking_through_named_link(database):
    from test_bookings import setup
    with client_for(database, uuid4(), address="192.0.2.201") as c:
        tenant, _, data = setup(c)
        slug = c.get("/api/v1/me").json()["public_slug"]
        available = c.post(f"/api/v1/public/{slug}/availability", json={"day": data["day"], "service_ids": data["service_ids"]})
        assert available.status_code == 200
        result = c.post(f"/api/v1/public/{slug}/appointments", json=data)
        assert result.status_code == 201, result.text
        assert c.post(f"/api/v1/public/{tenant}/appointments", json=data).json()["id"] == result.json()["id"]


def test_migration_backfills_existing_profiles(database):
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    with client_for(database, uuid4()) as c:
        created = c.put("/api/v1/me", json={**sample_profile(), "studio_name": "Estúdio Açúcar"}).json()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.downgrade(config, "0007_notifications")
    command.upgrade(config, "head")
    with database.admin.connect() as connection:
        assert connection.scalar(text("SELECT public_slug FROM levia.professionals WHERE id=:id"), {"id": created["id"]}) == "estudio-acucar"
