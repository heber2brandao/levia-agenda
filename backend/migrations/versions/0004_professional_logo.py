"""Small normalized logo, protected by the existing profile RLS."""

import sqlalchemy as sa
from alembic import op

revision = "0004_professional_logo"
down_revision = "0003_migration_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "professionals", sa.Column("logo_png", sa.LargeBinary(), nullable=True), schema="levia"
    )
    op.create_check_constraint(
        "logo_size",
        "professionals",
        "logo_png IS NULL OR octet_length(logo_png) <= 270000",
        schema="levia",
    )
    op.execute("GRANT UPDATE (logo_png) ON levia.professionals TO levia_app")


def downgrade():
    op.drop_constraint("logo_size", "professionals", schema="levia", type_="check")
    op.drop_column("professionals", "logo_png", schema="levia")
