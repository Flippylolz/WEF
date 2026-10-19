"""Failure boundaries for parser evidence, media ownership and worker health."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict

import pytest

from tests.test_listing_extraction import _candidate
from wef_backend.features.catalog.domain import ContentType
from wef_backend.features.contacts.domain.model import ContactKind as RevealContactKind
from wef_backend.features.contacts.domain.model import normalize_contact_value
from wef_backend.features.ingestion.domain import (
    CandidateDecision,
    Confidence,
    ContactKind,
    ExtractionWarning,
    ExtractionWarningCode,
    JSONValueError,
    LinkKind,
    MediaDescriptor,
    MediaKind,
    RuleProvenance,
    SourceSpan,
    canonical_json_bytes,
    freeze_json,
)
from wef_backend.features.ingestion.domain.extraction import ContactSpan, LinkSpan
from wef_backend.features.ingestion.domain.geocode_candidates import choose_geocode_candidate
from wef_backend.features.ingestion.domain.geocoding import (
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    SelectionReason,
    address_agreement_reason,
    normalize_geocode_query,
)
from wef_backend.features.ingestion.domain.media_grouping import (
    MediaAssociation,
    MediaAssociationRule,
    MediaReference,
)
from wef_backend.features.ingestion.domain.media_storage import (
    MediaObservation,
    MediaType,
    ObservationReason,
    ObservationStatus,
    StorageClass,
    StoredObject,
    VerifiedOriginal,
)
from wef_backend.features.ingestion.domain.telegram_worker_ops import (
    CriticalStageStatus,
    WorkerRuntimeHealth,
)


class _DecisionChanges(TypedDict, total=False):
    parser_version: str
    threshold: int
    is_candidate: bool
    content_type: ContentType | None


class _ListingChanges(TypedDict, total=False):
    source_message_id: int
    source_checksum: str
    parser_version: str


@pytest.mark.parametrize(
    "changes",
    [
        {"parser_version": ""},
        {"threshold": 0},
        {"is_candidate": True},
        {"content_type": ContentType.UNIT},
    ],
)
def test_candidate_decision_rejects_inconsistent_identity_and_classification(
    changes: _DecisionChanges,
) -> None:
    decision = CandidateDecision(
        parser_version="fixture-v1",
        is_candidate=False,
        score=0,
        threshold=1,
        content_type=None,
        signals=(),
    )
    with pytest.raises(ValueError, match=r"candidate|non-candidates"):
        replace(decision, **changes)


@pytest.mark.parametrize(
    "changes", [{"source_message_id": 0}, {"source_checksum": ""}, {"parser_version": ""}]
)
def test_listing_requires_source_identity(changes: _ListingChanges) -> None:
    listing = _candidate("For sale | Apartment\nPrice: 500 000 PLN").listing
    assert listing is not None
    with pytest.raises(ValueError, match="source identity and parser version"):
        replace(listing, **changes)


def test_contact_and_link_evidence_must_belong_to_their_rule() -> None:
    span = SourceSpan(0, 1)
    unrelated = SourceSpan(2, 3)
    provenance = RuleProvenance("fixture", "v1", Confidence.HIGH, (span,))
    with pytest.raises(ValueError, match="matching source provenance"):
        ContactSpan(ContactKind.TELEGRAM, "synthetic", unrelated, provenance)
    with pytest.raises(ValueError, match="requires a value"):
        ContactSpan(ContactKind.TELEGRAM, "", span, provenance)
    with pytest.raises(ValueError, match="HTTP URL"):
        LinkSpan(LinkKind.GOOGLE_MAPS, "ftp://example.invalid", span, provenance)
    with pytest.raises(ValueError, match="matching source provenance"):
        LinkSpan(LinkKind.GOOGLE_MAPS, "https://example.invalid", unrelated, provenance)


def test_warning_requires_a_stable_field_name() -> None:
    with pytest.raises(ValueError, match="requires a field name"):
        ExtractionWarning(ExtractionWarningCode.INVALID_RANGE, "")


@pytest.mark.parametrize(("listing_id", "version"), [(0, "v1"), (1, "")])
def test_media_associations_require_identity_and_version(listing_id: int, version: str) -> None:
    reference = MediaReference(1, 0, MediaDescriptor(MediaKind.PHOTO, "fixture.jpg"))
    with pytest.raises(ValueError, match="listing identity and grouping version"):
        MediaAssociation(
            reference, listing_id, MediaAssociationRule.SAME_MESSAGE, Confidence.HIGH, version
        )


def test_unread_media_cannot_carry_a_stored_original() -> None:
    stored = StoredObject(
        StorageClass.RESTRICTED_ORIGINAL, "v1/a/b/fixture.jpg", "a" * 64, "image/jpeg", 1
    )
    original = VerifiedOriginal(stored, MediaType.IMAGE, "image/jpeg", 1, 1, None)
    with pytest.raises(ValueError, match="only safely read observations carry a stored original"):
        MediaObservation(
            ObservationStatus.UNREAD_REJECTED,
            ObservationReason.MISSING,
            "fixture",
            None,
            None,
            original,
        )


def test_verified_media_requires_its_original() -> None:
    with pytest.raises(ValueError, match="only verified observations carry a stored original"):
        MediaObservation(
            ObservationStatus.READ_OBSERVED, ObservationReason.VERIFIED, "fixture", "a" * 64, 1
        )


def test_checksum_mismatch_requires_a_read_observation() -> None:
    with pytest.raises(ValueError, match="unread media requires a pre-read"):
        MediaObservation(
            ObservationStatus.UNREAD_REJECTED,
            ObservationReason.CHECKSUM_MISMATCH,
            "fixture",
            None,
            None,
        )


def test_running_reconciliation_without_a_completion_is_not_live() -> None:
    now = datetime(2030, 1, 1, tzinfo=UTC)
    health = WorkerRuntimeHealth(
        schema_version=1,
        written_at=now,
        transport_connected=True,
        consumer_running=True,
        reconciliation_status=CriticalStageStatus.RUNNING,
    )
    assert not health.is_live(now=now)


def test_candidate_selection_refuses_an_empty_provider_result() -> None:
    with pytest.raises(ValueError, match="non-empty result set"):
        choose_geocode_candidate(normalize_geocode_query("ul. Syntetyczna"), ())


def test_address_agreement_refuses_a_provider_ambiguity_marker() -> None:
    result = GeocodeResult(
        GeocodeProvider.FIXTURE,
        "fixture",
        Decimal(21),
        Decimal("52.2"),
        "Synthetic",
        GeocodePrecision.STREET,
        Decimal(1),
        within_scope=True,
        attribution_text="fixture",
        diagnostic=(("candidate_ambiguity", "true"),),
    )
    assert (
        address_agreement_reason(normalize_geocode_query("ul. Syntetyczna"), result)
        is SelectionReason.AMBIGUOUS_CANDIDATES
    )


def test_contact_normalization_preserves_a_plus_without_inventing_digits() -> None:
    assert normalize_contact_value(RevealContactKind.PHONE, " + ") == "+"


def test_canonical_json_preserves_finite_fractional_values() -> None:
    assert freeze_json(1.25) == 1.25
    assert canonical_json_bytes({"value": 1.25}) == b'{"value":1.25}'


@pytest.mark.parametrize("failure", [TypeError("synthetic"), ValueError("synthetic")])
def test_serializer_failures_have_a_stable_domain_error(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def fail_dumps(*_args: object, **_kwargs: object) -> str:
        raise failure

    monkeypatch.setattr(json, "dumps", fail_dumps)
    with pytest.raises(
        JSONValueError, match="value cannot be serialized as canonical JSON"
    ) as raised:
        canonical_json_bytes({"value": 1})
    assert raised.value.__cause__ is failure
