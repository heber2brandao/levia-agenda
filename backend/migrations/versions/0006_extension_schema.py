"""Keep the overlap-index extension outside the exposed public schema."""

from alembic import op

revision = "0006_extension_schema"
down_revision = "0005_bookings"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute("ALTER EXTENSION btree_gist SET SCHEMA extensions")
    op.execute("GRANT USAGE ON SCHEMA extensions TO levia_app")


def downgrade():
    op.execute("ALTER EXTENSION btree_gist SET SCHEMA public")
