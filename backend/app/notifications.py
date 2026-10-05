"""Transactional outbox. No provider calls inside HTTP booking transactions."""

import hashlib
import hmac
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.catalog import own_professional
from app.models import Client, ConsentEvent, EmailJob, EmailUsage, Notice, Professional
from app.profiles import TenantSession, User

router = APIRouter(prefix="/api/v1", tags=["notificações"])


def schedule_notifications(session, tenant, item, event):
    if item.kind != "appointment":
        return
    now = datetime.now(UTC)
    version = item.notification_version
    key = f"{item.id}:{version}"
    when = item.starts_at.astimezone(ZoneInfo(tenant.timezone)).strftime("%d/%m/%Y às %H:%M")
    titles = {
        "booked": "Novo agendamento",
        "confirmed": "Atendimento confirmado",
        "cancelled": "Agendamento cancelado",
        "rescheduled": "Agendamento reagendado",
        "completed": "Atendimento concluído",
    }
    message = f"{when} · {sum(s['duration_minutes'] for s in item.services)} minutos"
    session.add(
        Notice(tenant_id=tenant.id, event_key=key, title=titles[event], message=message, due_at=now)
    )
    if not item.notification_email:
        return
    details = f"{tenant.studio_name}\n{when}\n" + " + ".join(s["name"] for s in item.services)

    def enqueue(kind, subject, body, due, expires):
        session.add(
            EmailJob(
                tenant_id=tenant.id,
                appointment_id=item.id,
                version=version,
                event_key=f"{key}:{kind}",
                kind=kind,
                recipient=item.notification_email,
                subject=subject,
                body=body + "\n\n" + details,
                due_at=due,
                expires_at=expires,
            )
        )

    if event != "completed":
        title = (
            "Agendamento recebido — aguardando confirmação" if event == "booked" else titles[event]
        )
        enqueue(
            event,
            title,
            title + ".",
            now,
            now + timedelta(days=1) if event == "cancelled" else item.starts_at,
        )
    if event in ("booked", "confirmed", "rescheduled"):
        due = item.starts_at - timedelta(hours=24)
        if due > now:
            enqueue(
                "reminder",
                "Lembrete do seu atendimento",
                "Seu atendimento está chegando.",
                due,
                item.starts_at,
            )
    if event == "completed" and item.return_date:
        client = session.get(Client, item.client_id)
        if client.invites_allowed:
            due = datetime.combine(item.return_date, time(9), ZoneInfo(tenant.timezone))
            enqueue(
                "return",
                "Que tal agendar seu retorno?",
                "Já está na época sugerida para seu próximo cuidado. O convite é opcional.",
                due,
                due + timedelta(days=7),
            )


def unsubscribe_token(tenant_id, client_id, secret):
    value = f"{tenant_id}.{client_id}"
    signature = hmac.new(
        secret.encode(), ("email-optout:" + value).encode(), hashlib.sha256
    ).hexdigest()
    return value + "." + signature


@router.get("/me/notifications")
def notifications(user: User, session: TenantSession, request: Request):
    tenant = own_professional(user, session)
    now = datetime.now(UTC)
    month = now.astimezone(ZoneInfo(tenant.timezone)).date().replace(day=1)
    usage = session.get(EmailUsage, (tenant.id, month))
    rows = session.scalars(
        select(Notice)
        .where(Notice.tenant_id == tenant.id, Notice.due_at <= now)
        .order_by(Notice.due_at.desc())
        .limit(30)
    ).all()
    statuses = dict(
        session.execute(
            select(EmailJob.status, func.count())
            .where(EmailJob.tenant_id == tenant.id)
            .group_by(EmailJob.status)
        ).all()
    )
    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "created_at": n.due_at,
                "read": n.read_at is not None,
            }
            for n in rows
        ],
        "unread": session.scalar(
            select(func.count())
            .select_from(Notice)
            .where(Notice.tenant_id == tenant.id, Notice.read_at.is_(None), Notice.due_at <= now)
        ),
        "email": {
            "enabled": request.app.state.settings.email_enabled,
            "month": month,
            "limit": tenant.monthly_email_limit,
            "reserved": usage.reserved if usage else 0,
            "statuses": statuses,
        },
    }


@router.put("/me/notifications/{identifier}/read")
def mark_read(identifier: UUID, user: User, session: TenantSession):
    tenant = own_professional(user, session)
    notice = session.scalar(
        select(Notice).where(Notice.id == identifier, Notice.tenant_id == tenant.id)
    )
    if not notice:
        raise HTTPException(404, "Aviso não encontrado")
    notice.read_at = notice.read_at or datetime.now(UTC)
    return {"read": True}


class UnsubscribeInput(BaseModel):
    token: str = Field(max_length=150)


@router.post("/public/email/preferences")
def unsubscribe(data: UnsubscribeInput, request: Request):
    secret = request.app.state.settings.email_unsubscribe_secret
    try:
        tenant, client, _signature = data.token.split(".")
        tenant, client = UUID(tenant), UUID(client)
        if not secret or not hmac.compare_digest(
            data.token, unsubscribe_token(tenant, client, secret.get_secret_value())
        ):
            raise ValueError()
    except (ValueError, AttributeError):
        raise HTTPException(400, "Link de preferências inválido") from None
    if request.app.state.engine is None:
        raise HTTPException(503, "Serviço indisponível")
    with Session(request.app.state.engine) as session, session.begin():
        session.execute(
            text("SELECT set_config('levia.public_tenant', :tenant, true)"), {"tenant": str(tenant)}
        )
        professional = session.get(Professional, tenant)
        if not professional:
            raise HTTPException(400, "Link de preferências inválido")
        session.execute(
            text("SELECT set_config('levia.user_id', :owner, true)"),
            {"owner": str(professional.owner_id)},
        )
        customer = session.scalar(
            select(Client).where(Client.id == client, Client.tenant_id == tenant)
        )
        if not customer:
            raise HTTPException(400, "Link de preferências inválido")
        if customer.invites_allowed:
            customer.invites_allowed = False
            session.add(
                ConsentEvent(tenant_id=tenant, client_id=client, allowed=False, source="email")
            )
    return {"revoked": True}
