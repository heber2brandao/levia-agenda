"""Stable, unique public booking links; legacy UUID links remain valid."""

from alembic import op

revision = "0008_public_slugs"
down_revision = "0007_notifications"
branch_labels = depends_on = None

UPGRADE_SQL = """
ALTER TABLE levia.professionals ADD COLUMN public_slug varchar(100);
ALTER TABLE levia.professionals ADD CONSTRAINT professionals_public_slug_key UNIQUE(public_slug);
ALTER TABLE levia.professionals ADD CONSTRAINT public_slug_format
  CHECK (public_slug IS NULL OR public_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$');
DO $$
DECLARE item record; stem text; candidate text; suffix integer;
BEGIN
  FOR item IN SELECT id, studio_name FROM levia.professionals ORDER BY created_at,id LOOP
    stem := trim(both '-' from left(regexp_replace(translate(lower(item.studio_name),
      'áàâãäéèêëíìîïóòôõöúùûüçñ', 'aaaaaeeeeiiiiooooouuuucn'), '[^a-z0-9]+', '-', 'g'),70));
    IF stem = '' THEN stem := 'espaco'; END IF;
    IF stem ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
      OR stem ~ '^[0-9a-f]{32}$' THEN stem := 'espaco-' || stem; END IF;
    candidate := stem; suffix := 1;
    WHILE EXISTS (SELECT 1 FROM levia.professionals WHERE public_slug=candidate) LOOP
      suffix := suffix + 1;
      candidate := stem || '-' || suffix::text;
    END LOOP;
    UPDATE levia.professionals SET public_slug=candidate WHERE id=item.id;
  END LOOP;
END $$;
GRANT UPDATE(public_slug) ON levia.professionals TO levia_app;
CREATE POLICY public_profile_slug_lookup ON levia.professionals FOR SELECT TO levia_app
  USING (public_slug=nullif(current_setting('levia.public_slug',true),''));
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute("DROP POLICY public_profile_slug_lookup ON levia.professionals")
    op.execute("ALTER TABLE levia.professionals DROP COLUMN public_slug")
