"""Persist shared AI reservations, pacing and source-recovery checkpoints."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260905_0022"
down_revision: str | None = "20260905_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add metadata only; never submit requests or modify canonical offers."""
    statements = """
        CREATE TABLE ai_provider_accounts (
            owner_id uuid PRIMARY KEY, budget_day date NOT NULL,
            used integer NOT NULL CHECK (used >= 0),
            next_eligible_at timestamptz NOT NULL,
            attempt_id uuid, lease_until timestamptz
        );
        CREATE TABLE ai_provider_attempts (
            id uuid PRIMARY KEY, owner_id uuid NOT NULL, operation_id uuid,
            work_key varchar(64) NOT NULL,
            ordinal integer NOT NULL CHECK (ordinal > 0),
            state varchar(24) NOT NULL CHECK (state IN
                ('submitting','succeeded','rate_limited','retry','terminal','uncertain')),
            reason varchar(40), created_at timestamptz NOT NULL,
            finished_at timestamptz, next_eligible_at timestamptz,
            token_input integer, token_output integer, provider_request_id varchar(128),
            UNIQUE (owner_id, work_key, ordinal)
        );
        CREATE INDEX ix_ai_provider_attempt_owner ON ai_provider_attempts(owner_id, created_at);
        CREATE TABLE ai_recovery_work (
            id uuid PRIMARY KEY, evaluation_id uuid NOT NULL REFERENCES parse_evaluations(id)
                ON DELETE CASCADE,
            source_revision_id uuid NOT NULL REFERENCES source_message_revisions(id)
                ON DELETE CASCADE,
            parser_version varchar(40) NOT NULL, policy_version varchar(40) NOT NULL,
            schema_version varchar(80) NOT NULL,
            state varchar(24) NOT NULL CHECK (state IN
                ('queued','claimed','validated','observed','applied','deferred','terminal','superseded')),
            missing_fields jsonb NOT NULL, owner_id uuid NOT NULL,
            claim_id uuid, lease_until timestamptz, attempts integer NOT NULL DEFAULT 0,
            next_eligible_at timestamptz NOT NULL, proposal_id uuid, cohort_id uuid,
            local_failures integer NOT NULL DEFAULT 0,
            reason varchar(40), created_at timestamptz NOT NULL,
            updated_at timestamptz NOT NULL,
            UNIQUE (source_revision_id, parser_version, policy_version, schema_version)
        );
        CREATE INDEX ix_ai_recovery_due ON ai_recovery_work(state, next_eligible_at, id);
    """
    for statement in statements.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Explicit downgrade drops only recovery metadata; disable workers first."""
    for table in ("ai_recovery_work", "ai_provider_attempts", "ai_provider_accounts"):
        op.drop_table(table)
