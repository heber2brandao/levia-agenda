"""Tenant catalogue and read-only occupancy foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0002_catalog"
down_revision = "0001_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("levia.professionals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("return_days", sa.Integer()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="service_name_not_blank"),
        sa.CheckConstraint("price_cents between 0 and 9999999", name="service_price_range"),
        sa.CheckConstraint("duration_minutes between 5 and 480", name="service_duration_range"),
        sa.CheckConstraint(
            "return_days IS NULL OR return_days between 1 and 365", name="service_return_range"
        ),
        schema="levia",
    )
    op.create_table(
        "occupancies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("levia.professionals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.CheckConstraint("starts_at < ends_at", name="positive_occupancy"),
        sa.CheckConstraint("kind IN ('appointment','block')", name="occupancy_kind"),
        schema="levia",
    )
    for table in ("services", "occupancies"):
        op.create_index(f"ix_levia_{table}_tenant_id", table, ["tenant_id"], schema="levia")
        op.execute(f"ALTER TABLE levia.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE levia.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON levia.{table} FROM PUBLIC")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
          FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN
              EXECUTE format('REVOKE ALL ON levia.{table} FROM %I', r);
            END IF;
          END LOOP;
        END $$""")
        owned = "EXISTS (SELECT 1 FROM levia.professionals p WHERE p.id = tenant_id)"
        op.execute(
            f"CREATE POLICY own_{table} ON levia.{table} TO levia_app USING ({owned}) WITH CHECK ({owned})"
        )
    op.create_index(
        "ix_occupancy_lookup", "occupancies", ["tenant_id", "starts_at", "ends_at"], schema="levia"
    )
    op.execute("GRANT SELECT, INSERT ON levia.services TO levia_app")
    op.execute(
        "GRANT UPDATE (name,price_cents,duration_minutes,return_days,active) ON levia.services TO levia_app"
    )
    op.execute("GRANT SELECT ON levia.occupancies TO levia_app")


def downgrade():
    op.drop_table("occupancies", schema="levia")
    op.drop_table("services", schema="levia")
