"""Real appointments, clients, consent history and transactional conflict protection."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0005_bookings"
down_revision = "0004_professional_logo"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("SET LOCAL search_path = public, extensions")
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("levia.professionals.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(254)),
        sa.Column("invites_allowed", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("tenant_id", "phone"),
        sa.UniqueConstraint("tenant_id", "id"),
        schema="levia",
    )
    op.create_table(
        "consent_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("levia.professionals.id"), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "client_id"], ["levia.clients.tenant_id", "levia.clients.id"]
        ),
        schema="levia",
    )
    for table in ("clients", "consent_events"):
        op.create_index(f"ix_levia_{table}_tenant_id", table, ["tenant_id"], schema="levia")
        op.execute(f"REVOKE ALL ON levia.{table} FROM PUBLIC")
        op.execute(
            f"""DO $$ DECLARE r text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON levia.{table} FROM %I',r); END IF; END LOOP; END $$"""
        )
        op.execute(f"ALTER TABLE levia.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE levia.{table} FORCE ROW LEVEL SECURITY")
        predicate = "EXISTS (SELECT 1 FROM levia.professionals p WHERE p.id=tenant_id AND p.owner_id=nullif(current_setting('levia.user_id',true),'')::uuid)"
        op.execute(
            f"CREATE POLICY own_{table} ON levia.{table} TO levia_app USING ({predicate}) WITH CHECK ({predicate})"
        )
        op.execute(f"GRANT SELECT, INSERT ON levia.{table} TO levia_app")
    op.execute("GRANT UPDATE(name,phone,email,invites_allowed) ON levia.clients TO levia_app")
    for column in [
        sa.Column("client_id", sa.Uuid()),
        sa.Column("services", pg.JSONB(), nullable=False, server_default="[]"),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("request_key", sa.Uuid()),
        sa.Column("return_date", sa.Date()),
    ]:
        op.add_column("occupancies", column, schema="levia")
    op.create_foreign_key(
        "occupancy_client",
        "occupancies",
        "clients",
        ["tenant_id", "client_id"],
        ["tenant_id", "id"],
        source_schema="levia",
        referent_schema="levia",
    )
    op.create_unique_constraint(
        "occupancy_request", "occupancies", ["tenant_id", "request_key"], schema="levia"
    )
    op.create_check_constraint(
        "occupancy_status",
        "occupancies",
        "status IN ('pending','confirmed','completed','cancelled')",
        schema="levia",
    )
    op.execute(
        "ALTER TABLE levia.occupancies ADD CONSTRAINT no_overlap EXCLUDE USING gist (tenant_id WITH =, tstzrange(starts_at,ends_at,'[)') WITH &&) WHERE (NOT cancelled)"
    )
    op.execute("GRANT INSERT ON levia.occupancies TO levia_app")
    op.execute(
        "GRANT UPDATE(starts_at,ends_at,cancelled,status,return_date) ON levia.occupancies TO levia_app"
    )
    # Internal API bootstrap only; database credentials are never public. Routes expose a safe DTO.
    op.execute(
        "CREATE POLICY public_profile_lookup ON levia.professionals FOR SELECT TO levia_app USING (id=nullif(current_setting('levia.public_tenant',true),'')::uuid)"
    )


def downgrade():
    op.execute("DROP POLICY public_profile_lookup ON levia.professionals")
    op.execute("REVOKE INSERT, UPDATE ON levia.occupancies FROM levia_app")
    for name in ("no_overlap", "occupancy_status", "occupancy_request", "occupancy_client"):
        op.execute(f"ALTER TABLE levia.occupancies DROP CONSTRAINT {name}")
    for name in (
        "return_date",
        "request_key",
        "source",
        "status",
        "price_cents",
        "services",
        "client_id",
    ):
        op.drop_column("occupancies", name, schema="levia")
    op.drop_table("consent_events", schema="levia")
    op.drop_table("clients", schema="levia")
