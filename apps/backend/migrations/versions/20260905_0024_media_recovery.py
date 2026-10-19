"""Persist canonical media intentions, bounded recovery and discovery state."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260905_0024"
down_revision: str | None = "20260905_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add recovery metadata without rewriting canonical source or storage evidence."""
    statements = """
    CREATE TABLE media_recovery_intentions (
        source_revision_id uuid PRIMARY KEY
            REFERENCES source_message_revisions(id) ON DELETE CASCADE,
        discovered boolean NOT NULL DEFAULT false, context_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE media_recovery_work (
        id uuid PRIMARY KEY,
        source_revision_id uuid NOT NULL REFERENCES source_message_revisions(id) ON DELETE CASCADE,
        ordinal integer NOT NULL, descriptor_identity varchar(64) NOT NULL,
        grouping_version varchar(40) NOT NULL, transform_version varchar(40) NOT NULL,
        policy_version varchar(80) NOT NULL, descriptor_json jsonb NOT NULL,
        offer_id uuid REFERENCES offers(id),
        association_revision_id uuid REFERENCES source_message_revisions(id),
        association_rule varchar(40), association_confidence numeric(4,3),
        state varchar(24) NOT NULL, next_attempt_at timestamptz NOT NULL,
        lease_token uuid, lease_until timestamptz, data_failures integer NOT NULL DEFAULT 0,
        deferrals integer NOT NULL DEFAULT 0, reason varchar(80),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_media_recovery_identity UNIQUE
            (source_revision_id,ordinal,descriptor_identity,grouping_version,transform_version),
        CONSTRAINT ck_media_recovery_counters CHECK
            (ordinal >= 0 AND data_failures >= 0 AND deferrals >= 0),
        CONSTRAINT ck_media_recovery_state CHECK (state IN
            ('pending','leased','retry_wait','completed','unsupported','superseded','quarantined'))
    );
    CREATE INDEX ix_media_recovery_due ON media_recovery_work(state,next_attempt_at,id);
    CREATE TABLE media_recovery_channels (
        source_channel_id uuid PRIMARY KEY REFERENCES source_channels(id) ON DELETE CASCADE,
        scan_after_id bigint NOT NULL DEFAULT 0, scan_upper_id bigint,
        grouping_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        phase varchar(16) NOT NULL DEFAULT 'canary', canary_completed integer NOT NULL DEFAULT 0,
        source_retry_at timestamptz, reason varchar(80)
    );
    """
    for statement in statements.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Remove only recovery metadata after an explicitly paused recovery runner."""
    for table in ("media_recovery_work", "media_recovery_intentions", "media_recovery_channels"):
        op.drop_table(table)
