from datetime import date, datetime, time
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Professional(Base):
    __tablename__ = "professionals"
    logo_png: Mapped[bytes | None] = mapped_column(LargeBinary)
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="professional_name_not_blank"),
        CheckConstraint("length(trim(studio_name)) > 0", name="studio_name_not_blank"),
        CheckConstraint("primary_color ~ '^#[0-9a-fA-F]{6}$'", name="primary_color_hex"),
        CheckConstraint("background_color ~ '^#[0-9a-fA-F]{6}$'", name="background_color_hex"),
        CheckConstraint("logo_png IS NULL OR octet_length(logo_png) <= 270000", name="logo_size"),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    studio_name: Mapped[str] = mapped_column(String(100))
    public_slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    specialties: Mapped[list[str]] = mapped_column(JSONB, default=list)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Cuiaba")
    primary_color: Mapped[str] = mapped_column(String(7), default="#9a746d")
    background_color: Mapped[str] = mapped_column(String(7), default="#f7f3ef")
    monthly_email_limit: Mapped[int] = mapped_column(default=100, server_default="100")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkingPeriod(Base):
    __tablename__ = "working_periods"
    __table_args__ = (
        CheckConstraint("weekday between 0 and 6", name="valid_weekday"),
        CheckConstraint("starts_at < ends_at", name="positive_work_period"),
        UniqueConstraint("tenant_id", "weekday", "starts_at"),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("levia.professionals.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int]
    starts_at: Mapped[time]
    ends_at: Mapped[time]


class RateLimit(Base):
    __tablename__ = "rate_limits"
    __table_args__: ClassVar[dict] = {"schema": "levia"}
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    bucket: Mapped[int] = mapped_column(BigInteger)
    count: Mapped[int]


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="service_name_not_blank"),
        CheckConstraint("price_cents between 0 and 9999999", name="service_price_range"),
        CheckConstraint("duration_minutes between 5 and 480", name="service_duration_range"),
        CheckConstraint(
            "return_days IS NULL OR return_days between 1 and 365", name="service_return_range"
        ),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("levia.professionals.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    price_cents: Mapped[int]
    duration_minutes: Mapped[int]
    return_days: Mapped[int | None]
    active: Mapped[bool] = mapped_column(default=True)


class Occupancy(Base):
    """Appointments and blocks share one exclusion-protected timeline."""

    __tablename__ = "occupancies"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="positive_occupancy"),
        CheckConstraint("kind IN ('appointment','block')", name="occupancy_kind"),
        Index("ix_occupancy_lookup", "tenant_id", "starts_at", "ends_at"),
        ForeignKeyConstraint(
            ["tenant_id", "client_id"], ["levia.clients.tenant_id", "levia.clients.id"]
        ),
        UniqueConstraint("tenant_id", "request_key"),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("levia.professionals.id", ondelete="CASCADE"), index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(20))
    cancelled: Mapped[bool] = mapped_column(default=False)
    client_id: Mapped[UUID | None]
    services: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default="[]")
    price_cents: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    source: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    request_key: Mapped[UUID | None]
    return_date: Mapped[date | None]
    notification_email: Mapped[str | None] = mapped_column(String(254))
    notification_version: Mapped[int] = mapped_column(default=0, server_default="0")


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone"),
        UniqueConstraint("tenant_id", "id"),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("levia.professionals.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    invites_allowed: Mapped[bool] = mapped_column(default=False)


class ConsentEvent(Base):
    __tablename__ = "consent_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "client_id"], ["levia.clients.tenant_id", "levia.clients.id"]
        ),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("levia.professionals.id"), index=True)
    client_id: Mapped[UUID]
    allowed: Mapped[bool]
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notice(Base):
    __tablename__ = "notices"
    __table_args__ = (UniqueConstraint("tenant_id", "event_key"), {"schema": "levia"})
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("levia.professionals.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(180))
    title: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(500))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailJob(Base):
    __tablename__ = "email_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_key"),
        ForeignKeyConstraint(
            ["tenant_id", "appointment_id"], ["levia.occupancies.tenant_id", "levia.occupancies.id"]
        ),
        Index("ix_email_jobs_due", "status", "due_at"),
        {"schema": "levia"},
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("levia.professionals.id"), index=True)
    appointment_id: Mapped[UUID]
    version: Mapped[int]
    event_key: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(20))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str]
    payload: Mapped[dict | None] = mapped_column(JSONB)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    first_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    quota_month: Mapped[date | None]
    provider_id: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(40))


class EmailUsage(Base):
    __tablename__ = "email_usage"
    __table_args__ = ({"schema": "levia"},)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("levia.professionals.id"), primary_key=True)
    month: Mapped[date] = mapped_column(primary_key=True)
    reserved: Mapped[int] = mapped_column(default=0)
