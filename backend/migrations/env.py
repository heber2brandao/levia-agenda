from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import Settings
from app.models import Base

settings = Settings()
secret = settings.migration_database_url
if not secret:
    raise RuntimeError("Configure LEVIA_MIGRATION_DATABASE_URL com o papel de migrações")
url = secret.get_secret_value()
if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        include_schemas=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, include_schemas=True
        )
        with context.begin_transaction():
            context.run_migrations()
