from base64 import b64encode
import re
import unicodedata
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import current_user
from app.database import tenant_session
from app.models import Professional, WorkingPeriod
from app.schemas import ProfileInput, ProfileOutput

router = APIRouter(prefix="/api/v1/me", tags=["minha conta"])
User = Annotated[UUID, Depends(current_user)]
TenantSession = Annotated[Session, Depends(tenant_session, scope="function")]


def profile_output(session: Session, professional: Professional) -> ProfileOutput:
    periods = session.scalars(
        select(WorkingPeriod)
        .where(WorkingPeriod.tenant_id == professional.id)
        .order_by(WorkingPeriod.weekday, WorkingPeriod.starts_at)
    ).all()
    values = {
        key: getattr(professional, key)
        for key in ProfileInput.model_fields
        if key != "working_periods"
    }
    logo = (
        "data:image/png;base64," + b64encode(professional.logo_png).decode()
        if professional.logo_png
        else None
    )
    return ProfileOutput(id=professional.id, public_slug=professional.public_slug, **values, working_periods=periods, logo=logo)


@router.get("", response_model=ProfileOutput)
def get_profile(user: User, session: TenantSession):
    professional = session.scalar(select(Professional).where(Professional.owner_id == user))
    if professional is None:
        raise HTTPException(404, "Complete seu cadastro")
    return profile_output(session, professional)


@router.put("", response_model=ProfileOutput)
def save_profile(
    data: ProfileInput,
    user: User,
    session: TenantSession,
):
    values = data.model_dump(exclude={"working_periods"})
    normalized = unicodedata.normalize("NFKD", data.studio_name).encode("ascii", "ignore").decode().lower()
    stem = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:70].rstrip("-") or "espaco"
    # Avoid ambiguity with the legacy UUID route.
    try:
        UUID(stem)
        stem = "espaco-" + stem
    except ValueError:
        pass
    for attempt in range(5):
        slug = stem if attempt == 0 else f"{stem}-{uuid4().hex[:8]}"
        statement = insert(Professional).values(id=uuid4(), owner_id=user, public_slug=slug, **values)
        # A later profile edit must never change a shared link.
        statement = statement.on_conflict_do_update(
            index_elements=[Professional.owner_id], set_={
                **values, "updated_at": func.now(),
                "public_slug": func.coalesce(Professional.public_slug, statement.excluded.public_slug),
            }
        ).returning(Professional)
        try:
            with session.begin_nested():
                professional = session.scalars(statement).one()
            break
        except IntegrityError as error:
            if getattr(getattr(error.orig, "diag", None), "constraint_name", None) != "professionals_public_slug_key":
                raise
    else:
        raise HTTPException(409, "Não foi possível gerar o link. Tente salvar novamente.")
    session.execute(delete(WorkingPeriod).where(WorkingPeriod.tenant_id == professional.id))
    session.add_all(
        [WorkingPeriod(tenant_id=professional.id, **p.model_dump()) for p in data.working_periods]
    )
    session.flush()
    return profile_output(session, professional)
