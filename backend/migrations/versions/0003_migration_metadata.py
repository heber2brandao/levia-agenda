"""Restrict Alembic metadata on hosted databases with public schema defaults."""

from alembic import op

revision = "0003_migration_metadata"
down_revision = "0002_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("REVOKE ALL ON public.alembic_version FROM PUBLIC")
    op.execute("""DO $$ DECLARE r text; BEGIN
      FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN
          EXECUTE format('REVOKE ALL ON public.alembic_version FROM %I', r);
        END IF;
      END LOOP;
    END $$""")
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
