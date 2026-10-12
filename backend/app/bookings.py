from base64 import b64encode
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.availability import available_slots
from app.catalog import AvailabilityInput, get_availability, own_professional
from app.models import Client, ConsentEvent, Occupancy, Professional, Service, WorkingPeriod
from app.notifications import schedule_notifications
from app.profiles import TenantSession, User
from app.security import consume_limit

router = APIRouter(prefix="/api/v1/me", tags=["agenda e clientes"])
public = APIRouter(prefix="/api/v1/public", tags=["agendamento público"])


class BookingInput(AvailabilityInput):
    starts_at: AwareDatetime
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=r"^[0-9]{10,15}$")
    email: EmailStr | None = None
    invites_allowed: bool = False
    request_key: UUID


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "completed", "cancelled"]


class MoveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starts_at: AwareDatetime


class BlockInput(MoveInput):
    ends_at: AwareDatetime
    request_key: UUID


def bounds(day, zone):
    return datetime.combine(day, time.min, zone).astimezone(UTC), datetime.combine(
        day + timedelta(days=1), time.min, zone
    ).astimezone(UTC)


def validate_slot(session, tenant, starts_at, duration, exclude=None):
    zone = ZoneInfo(tenant.timezone)
    day = starts_at.astimezone(zone).date()
    now = datetime.now(UTC)
    if not now.astimezone(zone).date() <= day <= now.astimezone(zone).date() + timedelta(days=90):
        raise HTTPException(422, "Escolha uma data nos próximos 90 dias")
    opening, closing = bounds(day, zone)
    periods = session.scalars(
        select(WorkingPeriod).where(
            WorkingPeriod.tenant_id == tenant.id, WorkingPeriod.weekday == day.weekday()
        )
    ).all()
    query = select(Occupancy).where(
        Occupancy.tenant_id == tenant.id,
        Occupancy.cancelled.is_(False),
        Occupancy.starts_at < closing,
        Occupancy.ends_at > opening,
    )
    if exclude:
        query = query.where(Occupancy.id != exclude)
    busy = session.scalars(query).all()
    slots = available_slots(
        day,
        tenant.timezone,
        [(p.starts_at, p.ends_at) for p in periods],
        duration,
        [(b.starts_at, b.ends_at) for b in busy],
        now,
    )
    if not any(start == starts_at for start, _ in slots):
        raise HTTPException(409, "Este horário não está disponível. Consulte novamente.")


def book(data, tenant, session, source):
    previous = session.scalar(
        select(Occupancy).where(
            Occupancy.tenant_id == tenant.id, Occupancy.request_key == data.request_key
        )
    )
    if previous:
        if previous.starts_at != data.starts_at or {s["id"] for s in previous.services} != {
            str(x) for x in data.service_ids
        }:
            raise HTTPException(409, "Identificador já utilizado em outra reserva")
        return previous
    if data.starts_at.astimezone(ZoneInfo(tenant.timezone)).date() != data.day:
        raise HTTPException(422, "Data e horário não correspondem")
    if not data.name.strip():
        raise HTTPException(422, "Informe o nome")
    services = session.scalars(
        select(Service).where(
            Service.tenant_id == tenant.id,
            Service.id.in_(data.service_ids),
            Service.active.is_(True),
        )
    ).all()
    if len(services) != len(data.service_ids):
        raise HTTPException(404, "Serviço indisponível")
    duration = sum(s.duration_minutes for s in services)
    if duration > 480:
        raise HTTPException(422, "Selecione até 480 minutos de atendimento")
    validate_slot(session, tenant, data.starts_at, duration)
    client = session.scalar(
        select(Client).where(Client.tenant_id == tenant.id, Client.phone == data.phone)
    )
    if client is None:
        client = Client(
            tenant_id=tenant.id,
            name=data.name.strip(),
            phone=data.phone,
            email=str(data.email) if data.email else None,
            invites_allowed=data.invites_allowed,
        )
        session.add(client)
        session.flush()
        session.add(
            ConsentEvent(
                tenant_id=tenant.id,
                client_id=client.id,
                allowed=data.invites_allowed,
                source=source,
            )
        )
    elif source == "manual":
        client.name, client.email = (
            data.name.strip(),
            str(data.email) if data.email else client.email,
        )
    # Consent is an explicit event, separate from appointment processing.
    if data.invites_allowed and not client.invites_allowed:
        client.invites_allowed = True
        session.add(
            ConsentEvent(tenant_id=tenant.id, client_id=client.id, allowed=True, source=source)
        )
    appointment = Occupancy(
        tenant_id=tenant.id,
        client_id=client.id,
        starts_at=data.starts_at,
        ends_at=data.starts_at + timedelta(minutes=duration),
        kind="appointment",
        cancelled=False,
        status="pending",
        source=source,
        request_key=data.request_key,
        notification_email=str(data.email) if data.email else None,
        price_cents=sum(s.price_cents for s in services),
        services=[
            {
                "id": str(s.id),
                "name": s.name,
                "price_cents": s.price_cents,
                "duration_minutes": s.duration_minutes,
                "return_days": s.return_days,
            }
            for s in services
        ],
    )
    session.add(appointment)
    session.flush()
    schedule_notifications(session, tenant, appointment, "booked")
    return appointment


def appointment_output(item, client=None):
    return {
        "id": item.id,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "kind": item.kind,
        "status": "cancelled" if item.cancelled else item.status,
        "price_cents": item.price_cents,
        "services": item.services,
        "client_id": item.client_id,
        "client_name": client.name if client else "Bloqueio de horário",
        "phone": client.phone if client else None,
        "return_date": item.return_date,
    }


@router.post("/appointments", status_code=201)
def create_appointment(data: BookingInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    item = book(data, tenant, session, "manual")
    return appointment_output(item, session.get(Client, item.client_id))


@router.get("/appointments")
def list_appointments(
    user: User,
    session: TenantSession,
    start: date,
    end: date,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    tenant = own_professional(user, session)
    if not 0 <= (end - start).days <= 31:
        raise HTTPException(422, "Consulte até 31 dias por vez")
    zone = ZoneInfo(tenant.timezone)
    low, high = bounds(start, zone)[0], bounds(end, zone)[1]
    rows = session.execute(
        select(Occupancy, Client)
        .outerjoin(Client, Client.id == Occupancy.client_id)
        .where(
            Occupancy.tenant_id == tenant.id, Occupancy.starts_at < high, Occupancy.ends_at > low
        )
        .order_by(Occupancy.starts_at, Occupancy.id)
        .offset(offset)
        .limit(500)
    ).all()
    return {
        "timezone": tenant.timezone,
        "items": [appointment_output(a, c) for a, c in rows],
        "has_more": len(rows) == 500,
    }


def owned_item(session, tenant, identifier):
    item = session.scalar(
        select(Occupancy).where(Occupancy.tenant_id == tenant.id, Occupancy.id == identifier)
    )
    if not item:
        raise HTTPException(404, "Agendamento não encontrado")
    return item


@router.put("/appointments/{identifier}/status")
def change_status(identifier: UUID, data: StatusInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    item = owned_item(session, tenant, identifier)
    if item.status == data.status:
        return {"status": item.status}
    if item.cancelled or item.status == "completed":
        raise HTTPException(409, "Atendimento já encerrado")
    if item.kind == "block" and data.status != "cancelled":
        raise HTTPException(422, "Bloqueios só podem ser liberados")
    if data.status == "completed" and item.starts_at > datetime.now(UTC):
        raise HTTPException(422, "Não é possível concluir atendimento futuro")
    item.status = data.status
    item.notification_version += 1
    item.cancelled = data.status == "cancelled"
    if data.status == "completed":
        days = [s["return_days"] for s in item.services if s.get("return_days")]
        item.return_date = (
            item.starts_at.astimezone(ZoneInfo(tenant.timezone)).date() + timedelta(days=min(days))
            if days
            else None
        )
    session.flush()
    schedule_notifications(session, tenant, item, data.status)
    return {"status": item.status}


@router.put("/appointments/{identifier}/reschedule")
def reschedule(identifier: UUID, data: MoveInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    item = owned_item(session, tenant, identifier)
    if item.cancelled or item.status == "completed" or item.kind != "appointment":
        raise HTTPException(409, "Este atendimento não pode ser reagendado")
    duration = int((item.ends_at - item.starts_at).total_seconds() / 60)
    validate_slot(session, tenant, data.starts_at, duration, item.id)
    item.starts_at, item.ends_at = data.starts_at, data.starts_at + timedelta(minutes=duration)
    item.notification_version += 1
    session.flush()
    schedule_notifications(session, tenant, item, "rescheduled")
    return appointment_output(item, session.get(Client, item.client_id))


@router.post("/blocks", status_code=201)
def create_block(data: BlockInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    if data.starts_at < datetime.now(UTC) or not timedelta(
        0
    ) < data.ends_at - data.starts_at <= timedelta(days=31):
        raise HTTPException(422, "Informe um intervalo futuro de até 31 dias")
    previous = session.scalar(
        select(Occupancy).where(
            Occupancy.tenant_id == tenant.id, Occupancy.request_key == data.request_key
        )
    )
    if previous:
        if (
            previous.kind != "block"
            or previous.starts_at != data.starts_at
            or previous.ends_at != data.ends_at
        ):
            raise HTTPException(409, "Identificador já utilizado")
        return appointment_output(previous)
    item = Occupancy(
        tenant_id=tenant.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        kind="block",
        status="confirmed",
        request_key=data.request_key,
    )
    session.add(item)
    session.flush()
    return appointment_output(item)


@router.get("/dashboard")
def dashboard(user: User, session: TenantSession, day: date | None = None):
    tenant = own_professional(user, session)
    zone = ZoneInfo(tenant.timezone)
    day = day or datetime.now(zone).date()
    low, high = bounds(day, zone)
    month = day.replace(day=1)
    next_month = (month + timedelta(days=32)).replace(day=1)
    common = [
        Occupancy.tenant_id == tenant.id,
        Occupancy.kind == "appointment",
        Occupancy.cancelled.is_(False),
    ]
    today = (
        select(func.count())
        .select_from(Occupancy)
        .where(*common, Occupancy.starts_at >= low, Occupancy.starts_at < high)
    )
    predicted = (
        select(func.coalesce(func.sum(Occupancy.price_cents), 0)).where(
            *common, Occupancy.starts_at >= low, Occupancy.starts_at < high
        )
    )
    realized = (
        select(func.coalesce(func.sum(Occupancy.price_cents), 0)).where(
            *common,
            Occupancy.status == "completed",
            Occupancy.starts_at >= bounds(month, zone)[0],
            Occupancy.starts_at < bounds(next_month, zone)[0],
        )
    )
    latest = (
        select(Occupancy.client_id, func.max(Occupancy.starts_at).label("last"))
        .where(*common, Occupancy.status == "completed")
        .group_by(Occupancy.client_id)
        .subquery()
    )
    returns = (
        select(func.count())
        .select_from(Occupancy)
        .join(
            latest,
            (latest.c.client_id == Occupancy.client_id) & (latest.c.last == Occupancy.starts_at),
        )
        .join(Client, Client.id == Occupancy.client_id)
        .where(Occupancy.return_date <= day, Client.invites_allowed.is_(True))
    )
    clients = select(func.count()).select_from(Client).where(Client.tenant_id == tenant.id)
    # One database round trip for the five independent aggregates.
    stats = session.execute(select(
        today.scalar_subquery().label("appointments_today"),
        predicted.scalar_subquery().label("expected_cents"),
        realized.scalar_subquery().label("completed_month_cents"),
        returns.scalar_subquery().label("returns_due"),
        clients.scalar_subquery().label("clients"),
    )).mappings().one()
    return {
        "day": day,
        "timezone": tenant.timezone,
        **stats,
    }


@router.get("/clients")
def list_clients(
    user: User, session: TenantSession, q: str = "", offset: Annotated[int, Query(ge=0)] = 0
):
    tenant = own_professional(user, session)
    filters = [Client.tenant_id == tenant.id]
    if q:
        filters.append(
            Client.name.ilike("%" + q[:100].replace("%", "\\%").replace("_", "\\_") + "%")
        )
    rows = session.scalars(
        select(Client).where(*filters).order_by(Client.name, Client.id).offset(offset).limit(50)
    ).all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "invites_allowed": c.invites_allowed,
            }
            for c in rows
        ],
        "total": session.scalar(select(func.count()).select_from(Client).where(*filters)),
    }


@router.get("/clients/{identifier}/history")
def history(
    identifier: UUID, user: User, session: TenantSession, offset: Annotated[int, Query(ge=0)] = 0
):
    tenant = own_professional(user, session)
    client = session.scalar(
        select(Client).where(Client.tenant_id == tenant.id, Client.id == identifier)
    )
    if not client:
        raise HTTPException(404, "Cliente não encontrada")
    items = session.scalars(
        select(Occupancy)
        .where(Occupancy.tenant_id == tenant.id, Occupancy.client_id == identifier)
        .order_by(Occupancy.starts_at.desc())
        .offset(offset)
        .limit(50)
    ).all()
    return {"items": [appointment_output(i, client) for i in items]}


class ConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed: bool


@router.put("/clients/{identifier}/consent")
def consent(identifier: UUID, data: ConsentInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    client = session.scalar(
        select(Client).where(Client.id == identifier, Client.tenant_id == tenant.id)
    )
    if not client:
        raise HTTPException(404, "Cliente não encontrada")
    client.invites_allowed = data.allowed
    session.add(
        ConsentEvent(
            tenant_id=tenant.id, client_id=client.id, allowed=data.allowed, source="professional"
        )
    )
    session.flush()
    return {"invites_allowed": client.invites_allowed}


def public_session(tenant_id: str, request: Request):
    if request.app.state.engine is None:
        raise HTTPException(503, "Serviço indisponível")
    with Session(request.app.state.engine) as session, session.begin():
        try:
            identifier = UUID(tenant_id)
        except ValueError:
            identifier = None
        session.execute(text("SELECT set_config('levia.public_tenant',:id,true), set_config('levia.public_slug',:slug,true)"),
                        {"id": str(identifier) if identifier else "", "slug": tenant_id if not identifier else ""})
        tenant = session.scalar(select(Professional).where(
            Professional.id == identifier if identifier else Professional.public_slug == tenant_id
        ))
        if not tenant:
            raise HTTPException(404, "Espaço não encontrado")
        session.execute(
            text("SELECT set_config('levia.user_id',:id,true)"), {"id": str(tenant.owner_id)}
        )
        session.execute(text("SELECT set_config('levia.public_tenant','',true), set_config('levia.public_slug','',true)"))
        if request.method == "POST" and request.url.path.endswith("/appointments"):
            identity = "public-book:" + (request.client.host if request.client else "unknown")
            if not consume_limit(
                request.app.state.engine,
                request.app.state.settings.rate_limit_secret.get_secret_value(),
                identity,
                5,
            ):
                raise HTTPException(429, "Muitas tentativas. Aguarde um minuto.")
        yield session, tenant


PublicContext = Annotated[tuple, Depends(public_session, scope="function")]


@public.get("/{tenant_id}")
def public_profile(context: PublicContext):
    session, tenant = context
    services = session.scalars(
        select(Service)
        .where(Service.tenant_id == tenant.id, Service.active.is_(True))
        .order_by(Service.name)
    ).all()
    return {
        "id": tenant.id,
        "studio_name": tenant.studio_name,
        "timezone": tenant.timezone,
        "primary_color": tenant.primary_color,
        "background_color": tenant.background_color,
        "logo": "data:image/png;base64," + b64encode(tenant.logo_png).decode()
        if tenant.logo_png
        else None,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "price_cents": s.price_cents,
                "duration_minutes": s.duration_minutes,
            }
            for s in services
        ],
    }


@public.post("/{tenant_id}/availability")
def public_availability(data: AvailabilityInput, context: PublicContext):
    session, tenant = context
    return get_availability(data, tenant.owner_id, session)


@public.post("/{tenant_id}/appointments", status_code=201)
def public_book(data: BookingInput, context: PublicContext):
    session, tenant = context
    tenant = own_professional(tenant.owner_id, session, lock=True)
    item = book(data, tenant, session, "public")
    # Do not disclose customer data, even on idempotent repeats.
    return {
        "id": item.id,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "price_cents": item.price_cents,
        "status": item.status,
    }
