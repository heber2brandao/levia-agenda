from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.auth import current_user
from app.security import consume_limit


def make_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=5,
        max_overflow=0,
        pool_timeout=10,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "prepare_threshold": None},
    )


def check_runtime_role(engine: Engine):
    with engine.connect() as connection:
        safe = connection.scalar(
            text("""
            SELECT current_user = 'levia_app' AND NOT rolsuper AND NOT rolbypassrls
                   AND NOT rolcreaterole AND NOT rolcreatedb
            FROM pg_roles WHERE rolname = current_user
        """)
        )
        if not safe:
            raise RuntimeError("A API exige o papel restrito levia_app")
        owned = connection.scalar(
            text("""
            SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='levia' AND c.relowner=(SELECT oid FROM pg_roles
            WHERE rolname=current_user)
        """)
        )
        if owned:
            raise RuntimeError("O papel da API não pode ser dono das tabelas")
        memberships = connection.scalar(
            text("""
            SELECT count(*) FROM pg_auth_members
            WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user)
        """)
        )
        if memberships:
            raise RuntimeError("O papel da API não pode herdar outros papéis")
        protected = connection.scalar(
            text("""
            SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='levia' AND c.relname IN ('professionals','working_periods','rate_limits','services','occupancies','clients','consent_events','notices','email_jobs','email_usage')
              AND c.relrowsecurity AND c.relforcerowsecurity
        """)
        )
        if protected != 10:
            raise RuntimeError("Aplique as migrações e habilite RLS antes de iniciar a API")


def tenant_session(
    request: Request, user: Annotated[UUID, Depends(current_user)]
) -> Generator[Session]:
    engine = request.app.state.engine
    if engine is None:
        raise HTTPException(503, "Banco de dados ainda não configurado")
    settings = request.app.state.settings
    if not consume_limit(
        engine,
        settings.rate_limit_secret.get_secret_value(),
        "user:" + str(user),
        settings.rate_limit_per_minute,
    ):
        raise HTTPException(429, "Muitas tentativas", headers={"Retry-After": "60"})
    with Session(engine) as session, session.begin():
        session.execute(
            text("SELECT set_config('levia.user_id', :user, true)"), {"user": str(user)}
        )
        yield session
