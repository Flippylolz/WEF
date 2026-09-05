"""Retain parser release canaries, fair replay work and field lineage."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260905_0024"
down_revision: str | None = "20260905_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ORIGINAL_FIELDS = (
    "market_type",
    "currency",
    "apartment_price_min",
    "apartment_price_max",
    "parking_price_min",
    "parking_price_max",
    "parking_included_in_price",
    "storage_price_min",
    "storage_price_max",
    "storage_included_in_price",
    "area_min_sqm",
    "area_max_sqm",
    "rooms_min",
    "rooms_max",
    "floor_label",
    "delivery_label",
)


def upgrade() -> None:
    """Add metadata without activating replay or copying source text."""
    op.drop_constraint("ck_offer_field_origins_field_name", "offer_field_origins", type_="check")
    old_fields = "field_name IN (" + ", ".join(f"'{name}'" for name in _ORIGINAL_FIELDS) + ")"
    op.create_check_constraint(
        "ck_offer_field_origins_field_name",
        "offer_field_origins",
        old_fields + " OR (origin='parser' AND field_name IN ('content_type','property_type'))",
    )
    for statement in [
        """
CREATE TABLE parser_replay_releases ( version text PRIMARY KEY, parser_version text
NOT NULL, policy_version text NOT NULL, phase text NOT NULL CHECK (phase IN
('canary','running','paused')), reason text, created_at timestamptz NOT NULL DEFAULT
now() )
""",
        """
CREATE TABLE parser_replay_work ( id uuid PRIMARY KEY, release_version text NOT NULL
REFERENCES parser_replay_releases(version), message_id uuid NOT NULL REFERENCES
source_messages(id) ON DELETE CASCADE, revision_id uuid NOT NULL REFERENCES
source_message_revisions(id) ON DELETE CASCADE, state text NOT NULL CHECK (state IN
('queued','claimed','observed','updated','unchanged',
'source_absent','excluded','deferred','protected_conflict','failed')), canary_passed
boolean NOT NULL DEFAULT false, reason text, claim_id uuid, lease_until timestamptz,
attempts integer NOT NULL DEFAULT 0, next_eligible_at timestamptz NOT NULL DEFAULT
now(), updated_at timestamptz NOT NULL DEFAULT now(),
UNIQUE(revision_id,release_version) )
""",
        """
CREATE INDEX ix_parser_replay_due ON
parser_replay_work(release_version,state,next_eligible_at,id)
""",
        """
CREATE TABLE parser_replay_field_events ( id uuid PRIMARY KEY, work_id uuid NOT NULL
REFERENCES parser_replay_work(id) ON DELETE CASCADE, offer_id uuid NOT NULL
REFERENCES offers(id) ON DELETE CASCADE, field_name text NOT NULL, before_value
jsonb, after_value jsonb, before_origin jsonb, reverted_at timestamptz,
rollback_reason text, parser_version text NOT NULL, source_start integer NOT NULL,
source_end integer NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
UNIQUE(work_id,field_name), CHECK(source_start>=0 AND source_end>source_start) )
""",
    ]:
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Drop only metadata; this does not reverse canonical field writes."""
    op.execute("DROP TABLE parser_replay_field_events, parser_replay_work, parser_replay_releases")
    op.execute(
        "DELETE FROM offer_field_origins WHERE field_name IN ('content_type','property_type')"
    )
    op.drop_constraint("ck_offer_field_origins_field_name", "offer_field_origins", type_="check")
    old_fields = "field_name IN (" + ", ".join(f"'{name}'" for name in _ORIGINAL_FIELDS) + ")"
    op.create_check_constraint(
        "ck_offer_field_origins_field_name", "offer_field_origins", old_fields
    )
