"""Atomic source-evidence evaluation and append-only resolution history."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.parse_quality import (
    ParseClassification,
    classify_parse,
)
from wef_backend.features.ingestion.infrastructure.models import (
    ParseEvaluationRow,
    ParseEvaluationTransitionRow,
    SourceMessageRow,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from wef_backend.features.ingestion.domain.extraction import ExtractionResult


async def record_parse_evaluation(
    session: AsyncSession,
    *,
    message_id: UUID,
    revision_id: UUID,
    text: str,
    extraction: ExtractionResult,
) -> bool:
    """Serialize current-revision evaluations; return whether a new one landed."""
    current_revision = await session.scalar(
        select(SourceMessageRow.current_revision_id)
        .where(SourceMessageRow.id == message_id)
        .with_for_update(),
    )
    if current_revision != revision_id:
        return False
    previous = (
        await session.scalars(
            select(ParseEvaluationRow).where(
                ParseEvaluationRow.source_message_id == message_id,
                ParseEvaluationRow.state == "open",
            ),
        )
    ).all()
    older = any(
        row.source_message_revision_id == revision_id
        and _older_generation(extraction.decision.parser_version, row.parser_version)
        for row in previous
    )
    quality = classify_parse(text, extraction)
    evaluation_id = uuid4()
    inserted = await session.scalar(
        insert(ParseEvaluationRow)
        .values(
            id=evaluation_id,
            source_message_id=message_id,
            source_message_revision_id=revision_id,
            parser_version=extraction.decision.parser_version,
            policy_version=quality.policy_version,
            classification=quality.classification.value,
            recovery_eligible=quality.recovery_eligible and not older,
            fields_json=[
                {
                    "field_name": field.field_name,
                    "classification": field.classification.value,
                    "spans": [{"start": span.start, "end": span.end} for span in field.spans],
                }
                for field in quality.fields
            ],
            state="superseded" if older else "open",
        )
        .on_conflict_do_nothing(constraint="uq_parse_evaluation_identity")
        .returning(ParseEvaluationRow.id),
    )
    if inserted is None:
        return False
    if older:
        return False
    repaired = {
        field.field_name
        for field in quality.fields
        if field.classification is ParseClassification.COMPLETE
    }
    for row in previous:
        prior_fields = row.fields_json if isinstance(row.fields_json, list) else []
        gaps = {
            field["field_name"]
            for field in prior_fields
            if field.get("classification") in {"extraction_miss", "conflicting"}
        }
        state = (
            "resolved"
            if row.source_message_revision_id == revision_id and gaps and gaps <= repaired
            else "superseded"
        )
        row.state = state
        session.add(
            ParseEvaluationTransitionRow(
                id=uuid4(), evaluation_id=row.id, caused_by_id=evaluation_id, state=state
            )
        )
    return True


def _older_generation(candidate: str, previous: str) -> bool:
    """Compare numbered generations only within the same parser family."""
    left = re.fullmatch(r"(.+?)(\d+)", candidate)
    right = re.fullmatch(r"(.+?)(\d+)", previous)
    return bool(left and right and left[1] == right[1] and int(left[2]) < int(right[2]))
