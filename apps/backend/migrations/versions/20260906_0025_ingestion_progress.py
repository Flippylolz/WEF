"""Persist bounded ingestion progress observations and deduplicated incidents."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260906_0025"
down_revision: str | None = "20260905_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add monitoring state without rewriting source, retries or recovery ownership."""
    statements = """
    CREATE TABLE ingestion_progress_controls (
        channel varchar(80) PRIMARY KEY, enabled boolean NOT NULL DEFAULT false,
        enabled_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE ingestion_progress_checkpoints (
        channel varchar(80) NOT NULL, stage varchar(32) NOT NULL,
        payload jsonb NOT NULL, PRIMARY KEY(channel,stage)
    );
    CREATE TABLE ingestion_progress_samples (
        channel varchar(80) NOT NULL, sampled_at timestamptz NOT NULL,
        payload jsonb NOT NULL, PRIMARY KEY(channel,sampled_at)
    );
    CREATE TABLE ingestion_progress_incidents (
        id uuid PRIMARY KEY, channel varchar(80) NOT NULL, stage varchar(32) NOT NULL,
        reason varchar(64) NOT NULL, opened_at timestamptz NOT NULL,
        closed_at timestamptz
    );
    CREATE UNIQUE INDEX uq_ingestion_progress_open_incident
        ON ingestion_progress_incidents(channel,stage) WHERE closed_at IS NULL;
    CREATE TABLE ingestion_observation_counters (
        channel varchar(80) NOT NULL, name varchar(40) NOT NULL,
        value bigint NOT NULL CHECK(value >= 0), since timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(channel,name)
    );
    """
    for statement in statements.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Remove monitoring metadata only after explicitly disabling its worker."""
    for table in (
        "ingestion_observation_counters",
        "ingestion_progress_incidents",
        "ingestion_progress_samples",
        "ingestion_progress_checkpoints",
        "ingestion_progress_controls",
    ):
        op.drop_table(table)
