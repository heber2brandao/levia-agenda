from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select

from app.availability import available_slots
from app.models import Occupancy, Professional, Service, WorkingPeriod
from app.profiles import TenantSession, User

router = APIRouter(prefix="/api/v1/me", tags=["serviços e disponibilidade"])


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)
    name: str = Field(min_length=1, max_length=100)
    price_cents: int = Field(ge=0, le=9999999, strict=True)
    duration_minutes: int = Field(ge=5, le=480, strict=True)
    return_days: int | None = Field(default=None, ge=1, le=365, strict=True)
    active: bool = True


class ServiceOutput(ServiceInput):
    id: UUID


class ServicePage(BaseModel):
    items: list[ServiceOutput]
    total: int


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day: date
    service_ids: list[UUID] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def no_duplicates(self):
        if len(set(self.service_ids)) != len(self.service_ids):
            raise ValueError("Selecione cada serviço apenas uma vez")
        return self


class Slot(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AvailabilityOutput(BaseModel):
    day: date
    timezone: str
    duration_minutes: int
    price_cents: int
    slots: list[Slot]


SUGGESTIONS = {
    "Unhas": [("Manicure", 45, 14), ("Pedicure", 60, 21), ("Esmaltação em gel", 90, 21)],
    "Cílios": [("Extensão de cílios", 120, 21), ("Manutenção de cílios", 90, 21)],
    "Sobrancelhas": [("Design de sobrancelhas", 30, 21), ("Design com henna", 45, 21)],
    "Cabelos": [("Corte", 60, 45), ("Escova", 60, None)],
    "Depilação": [("Depilação de pernas", 45, 30), ("Depilação de axilas", 20, 30)],
    "Estética": [("Limpeza de pele", 90, 60), ("Massagem facial", 45, None)],
}


def own_professional(user: UUID, session, lock=False):
    query = select(Professional).where(Professional.owner_id == user)
    if lock:
        query = query.with_for_update()
    professional = session.scalar(query)
    if professional is None:
        raise HTTPException(404, "Complete seu perfil primeiro")
    return professional


@router.get("/services", response_model=ServicePage)
def list_services(
    user: User,
    session: TenantSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    active_only: bool = False,
):
    tenant = own_professional(user, session)
    filters = [Service.tenant_id == tenant.id]
    if active_only:
        filters.append(Service.active.is_(True))
    return {
        "items": session.scalars(
            select(Service)
            .where(*filters)
            .order_by(Service.name, Service.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(Service).where(*filters)),
    }


@router.post("/services", response_model=ServiceOutput, status_code=201)
def create_service(data: ServiceInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    count = session.scalar(
        select(func.count()).select_from(Service).where(Service.tenant_id == tenant.id)
    )
    if count >= 500:
        raise HTTPException(409, "Limite de 500 serviços no catálogo atingido")
    service = Service(tenant_id=tenant.id, **data.model_dump())
    session.add(service)
    session.flush()
    return service


@router.put("/services/{service_id}", response_model=ServiceOutput)
def update_service(service_id: UUID, data: ServiceInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    service = session.scalar(
        select(Service).where(Service.tenant_id == tenant.id, Service.id == service_id)
    )
    if service is None:
        raise HTTPException(404, "Serviço não encontrado")
    for key, value in data.model_dump().items():
        setattr(service, key, value)
    session.flush()
    return service


@router.get("/service-suggestions")
def service_suggestions(user: User, session: TenantSession):
    tenant = own_professional(user, session)
    return [
        {"specialty": specialty, "name": name, "duration_minutes": duration, "return_days": days}
        for specialty in tenant.specialties
        for name, duration, days in SUGGESTIONS.get(specialty, [])
    ]


@router.post("/availability", response_model=AvailabilityOutput)
def get_availability(data: AvailabilityInput, user: User, session: TenantSession):
    tenant = own_professional(user, session, lock=True)
    zone = ZoneInfo(tenant.timezone)
    now = datetime.now(UTC)
    today = now.astimezone(zone).date()
    if not today <= data.day <= today + timedelta(days=90):
        raise HTTPException(422, "Escolha uma data entre hoje e os próximos 90 dias")
    services = session.scalars(
        select(Service).where(
            Service.tenant_id == tenant.id,
            Service.active.is_(True),
            Service.id.in_(data.service_ids),
        )
    ).all()
    if len(services) != len(data.service_ids):
        raise HTTPException(404, "Um dos serviços não está disponível")
    duration = sum(s.duration_minutes for s in services)
    price = sum(s.price_cents for s in services)
    if duration > 480:
        raise HTTPException(422, "O atendimento deve ter no máximo 480 minutos")
    periods = session.scalars(
        select(WorkingPeriod).where(
            WorkingPeriod.tenant_id == tenant.id, WorkingPeriod.weekday == data.day.weekday()
        )
    ).all()
    day_start = datetime.combine(data.day, time.min, zone).astimezone(UTC)
    day_end = datetime.combine(data.day + timedelta(days=1), time.min, zone).astimezone(UTC)
    busy = session.scalars(
        select(Occupancy).where(
            Occupancy.tenant_id == tenant.id,
            Occupancy.cancelled.is_(False),
            Occupancy.starts_at < day_end,
            Occupancy.ends_at > day_start,
        )
    ).all()
    slots = available_slots(
        data.day,
        tenant.timezone,
        [(p.starts_at, p.ends_at) for p in periods],
        duration,
        [(b.starts_at, b.ends_at) for b in busy],
        now,
    )
    return AvailabilityOutput(
        day=data.day,
        timezone=tenant.timezone,
        duration_minutes=duration,
        price_cents=price,
        slots=[Slot(starts_at=start, ends_at=end) for start, end in slots],
    )
