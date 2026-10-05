"""Tenant-scoped transactional notices, outbox and quota ledger."""

from alembic import op

revision = "0007_notifications"
down_revision = "0006_extension_schema"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE levia.professionals ADD COLUMN monthly_email_limit integer NOT NULL DEFAULT 100
      CHECK (monthly_email_limit BETWEEN 0 AND 100000);
    ALTER TABLE levia.occupancies ADD COLUMN notification_email varchar(254);
    ALTER TABLE levia.occupancies ADD COLUMN notification_version integer NOT NULL DEFAULT 0;
    ALTER TABLE levia.occupancies ADD CONSTRAINT occupancy_tenant_id UNIQUE (tenant_id,id);
    GRANT UPDATE(notification_version) ON levia.occupancies TO levia_app;
    CREATE TABLE levia.notices (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES levia.professionals(id),
      event_key varchar(180) NOT NULL, title varchar(100) NOT NULL, message varchar(500) NOT NULL,
      due_at timestamptz NOT NULL, read_at timestamptz, UNIQUE(tenant_id,event_key));
    CREATE INDEX ix_notices_tenant_due ON levia.notices(tenant_id,due_at DESC);
    CREATE TABLE levia.email_jobs (
      id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES levia.professionals(id),
      appointment_id uuid NOT NULL, version integer NOT NULL, event_key varchar(180) NOT NULL,
      kind varchar(20) NOT NULL, recipient varchar(254) NOT NULL, subject varchar(200) NOT NULL,
      body text NOT NULL, payload jsonb, due_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
      status varchar(20) NOT NULL CHECK(status IN ('pending','processing','accepted','skipped','quota','failed','review')),
      attempts integer NOT NULL DEFAULT 0, first_attempt_at timestamptz, lease_until timestamptz,
      lease_token uuid, quota_month date, provider_id varchar(100), error_code varchar(40),
      UNIQUE(tenant_id,event_key),
      FOREIGN KEY(tenant_id,appointment_id) REFERENCES levia.occupancies(tenant_id,id));
    CREATE INDEX ix_email_jobs_due ON levia.email_jobs(status,due_at);
    CREATE INDEX ix_email_jobs_tenant ON levia.email_jobs(tenant_id);
    CREATE INDEX ix_email_jobs_appointment ON levia.email_jobs(tenant_id,appointment_id);
    CREATE TABLE levia.email_usage (
      tenant_id uuid NOT NULL REFERENCES levia.professionals(id), month date NOT NULL,
      reserved integer NOT NULL DEFAULT 0 CHECK(reserved >= 0), PRIMARY KEY(tenant_id,month));
    """)
    predicate = "EXISTS (SELECT 1 FROM levia.professionals p WHERE p.id=tenant_id AND p.owner_id=nullif(current_setting('levia.user_id',true),'')::uuid)"
    for table in ("notices", "email_jobs", "email_usage"):
        op.execute(f"ALTER TABLE levia.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE levia.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON levia.{table} FROM PUBLIC, anon, authenticated, service_role")
        op.execute(
            f"CREATE POLICY own_{table} ON levia.{table} TO levia_app USING ({predicate}) WITH CHECK ({predicate})"
        )
        op.execute(f"GRANT SELECT, INSERT ON levia.{table} TO levia_app")
    op.execute("GRANT UPDATE(read_at) ON levia.notices TO levia_app")
    op.execute("GRANT UPDATE ON levia.email_jobs,levia.email_usage TO levia_app")


def downgrade():
    for table in ("email_usage", "email_jobs", "notices"):
        op.execute(f"DROP TABLE levia.{table}")
    op.execute("ALTER TABLE levia.occupancies DROP CONSTRAINT occupancy_tenant_id")
    op.execute(
        "ALTER TABLE levia.occupancies DROP COLUMN notification_email, DROP COLUMN notification_version"
    )
    op.execute("ALTER TABLE levia.professionals DROP COLUMN monthly_email_limit")
