"""Add fenced location revalidation and immutable observation/application receipts."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260906_0026"
down_revision: str | None = "20260906_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create empty metadata only; never move existing points during migration."""
    statements = """
        CREATE TABLE location_validation_control (
            target varchar(160) PRIMARY KEY,
            cursor_id uuid,
            mode varchar(16) NOT NULL DEFAULT 'observe'
                CHECK (mode IN ('off', 'observe', 'apply')),
            discovery_ready boolean NOT NULL DEFAULT false,
            canary_ids jsonb NOT NULL DEFAULT '[]',
            canary_verified boolean NOT NULL DEFAULT false,
            next_eligible_at timestamptz NOT NULL DEFAULT now(),
            operator_actions integer NOT NULL DEFAULT 0,
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE location_validation_work (
            id uuid PRIMARY KEY,
            location_id uuid NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
            source_fingerprint varchar(64) NOT NULL,
            target varchar(160) NOT NULL REFERENCES location_validation_control(target),
            source_json jsonb NOT NULL,
            selection_version integer NOT NULL,
            state varchar(24) NOT NULL DEFAULT 'pending'
                CHECK (state IN ('pending','leased','deferred','observed','terminal','exception')),
            mode varchar(16) NOT NULL DEFAULT 'observe',
            fence integer NOT NULL DEFAULT 0,
            lease_until timestamptz,
            next_attempt_at timestamptz NOT NULL DEFAULT now(),
            failures integer NOT NULL DEFAULT 0,
            outcome varchar(48),
            observation_result_id uuid REFERENCES geocode_results(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(location_id, source_fingerprint, target)
        );
        CREATE INDEX ix_location_validation_pending
            ON location_validation_work(target, state, next_attempt_at, id);
        CREATE TABLE location_validation_receipts (
            id uuid PRIMARY KEY,
            work_id uuid NOT NULL REFERENCES location_validation_work(id) ON DELETE CASCADE,
            mode varchar(16) NOT NULL CHECK (mode IN ('observe','apply')),
            before_json jsonb NOT NULL,
            after_json jsonb NOT NULL,
            outcome varchar(48) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(work_id, mode)
        );
    """
    for statement in statements.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Remove empty/reviewed metadata only when the operator chooses downgrade."""
    op.execute("DROP TABLE location_validation_receipts")
    op.execute("DROP TABLE location_validation_work")
    op.execute("DROP TABLE location_validation_control")
