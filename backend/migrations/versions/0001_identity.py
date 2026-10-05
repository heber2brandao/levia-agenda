"""Private tenant profile, working periods and shared abuse counters."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DO $$ BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='levia_app') THEN
        CREATE ROLE levia_app NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
      END IF;
    END $$""")
    op.execute("CREATE SCHEMA levia")
    op.execute("REVOKE ALL ON SCHEMA levia FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA levia TO levia_app")
    op.execute("""DO $$ DECLARE role_name text; BEGIN
      FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        IF EXISTS (SELECT FROM pg_roles WHERE rolname=role_name) THEN
          EXECUTE format('REVOKE ALL ON SCHEMA levia FROM %I', role_name);
        END IF;
      END LOOP;
    END $$""")
    op.create_table(
        "professionals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("studio_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(254)),
        sa.Column("specialties", pg.JSONB(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("primary_color", sa.String(7), nullable=False),
        sa.Column("background_color", sa.String(7), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="professional_name_not_blank"),
        sa.CheckConstraint("length(trim(studio_name)) > 0", name="studio_name_not_blank"),
        sa.CheckConstraint("primary_color ~ '^#[0-9a-fA-F]{6}$'", name="primary_color_hex"),
        sa.CheckConstraint("background_color ~ '^#[0-9a-fA-F]{6}$'", name="background_color_hex"),
        schema="levia",
    )
    op.create_table(
        "working_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("levia.professionals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=False),
        sa.Column("ends_at", sa.Time(), nullable=False),
        sa.CheckConstraint("weekday between 0 and 6", name="valid_weekday"),
        sa.CheckConstraint("starts_at < ends_at", name="positive_work_period"),
        sa.UniqueConstraint("tenant_id", "weekday", "starts_at"),
        schema="levia",
    )
    op.create_index(
        "ix_levia_working_periods_tenant_id", "working_periods", ["tenant_id"], schema="levia"
    )
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("bucket", sa.BigInteger(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        schema="levia",
    )
    for table in ("professionals", "working_periods", "rate_limits"):
        op.execute(f"REVOKE ALL ON levia.{table} FROM PUBLIC")
        op.execute(f"""DO $$ DECLARE role_name text; BEGIN
          FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF EXISTS (SELECT FROM pg_roles WHERE rolname=role_name) THEN
              EXECUTE format('REVOKE ALL ON levia.{table} FROM %I', role_name);
            END IF;
          END LOOP;
        END $$""")
        op.execute(f"ALTER TABLE levia.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE levia.{table} FORCE ROW LEVEL SECURITY")
    owner = "owner_id = nullif(current_setting('levia.user_id', true), '')::uuid"
    op.execute(
        f"CREATE POLICY own_profile ON levia.professionals TO levia_app USING ({owner}) WITH CHECK ({owner})"
    )
    period = "EXISTS (SELECT 1 FROM levia.professionals p WHERE p.id = tenant_id)"
    op.execute(
        f"CREATE POLICY own_period ON levia.working_periods TO levia_app USING ({period}) WITH CHECK ({period})"
    )
    op.execute(
        "CREATE POLICY internal_counters ON levia.rate_limits TO levia_app USING (true) WITH CHECK (true)"
    )
    op.execute("GRANT SELECT, INSERT ON levia.professionals TO levia_app")
    op.execute("""GRANT UPDATE (name, studio_name, phone, email, specialties, timezone,
        primary_color, background_color, updated_at) ON levia.professionals TO levia_app""")
    op.execute("GRANT SELECT, INSERT, DELETE ON levia.working_periods TO levia_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON levia.rate_limits TO levia_app")


def downgrade():
    for table in ("rate_limits", "working_periods", "professionals"):
        op.drop_table(table, schema="levia")
    op.execute("DROP SCHEMA levia")
    # Role is retained: it may own connections/credentials outside this migration.
