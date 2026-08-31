"""Shared SQL helpers for active AI field-origin detection."""

# ruff: noqa: ANN401

from typing import Any

from sqlalchemy import exists, select

from wef_backend.features.admin.application.offer_enrichment import OriginKind, OriginState
from wef_backend.features.admin.infrastructure.ai_enrichment_models import OfferFieldOriginRow


def active_ai_origin_exists(offer_id: Any) -> Any:
    """Return an EXISTS predicate for one offer's active AI origins."""
    return exists(
        select(1).where(
            OfferFieldOriginRow.offer_id == offer_id,
            OfferFieldOriginRow.origin == OriginKind.AI.value,
            OfferFieldOriginRow.state == OriginState.ACTIVE.value,
        ),
    )
