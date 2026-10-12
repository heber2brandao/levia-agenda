"""Durable, tenant-scoped email worker. Run: python -m app.worker [--once]."""

import argparse
import logging
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database import check_runtime_role, make_engine
from app.models import Client, EmailJob, EmailUsage, Occupancy, Professional
from app.notifications import unsubscribe_token

log = logging.getLogger("levia.worker")


@contextmanager
def scoped_session(engine, owner):
    with Session(engine, expire_on_commit=False) as session, session.begin():
        session.execute(
            text("SELECT set_config('levia.user_id', :owner, true)"), {"owner": str(owner)}
        )
        yield session


def eligible(session, job, item, now):
    if not item or item.notification_version != job.version or job.expires_at <= now:
        return False
    if job.kind == "cancelled":
        return item.cancelled
    if item.cancelled:
        return False
    if job.kind == "return":
        client = session.get(Client, item.client_id)
        if not client or not client.invites_allowed or item.status != "completed":
            return False
        # A newer completed visit or an active future reservation supersedes this invitation.
        newer = session.scalar(
            select(Occupancy.id)
            .where(
                Occupancy.tenant_id == item.tenant_id,
                Occupancy.client_id == item.client_id,
                Occupancy.id != item.id,
                Occupancy.cancelled.is_(False),
                or_(
                    (Occupancy.status == "completed") & (Occupancy.starts_at > item.starts_at),
                    (Occupancy.status.in_(["pending", "confirmed"])) & (Occupancy.ends_at > now),
                ),
            )
            .limit(1)
        )
        return newer is None
    return item.status in ("pending", "confirmed") and item.starts_at > now


def claim(engine, owner, settings, now):
    with scoped_session(engine, owner) as session:
        tenant = session.scalar(select(Professional).where(Professional.owner_id == owner))
        if not tenant:
            return None
        job = session.scalar(
            select(EmailJob)
            .where(
                EmailJob.tenant_id == tenant.id,
                or_(
                    (EmailJob.status == "pending") & (EmailJob.due_at <= now),
                    (EmailJob.status == "processing") & (EmailJob.lease_until <= now),
                ),
            )
            .order_by(EmailJob.due_at, EmailJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        item = session.get(Occupancy, job.appointment_id)
        if not eligible(session, job, item, now):
            job.status = "review" if job.first_attempt_at else "skipped"
            job.error_code = "outdated"
            return {"handled": True}
        # Resend only retains idempotency keys for 24h. Never retry beyond 23h.
        if job.first_attempt_at and (
            now >= job.first_attempt_at + timedelta(hours=23) or job.attempts >= 8
        ):
            job.status, job.error_code = "review", "retry_window_closed"
            return {"handled": True}
        if job.quota_month is None:
            month = now.astimezone(ZoneInfo(tenant.timezone)).date().replace(day=1)
            if tenant.monthly_email_limit <= 0:
                job.status, job.error_code = "quota", "monthly_limit"
                return {"handled": True}
            statement = insert(EmailUsage).values(tenant_id=tenant.id, month=month, reserved=1)
            statement = statement.on_conflict_do_update(
                index_elements=[EmailUsage.tenant_id, EmailUsage.month],
                set_={"reserved": EmailUsage.reserved + 1},
                where=EmailUsage.reserved < tenant.monthly_email_limit,
            ).returning(EmailUsage.reserved)
            if session.scalar(statement) is None:
                job.status, job.error_code = "quota", "monthly_limit"
                return {"handled": True}
            job.quota_month = month
        if job.payload is None:
            body = job.body
            if job.kind == "return":
                token = unsubscribe_token(
                    tenant.id, item.client_id, settings.email_unsubscribe_secret.get_secret_value()
                )
                body += (
                    "\n\nAgendar: " + settings.public_web_url.rstrip("/") + f"/agendar/{tenant.public_slug or tenant.id}"
                )
                body += (
                    "\nNão receber mais convites: "
                    + settings.public_web_url.rstrip("/")
                    + f"/preferencias/{token}"
                )
            job.payload = {
                "from": settings.email_from,
                "to": [job.recipient],
                "subject": job.subject,
                "text": body,
            }
        job.first_attempt_at = job.first_attempt_at or now
        job.attempts += 1
        job.status = "processing"
        job.lease_until = now + timedelta(minutes=5)
        job.lease_token = uuid4()
        return {
            "id": job.id,
            "lease": job.lease_token,
            "payload": job.payload,
            "key": f"levia-email/{job.id}",
        }


class DeliveryError(Exception):
    def __init__(self, code, retryable=True):
        self.code, self.retryable = code, retryable
        super().__init__(code)


def resend_send(settings, payload, key):
    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": "Bearer " + settings.resend_api_key.get_secret_value(),
                    "Idempotency-Key": key,
                },
            )
        if response.status_code >= 300:
            raise DeliveryError(
                f"http_{response.status_code}",
                response.status_code in (408, 409, 429) or response.status_code >= 500,
            )
        identifier = response.json().get("id")
        if not isinstance(identifier, str) or not identifier or len(identifier) > 100:
            raise DeliveryError("invalid_response")
        return identifier
    except httpx.HTTPError:
        raise DeliveryError("network_error") from None
    except ValueError:
        raise DeliveryError("invalid_response") from None


def process_one(engine, owner, settings, sender=None, now=None):
    if not settings.email_enabled:
        return False
    fixed_now = now
    now = now or datetime.now(UTC)
    job = claim(engine, owner, settings, now)
    if job is None:
        return False
    if job.get("handled"):
        return True
    failure, provider_id = None, None
    # Recheck cancellation/consent immediately before the provider call.
    with scoped_session(engine, owner) as session:
        current = session.get(EmailJob, job["id"])
        check_time = fixed_now or datetime.now(UTC)
        if current.lease_token != job["lease"] or current.status != "processing":
            return True
        if current.lease_until <= check_time:
            return True
        if not eligible(
            session, current, session.get(Occupancy, current.appointment_id), check_time
        ):
            current.status, current.error_code = "review", "outdated"
            return True
    try:
        provider_id = (sender or (lambda payload, key: resend_send(settings, payload, key)))(
            job["payload"], job["key"]
        )
    except DeliveryError as exc:
        failure = exc
    with scoped_session(engine, owner) as session:
        current = session.scalar(select(EmailJob).where(EmailJob.id == job["id"]).with_for_update())
        if current.lease_token != job["lease"]:
            return True
        current.lease_until, current.lease_token = None, None
        if failure is None:
            current.status, current.provider_id, current.error_code = "accepted", provider_id, None
        else:
            current.error_code = failure.code
            if not failure.retryable:
                current.status = "failed"
            elif current.attempts >= 8:
                current.status = "review"
            else:
                current.status = "pending"
                current.due_at = now + timedelta(seconds=min(60 * 2**current.attempts, 3600))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if not settings.email_enabled:
        print("Envios desativados. Nenhum e-mail processado.")
        return
    if not settings.database_url or not settings.worker_owner_ids:
        raise SystemExit(
            "Configure DATABASE_URL restrito e WORKER_OWNER_IDS para as contas autorizadas."
        )
    engine = make_engine(settings.database_url.get_secret_value())
    check_runtime_role(engine)
    try:
        while True:
            for owner in settings.worker_owner_ids:
                # Bounded fair batches; an owner cannot starve other configured owners.
                for _ in range(20):
                    try:
                        if not process_one(engine, owner, settings):
                            break
                    except Exception:  # noqa: BLE001 -- keep daemon alive without logging secrets
                        log.error("Falha no ciclo; a fila será retomada sem expor dados pessoais.")
                        break
                    time.sleep(0.6)  # conservative provider-wide throughput
            if args.once:
                break
            time.sleep(settings.worker_poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
