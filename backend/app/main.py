from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import TokenVerifier
from app.bookings import public as public_router
from app.bookings import router as bookings_router
from app.catalog import router as catalog_router
from app.core.config import Settings
from app.database import check_runtime_role, make_engine
from app.logos import router as logos_router
from app.notifications import router as notifications_router
from app.profiles import router
from app.security import SecurityMiddleware


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    stage: Literal["operations"] = "operations"
    database_configured: bool = False
    auth_configured: bool = False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        if settings.database_url:
            app.state.engine = make_engine(settings.database_url.get_secret_value())
            try:
                check_runtime_role(app.state.engine)
                yield
            finally:
                app.state.engine.dispose()
        else:
            yield

    app = FastAPI(
        title=settings.app_name,
        version="0.6.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        openapi_url=None if settings.environment == "production" else "/openapi.json",
    )
    app.state.engine = None
    app.state.settings = settings
    app.state.verifier = (
        TokenVerifier(settings.supabase_url + "/auth/v1", settings.jwt_audience)
        if settings.supabase_url
        else None
    )
    app.add_middleware(SecurityMiddleware, state=app.state, settings=settings)
    if settings.environment == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(router)
    app.include_router(notifications_router)
    app.include_router(catalog_router)
    app.include_router(logos_router)
    app.include_router(bookings_router)
    app.include_router(public_router)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Never echo input values: they can contain personal data or credentials.
        return JSONResponse({"detail": "Confira os campos informados"}, 422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse({"detail": "Não foi possível acessar seus dados"}, 503)

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse(
            {"detail": "Horário ocupado ou operação conflitante. Atualize e tente novamente."}, 409
        )

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["infraestrutura"])
    def health() -> HealthResponse:
        """Liveness somente: não verifica banco, autenticação ou provedores."""
        return HealthResponse(
            database_configured=bool(settings.database_url),
            auth_configured=bool(settings.supabase_url),
        )

    @app.get("/api/v1/ready", tags=["infraestrutura"])
    def ready():
        if app.state.engine is not None:
            try:
                with app.state.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return {"status": "ready"}
            except SQLAlchemyError:
                pass
        return JSONResponse({"status": "unavailable"}, 503)

    return app


app = create_app()
