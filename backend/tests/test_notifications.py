from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from test_bookings import setup
from test_postgres import ADMIN_URL, client_for
from test_postgres import database as database  # noqa: PLC0414

from app.core.config import Settings
from app.models import EmailJob, EmailUsage
from app.notifications import unsubscribe_token
from app.worker import DeliveryError, claim, process_one, scoped_session

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="PostgreSQL local não configurado")


def test_resend_adapter_idempotency_and_safe_errors(monkeypatch):
    import httpx

    from app.worker import resend_send

    real_client = httpx.Client
    observed = []

    def transport(request):
        observed.append(request)
        return httpx.Response(200, json={"id": "accepted-id"})

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(transport), **kwargs),
    )
    assert resend_send(config(), {"text": "test"}, "stable-key") == "accepted-id"
    assert observed[0].headers["Idempotency-Key"] == "stable-key"
    assert str(observed[0].url) == "https://api.resend.com/emails"
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, text="private response")
            ),
            **kwargs,
        ),
    )
    with pytest.raises(DeliveryError) as error:
        resend_send(config(), {}, "stable-key")
    assert error.value.retryable and str(error.value) == "http_429"


def config():
    return Settings(
        _env_file=None,
        email_enabled=True,
        email_from="agenda@example.com",
        public_web_url="https://agenda.example.test",
        resend_api_key="test-only",
        email_unsubscribe_secret="test-only-" + "x" * 40,
    )


def booking(database, owner):
    with client_for(database, owner) as client:
        tenant, _, data = setup(client)
        data["email"] = "customer@example.com"
        response = client.post("/api/v1/me/appointments", json=data)
        assert response.status_code == 201, response.text
        return tenant, data, response.json()


def test_notice_atomic_idempotent_and_tenant_isolation(database):
    owner = uuid4()
    tenant, data, item = booking(database, owner)
    with client_for(database, owner) as client:
        assert client.post("/api/v1/me/appointments", json=data).status_code == 201
        result = client.get("/api/v1/me/notifications").json()
        assert result["unread"] == 1
        assert result["email"]["statuses"] == {"pending": 2}
        assert result["email"]["limit"] == 100
        notice = result["items"][0]["id"]
        assert client.put(f"/api/v1/me/notifications/{notice}/read").status_code == 200
        assert client.get("/api/v1/me/notifications").json()["unread"] == 0
    stranger = uuid4()
    with client_for(database, stranger) as other:
        setup(other)
        assert other.get("/api/v1/me/notifications").json()["items"] == []
        assert other.put(f"/api/v1/me/notifications/{notice}/read").status_code == 404
    with scoped_session(database.engine, stranger) as session:
        assert (
            session.scalars(select(EmailJob).where(EmailJob.tenant_id == UUID(tenant))).all() == []
        )
        assert (
            session.scalars(select(EmailUsage).where(EmailUsage.tenant_id == UUID(tenant))).all()
            == []
        )
    with client_for(database, owner) as client:
        collision = client.post(
            "/api/v1/me/appointments", json={**data, "request_key": str(uuid4())}
        )
        assert collision.status_code == 409
        assert len(client.get("/api/v1/me/notifications").json()["items"]) == 1
    with scoped_session(database.engine, owner) as session:
        jobs = session.scalars(select(EmailJob).order_by(EmailJob.due_at)).all()
        assert jobs[1].due_at == datetime.fromisoformat(item["starts_at"]) - timedelta(hours=24)


def test_retry_reuses_payload_quota_and_idempotency_key(database):
    owner = uuid4()
    _tenant, _, _ = booking(database, owner)
    now = datetime.now(UTC)
    calls = []

    def timeout(payload, key):
        calls.append((payload, key))
        raise DeliveryError("timeout")

    assert not process_one(database.engine, owner, Settings(_env_file=None), timeout, now)
    assert process_one(database.engine, owner, config(), timeout, now)

    def accepted(payload, key):
        calls.append((payload, key))
        return "provider-test-id"

    assert process_one(database.engine, owner, config(), accepted, now + timedelta(minutes=3))
    assert calls[0] == calls[1]
    with scoped_session(database.engine, owner) as session:
        assert session.scalar(select(EmailUsage.reserved)) == 1
        job = session.scalar(select(EmailJob).where(EmailJob.status == "accepted"))
        assert job.attempts == 2 and job.provider_id == "provider-test-id"


def test_restart_lease_and_idempotency_expiry(database):
    owner = uuid4()
    booking(database, owner)
    now = datetime.now(UTC)
    original = claim(database.engine, owner, config(), now)
    # Simulate process loss after provider acceptance but before DB acknowledgement.
    recovered = claim(database.engine, owner, config(), now + timedelta(minutes=6))
    assert original["key"] == recovered["key"] and original["payload"] == recovered["payload"]
    assert original["lease"] != recovered["lease"]

    def forbidden(*_args):
        pytest.fail("Must not retry after the provider's idempotency window")

    assert process_one(
        database.engine, owner, config(), forbidden, now + timedelta(hours=23, minutes=1)
    )
    with scoped_session(database.engine, owner) as session:
        assert session.get(EmailJob, original["id"]).status == "review"


def test_concurrent_claims_and_atomic_monthly_limit(database):
    owner = uuid4()
    tenant, data, _ = booking(database, owner)
    with client_for(database, owner) as client:
        data["starts_at"] = (
            datetime.fromisoformat(data["starts_at"]) + timedelta(hours=2)
        ).isoformat()
        data["request_key"] = str(uuid4())
        assert client.post("/api/v1/me/appointments", json=data).status_code == 201
    with database.admin.begin() as db:
        db.execute(
            text("UPDATE levia.professionals SET monthly_email_limit=1 WHERE id=:id"),
            {"id": tenant},
        )
    sent = []

    def accepted(payload, key):
        sent.append(key)
        return "provider-id"

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: process_one(database.engine, owner, config(), accepted), range(2)))
    assert len(sent) == 1
    with scoped_session(database.engine, owner) as session:
        assert session.scalar(select(EmailUsage.reserved)) == 1
        assert session.scalar(select(EmailJob.id).where(EmailJob.status == "quota"))


def test_cancellation_reschedule_and_return_revocation(database):
    owner = uuid4()
    tenant, data, item = booking(database, owner)
    with client_for(database, owner) as client:
        moved = datetime.fromisoformat(data["starts_at"]) + timedelta(hours=1)
        assert (
            client.put(
                f"/api/v1/me/appointments/{item['id']}/reschedule",
                json={"starts_at": moved.isoformat()},
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "cancelled"}
            ).status_code
            == 200
        )
    sent = []

    def accepted(payload, key):
        sent.append(payload)
        return "provider-id"

    for _ in range(5):
        process_one(database.engine, owner, config(), accepted)
    assert len(sent) == 1 and sent[0]["subject"] == "Agendamento cancelado"

    owner = uuid4()
    tenant, _, item = booking(database, owner)
    past = datetime.now(UTC) - timedelta(days=14)
    with database.admin.begin() as db:
        db.execute(
            text("UPDATE levia.occupancies SET starts_at=:s,ends_at=:e WHERE id=:id"),
            {"s": past, "e": past + timedelta(minutes=45), "id": item["id"]},
        )
    with client_for(database, owner) as client:
        assert (
            client.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "completed"}
            ).status_code
            == 200
        )
        client.app.state.settings.email_unsubscribe_secret = config().email_unsubscribe_secret
        token = unsubscribe_token(
            tenant, item["client_id"], config().email_unsubscribe_secret.get_secret_value()
        )
        assert (
            client.post(
                "/api/v1/public/email/preferences", json={"token": token[:-1] + "z"}
            ).status_code
            == 400
        )
        assert (
            client.post("/api/v1/public/email/preferences", json={"token": token}).status_code
            == 200
        )
        assert not client.get("/api/v1/me/clients").json()["items"][0]["invites_allowed"]

    def forbidden(*_args):
        pytest.fail("Revoked invitation must not be sent")

    for _ in range(5):
        process_one(
            database.engine, owner, config(), forbidden, datetime.now(UTC) + timedelta(days=1)
        )
    with scoped_session(database.engine, owner) as session:
        assert session.scalar(select(EmailJob).where(EmailJob.kind == "return")).status == "skipped"


def test_reminder_expiration_and_return_opt_in(database):
    owner = uuid4()
    _, data, _ = booking(database, owner)

    def forbidden(*_args):
        pytest.fail("Expired messages must never be sent")

    expired = datetime.fromisoformat(data["starts_at"]) + timedelta(hours=1)
    for _ in range(3):
        process_one(database.engine, owner, config(), forbidden, expired)
    with scoped_session(database.engine, owner) as session:
        assert all(j.status == "skipped" for j in session.scalars(select(EmailJob)).all())
        assert session.scalar(select(EmailUsage.reserved)) is None

    owner = uuid4()
    with client_for(database, owner) as client:
        _, _, data = setup(client)
        data.update(email="customer@example.com", invites_allowed=False)
        item = client.post("/api/v1/me/appointments", json=data).json()
        past = datetime.now(UTC) - timedelta(hours=2)
        with database.admin.begin() as db:
            db.execute(
                text("UPDATE levia.occupancies SET starts_at=:s, ends_at=:e WHERE id=:id"),
                {"s": past, "e": past + timedelta(minutes=45), "id": item["id"]},
            )
        assert (
            client.put(
                f"/api/v1/me/appointments/{item['id']}/status", json={"status": "completed"}
            ).status_code
            == 200
        )
    with scoped_session(database.engine, owner) as session:
        assert session.scalar(select(EmailJob.id).where(EmailJob.kind == "return")) is None
