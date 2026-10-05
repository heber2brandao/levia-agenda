from urllib.parse import urlparse
from uuid import UUID

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEVIA_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    app_name: str = "Levia Agenda"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    supabase_url: str = ""
    jwt_audience: str = "authenticated"
    rate_limit_secret: SecretStr | None = None
    rate_limit_per_minute: int = 60
    environment: str = "development"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    email_enabled: bool = False
    resend_api_key: SecretStr | None = None
    email_from: str = ""
    public_web_url: str = ""
    email_unsubscribe_secret: SecretStr | None = None
    worker_owner_ids: list[UUID] = []
    worker_poll_seconds: int = 30

    @model_validator(mode="after")
    def validate_security_config(self):
        if not 5 <= self.worker_poll_seconds <= 300:
            raise ValueError("Intervalo do worker deve estar entre 5 e 300 segundos")
        if self.email_enabled:
            from pydantic import EmailStr, TypeAdapter

            TypeAdapter(EmailStr).validate_python(self.email_from)
            parsed_web = urlparse(self.public_web_url)
            if (
                parsed_web.scheme != "https"
                or not parsed_web.hostname
                or parsed_web.username
                or parsed_web.password
                or parsed_web.query
                or parsed_web.fragment
                or parsed_web.path not in ("", "/")
            ):
                raise ValueError("Envios exigem PUBLIC_WEB_URL como origem HTTPS")
            if (
                not self.resend_api_key
                or not self.email_unsubscribe_secret
                or len(self.email_unsubscribe_secret.get_secret_value()) < 32
            ):
                raise ValueError(
                    "Envios exigem chave Resend e segredo de revogação de 32 caracteres"
                )
        self.supabase_url = self.supabase_url.rstrip("/")
        if self.supabase_url:
            parsed = urlparse(self.supabase_url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("SUPABASE_URL deve ser a origem HTTPS do projeto")
        if self.database_url:
            database = make_url(self.database_url.get_secret_value())
            if database.drivername != "postgresql+psycopg":
                raise ValueError("Use PostgreSQL com o driver psycopg")
            if self.environment == "production" and database.query.get("sslmode") != "verify-full":
                raise ValueError("Produção exige sslmode=verify-full para o banco")
        if not 1 <= self.rate_limit_per_minute <= 600:
            raise ValueError("Limite deve estar entre 1 e 600")
        if self.database_url and (
            not self.rate_limit_secret or len(self.rate_limit_secret.get_secret_value()) < 32
        ):
            raise ValueError("Configure RATE_LIMIT_SECRET com no mínimo 32 caracteres")
        if self.environment == "production":
            if not self.database_url or not self.supabase_url:
                raise ValueError("Produção exige banco e Supabase")
            if not self.allowed_hosts or any(
                not host or "*" in host or "/" in host or ":" in host for host in self.allowed_hosts
            ):
                raise ValueError("Produção exige hosts explícitos, sem curingas")
            if not self.cors_origins:
                raise ValueError("Configure a origem pública do frontend")
            for origin in [*self.cors_origins, self.public_web_url]:
                parsed = urlparse(origin)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.path not in ("", "/")
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValueError("Produção exige origens HTTPS explícitas")
            if self.migration_database_url:
                raise ValueError(
                    "Não disponibilize credenciais de migração na aplicação de produção"
                )
        return self
