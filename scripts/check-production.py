"""Read-only deployment preflight. Never prints configuration values/secrets."""
import argparse
import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from pydantic import ValidationError
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings  # noqa: E402


class FileSettings(Settings):
    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        return (init_settings,)


def check(directory: Path, with_email: bool = False):
    errors = []
    for name in (".env", ".env.backend", "secrets/postgres-ca.crt"):
        if not (directory / name).is_file():
            errors.append(f"Falta deploy/{name}")
    if errors:
        return errors
    public = dotenv_values(directory / ".env")
    domain = public.get("DOMAIN") or ""
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", domain):
        errors.append("DOMAIN deve ser um domínio válido, sem protocolo nem caminho")
    if not (public.get("SUPABASE_PUBLISHABLE_KEY") or "").startswith("sb_publishable_"):
        errors.append("Informe somente a chave publicável no arquivo público")
    raw = dotenv_values(directory / ".env.backend")
    # Ignore shell environment: validate exactly the file passed to Compose.
    import json
    values = {}
    try:
        for key, value in raw.items():
            if key.startswith("LEVIA_"):
                name = key[6:].lower()
                values[name] = json.loads(value) if name in {
                    "cors_origins", "allowed_hosts", "worker_owner_ids"
                } else value
        settings = FileSettings(_env_file=None, **values)
    except (ValidationError, ValueError, TypeError):
        return [*errors, "Configuração backend inválida; conferir o modelo e as regras de produção (valores omitidos)"]
    if settings.environment != "production":
        errors.append("Backend deve declarar ENVIRONMENT=production")
    origin = "https://" + domain
    if settings.public_web_url.rstrip("/") != origin or settings.cors_origins != [origin]:
        errors.append("PUBLIC_WEB_URL e CORS devem corresponder ao domínio público")
    if domain not in settings.allowed_hosts or "127.0.0.1" not in settings.allowed_hosts:
        errors.append("ALLOWED_HOSTS deve incluir o domínio e 127.0.0.1 para healthcheck")
    if settings.supabase_url != public.get("SUPABASE_ORIGIN"):
        errors.append("API e frontend devem usar o mesmo projeto Supabase")
    if settings.database_url:
        url = make_url(settings.database_url.get_secret_value())
        if url.username != "levia_app" or url.query.get("sslrootcert") != "/run/secrets/postgres-ca.crt":
            errors.append("Use levia_app e o caminho de certificado montado no contêiner")
    certificate = (directory / "secrets/postgres-ca.crt").read_text(encoding="utf-8")
    if "-----BEGIN CERTIFICATE-----" not in certificate:
        errors.append("O arquivo da autoridade certificadora deve estar em formato PEM")
    if with_email and (not settings.email_enabled or not settings.worker_owner_ids):
        errors.append("Worker exige EMAIL_ENABLED=true e lista explícita WORKER_OWNER_IDS")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "deploy")
    parser.add_argument("--with-email", action="store_true")
    args = parser.parse_args()
    problems = check(args.directory, args.with_email)
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(2)
    print("Configuração validada localmente. DNS, TLS, banco e envios ainda exigem teste no ambiente publicado.")
