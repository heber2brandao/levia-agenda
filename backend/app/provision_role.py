"""Explicit administrator task, run after migrations. Password never printed."""

from getpass import getpass

from psycopg import sql
from sqlalchemy import create_engine

from app.core.config import Settings


def main():
    settings = Settings()
    if not settings.migration_database_url:
        raise SystemExit("Configure LEVIA_MIGRATION_DATABASE_URL primeiro")
    password = getpass("Nova senha exclusiva do papel levia_app (mínimo 24 caracteres): ")
    if len(password) < 24 or password != getpass("Repita a senha: "):
        raise SystemExit("Senha curta ou confirmação diferente")
    engine = create_engine(settings.migration_database_url.get_secret_value(), hide_parameters=True)
    try:
        with engine.begin() as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("ALTER ROLE levia_app LOGIN PASSWORD {}").format(sql.Literal(password))
            )
    finally:
        engine.dispose()
    print("Papel configurado. Guarde a senha no gerenciador de segredos e configure a URL da API.")


if __name__ == "__main__":
    main()
