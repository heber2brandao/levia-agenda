from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_postgres import (
    ADMIN_URL,
    client_for,
    sample_profile,
)
from test_postgres import database as database  # noqa: PLC0414

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL local não configurado")


def setup(client):
    day = (datetime.now(UTC) + timedelta(days=2)).date()
    profile = sample_profile()
    profile["timezone"] = "America/Cuiaba"
    profile["working_periods"] = [
        {"weekday": day.weekday(), "starts_at": "09:00", "ends_at": "18:00"}
    ]
    tenant = client.put("/api/v1/me", json=profile).json()["id"]
    service = client.post(
        "/api/v1/me/services",
        json={"name": "Cuidado", "price_cents": 3500, "duration_minutes": 45, "return_days": 14},
    ).json()["id"]
    starts = datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=13)
    data = {
        "day": str(day),
        "starts_at": starts.isoformat(),
        "service_ids": [service],
        "name": "Cliente de teste",
        "phone": "65999999999",
        "request_key": str(uuid4()),
        "invites_allowed": True,
    }
    return tenant, service, data


def test_real_lifecycle_clients_revenue_and_consent(database):
    with client_for(database, uuid4()) as c:
        tenant, _service, data = setup(c)
        response = c.post("/api/v1/me/appointments", json=data)
        assert response.status_code == 201, response.text
        item = response.json()
        assert c.post("/api/v1/me/appointments", json=data).json()["id"] == item["id"]
        assert (
            c.post(
                "/api/v1/me/appointments", json={**data, "request_key": str(uuid4())}
            ).status_code
            == 409
        )
        listing = c.get(f"/api/v1/me/appointments?start={data['day']}&end={data['day']}").json()
        assert len(listing["items"]) == 1
        assert c.get("/api/v1/me/clients").json()["total"] == 1
        assert (
            c.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "confirmed"}
            ).status_code
            == 200
        )
        assert (
            c.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "completed"}
            ).status_code
            == 422
        )
        summary = c.get("/api/v1/me/dashboard", params={"day": data["day"]}).json()
        assert summary["expected_cents"] == 3500 and summary["completed_month_cents"] == 0
        shifted = datetime.now(UTC) - timedelta(hours=2)
        with database.admin.begin() as db:
            db.execute(
                text("UPDATE levia.occupancies SET starts_at=:start, ends_at=:end WHERE id=:id"),
                {"start": shifted, "end": shifted + timedelta(minutes=45), "id": item["id"]},
            )
        assert (
            c.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "completed"}
            ).status_code
            == 200
        )
        month_day = shifted.astimezone(ZoneInfo("America/Cuiaba")).date()
        assert (
            c.get("/api/v1/me/dashboard", params={"day": str(month_day)}).json()[
                "completed_month_cents"
            ]
            == 3500
        )
        history = c.get(f"/api/v1/me/clients/{item['client_id']}/history").json()["items"]
        assert history[0]["return_date"] is not None
        assert (
            c.put(
                f"/api/v1/me/clients/{item['client_id']}/consent", json={"allowed": False}
            ).status_code
            == 200
        )
        assert not c.get("/api/v1/me/clients").json()["items"][0]["invites_allowed"]
        with database.admin.connect() as db:
            assert (
                db.scalar(
                    text("SELECT count(*) FROM levia.consent_events WHERE tenant_id=:id"),
                    {"id": tenant},
                )
                == 2
            )


def test_reschedule_blocks_cancellation_and_snapshot(database):
    with client_for(database, uuid4()) as c:
        _, service, data = setup(c)
        original = c.post("/api/v1/me/appointments", json=data).json()
        new = datetime.fromisoformat(data["starts_at"]) + timedelta(hours=2)
        block = {
            "starts_at": new.isoformat(),
            "ends_at": (new + timedelta(hours=1)).isoformat(),
            "request_key": str(uuid4()),
        }
        blocked = c.post("/api/v1/me/blocks", json=block)
        assert blocked.status_code == 201, blocked.text
        assert (
            c.put(
                f"/api/v1/me/appointments/{original['id']}/reschedule",
                json={"starts_at": new.isoformat()},
            ).status_code
            == 409
        )
        assert (
            c.put(
                f"/api/v1/me/appointments/{blocked.json()['id']}/status",
                json={"status": "cancelled"},
            ).status_code
            == 200
        )
        moved = c.put(
            f"/api/v1/me/appointments/{original['id']}/reschedule",
            json={"starts_at": new.isoformat()},
        )
        assert moved.status_code == 200, moved.text
        c.put(
            f"/api/v1/me/services/{service}",
            json={"name": "Alterado", "price_cents": 9999, "duration_minutes": 60, "active": False},
        )
        assert moved.json()["price_cents"] == 3500
        assert moved.json()["services"][0]["name"] == "Cuidado"
        assert (
            c.put(
                f"/api/v1/me/appointments/{original['id']}/status", json={"status": "cancelled"}
            ).status_code
            == 200
        )
        assert (
            c.get("/api/v1/me/dashboard", params={"day": data["day"]}).json()["expected_cents"] == 0
        )


@pytest.mark.parametrize("source", ["manual", "public"])
def test_more_than_four_bookings_keep_distinct_clients(database, source):
    user = uuid4()
    with client_for(database, user) as c:
        tenant, _, data = setup(c)
        path = (
            "/api/v1/me/appointments"
            if source == "manual"
            else f"/api/v1/public/{tenant}/appointments"
        )
        saved = []
        for index in range(6):
            payload = {
                **data,
                "starts_at": (
                    datetime.fromisoformat(data["starts_at"]) + timedelta(hours=index)
                ).isoformat(),
                "name": f"Cliente {index + 1}",
                "phone": f"6599999999{index}",
                "request_key": str(uuid4()),
            }
            # Independent public visitors; keep the real per-IP quota enabled.
            with client_for(database, user, address=f"192.0.2.{index + 1}") as visitor:
                response = visitor.post(path, json=payload)
            assert response.status_code == 201, response.text
            saved.append(response.json()["id"])
        listing = c.get(
            "/api/v1/me/appointments", params={"start": data["day"], "end": data["day"]}
        ).json()["items"]
        assert [item["id"] for item in listing] == saved
        assert [item["client_name"] for item in listing] == [
            f"Cliente {index + 1}" for index in range(6)
        ]
        assert len({item["client_id"] for item in listing}) == 6
        assert c.get("/api/v1/me/clients").json()["total"] == 6


def test_public_reused_phone_saves_new_booking_under_existing_client(database):
    with client_for(database, uuid4(), address="192.0.2.100") as c:
        tenant, _, data = setup(c)
        path = f"/api/v1/public/{tenant}/appointments"
        first = c.post(path, json=data)
        second = c.post(path, json={
            **data,
            "starts_at": (
                datetime.fromisoformat(data["starts_at"]) + timedelta(hours=1)
            ).isoformat(),
            "name": "Outro nome no mesmo telefone",
            "request_key": str(uuid4()),
        })
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
        items = c.get(
            "/api/v1/me/appointments", params={"start": data["day"], "end": data["day"]}
        ).json()["items"]
        assert len(items) == 2
        assert items[0]["client_id"] == items[1]["client_id"]
        assert [item["client_name"] for item in items] == [data["name"], data["name"]]


def test_concurrent_booking_wins_only_once(database):
    user = uuid4()
    with client_for(database, user) as c:
        _, _, data = setup(c)

    def create(_):
        with client_for(database, user) as c:
            return c.post(
                "/api/v1/me/appointments", json={**data, "request_key": str(uuid4())}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, range(2))) == [201, 409]


def test_cross_tenant_and_public_privacy(database):
    with client_for(database, uuid4()) as a, client_for(database, uuid4()) as b:
        tenant, _, data = setup(a)
        setup(b)
        page = a.get(f"/api/v1/public/{tenant}")
        assert page.status_code == 200, page.text
        assert not {"owner_id", "phone", "email"} & page.json().keys()
        available = a.post(
            f"/api/v1/public/{tenant}/availability",
            json={"day": data["day"], "service_ids": data["service_ids"]},
        )
        assert available.status_code == 200, available.text
        reservation = a.post(f"/api/v1/public/{tenant}/appointments", json=data)
        assert reservation.status_code == 201, reservation.text
        assert not {"name", "phone", "email", "client_id"} & reservation.json().keys()
        item = a.get(f"/api/v1/me/appointments?start={data['day']}&end={data['day']}").json()[
            "items"
        ][0]
        assert (
            b.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "cancelled"}
            ).status_code
            == 404
        )
        assert b.get(f"/api/v1/me/clients/{item['client_id']}/history").status_code == 404
        assert (
            b.put(
                f"/api/v1/me/clients/{item['client_id']}/consent", json={"allowed": True}
            ).status_code
            == 404
        )
        assert b.get("/api/v1/me/clients").json()["total"] == 0


def test_exclusion_constraint_protects_direct_writes(database):
    with client_for(database, uuid4()) as c:
        tenant, _, data = setup(c)
        assert c.post("/api/v1/me/appointments", json=data).status_code == 201
    start = datetime.fromisoformat(data["starts_at"])
    with pytest.raises(IntegrityError), database.admin.begin() as db:
        db.execute(
            text(
                "INSERT INTO levia.occupancies(id,tenant_id,starts_at,ends_at,kind,cancelled) VALUES(:id,:tenant,:start,:end,'block',false)"
            ),
            {"id": uuid4(), "tenant": tenant, "start": start, "end": start + timedelta(minutes=15)},
        )
