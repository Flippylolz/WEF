"""SQLAlchemy adapter for owner location administration and decisions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, func, select, update

from wef_backend.features.admin.application.admin_ops import (
    GeocodeCandidateSummary,
    LocationAdminSummary,
    LocationEditDetail,
    LocationStatusFilter,
    OfferContextSummary,
)
from wef_backend.features.catalog.infrastructure.models import LocationRow, OfferRow
from wef_backend.features.ingestion.domain.geocoding import (
    REVIEW_POLICY_VERSION,
    SelectionReason,
)
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy.sql.selectable import Select, Subquery

_PENDING_STATUSES = ("needs_review", "ungeocoded")
_OFFER_LIMIT = 5
_MANUAL_PRECISION = "building"
_MANUAL_CONFIDENCE = Decimal("1.00")


class SQLAlchemyLocationAdminStore:
    """List, load, and decide canonical locations for the owner console."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def list_locations(
        self,
        *,
        status: LocationStatusFilter,
        search: str | None,
        limit: int = 100,
    ) -> tuple[LocationAdminSummary, ...]:
        """Return locations newest-activity-first within the requested slice."""
        async with self._session_factory() as session:
            latest = _latest_selection_subquery()
            offer_count = (
                select(func.count())
                .select_from(OfferRow)
                .where(OfferRow.location_id == LocationRow.id)
                .correlate(LocationRow)
                .scalar_subquery()
            )
            stmt: Select[Any] = select(
                LocationRow,
                latest.c.reason_code.label("reason_code"),
                offer_count.label("offer_count"),
            ).join(
                latest,
                and_(latest.c.location_id == LocationRow.id, latest.c.rn == 1),
                isouter=True,
            )
            stmt = _apply_status_filter(stmt, status)
            if search is not None:
                pattern = _escaped_search(search)
                stmt = stmt.where(
                    LocationRow.display_address.ilike(pattern, escape="\\")
                    | LocationRow.display_name.ilike(pattern, escape="\\"),
                )
            stmt = stmt.order_by(LocationRow.updated_at.desc(), LocationRow.id.desc())
            stmt = stmt.limit(limit)
            rows = (await session.execute(stmt)).all()
        return tuple(
            LocationAdminSummary(
                id=row.LocationRow.id,
                display_name=row.LocationRow.display_name,
                display_address=row.LocationRow.display_address,
                district=row.LocationRow.district,
                city=row.LocationRow.city,
                review_status=row.LocationRow.review_status,
                precision=row.LocationRow.precision,
                confidence=row.LocationRow.confidence,
                has_point=row.LocationRow.point is not None,
                out_of_scope=row.LocationRow.out_of_scope,
                reason_code=row.reason_code,
                offer_count=int(row.offer_count),
                updated_at=row.LocationRow.updated_at,
            )
            for row in rows
        )

    async def get_edit_detail(self, location_id: UUID) -> LocationEditDetail | None:
        """Return one location's verification detail, or None when unknown."""
        async with self._session_factory() as session:
            row = await session.get(LocationRow, location_id)
            if row is None:
                return None
            reason_code = await _latest_reason(session, location_id)
            latest = await _latest_selection_row(session, location_id)
            candidate = await _latest_candidate(session, latest)
            point_coordinates = await _point_coordinates(
                session,
                select(func.ST_X(LocationRow.point), func.ST_Y(LocationRow.point)).where(
                    LocationRow.id == location_id,
                ),
            )
            offer_rows = (
                await session.scalars(
                    select(OfferRow)
                    .where(OfferRow.location_id == location_id)
                    .order_by(OfferRow.published_at.desc(), OfferRow.id.desc())
                    .limit(_OFFER_LIMIT),
                )
            ).all()
            offer_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(OfferRow)
                    .where(OfferRow.location_id == location_id),
                )
                or 0,
            )
        summary = LocationAdminSummary(
            id=row.id,
            display_name=row.display_name,
            display_address=row.display_address,
            district=row.district,
            city=row.city,
            review_status=row.review_status,
            precision=row.precision,
            confidence=row.confidence,
            has_point=row.point is not None,
            out_of_scope=row.out_of_scope,
            reason_code=reason_code,
            offer_count=offer_count,
            updated_at=row.updated_at,
        )
        return LocationEditDetail(
            summary=summary,
            normalized_address=row.normalized_address,
            longitude=None if point_coordinates is None else point_coordinates[0],
            latitude=None if point_coordinates is None else point_coordinates[1],
            candidate=candidate,
            offers=tuple(_offer_summary(offer) for offer in offer_rows),
        )

    async def apply_accept_candidate(
        self,
        *,
        location_id: UUID,
        actor_id: str,
        decided_at: datetime,
    ) -> bool:
        """Promote the latest in-scope candidate point; False when not applicable."""
        async with self._session_factory.begin() as session:
            row = await session.get(LocationRow, location_id)
            if row is None:
                return False
            latest = await _latest_selection_row(session, location_id)
            if latest is None or latest.geocode_result_id is None:
                return False
            result = await _usable_candidate_result(session, latest.geocode_result_id)
            if result is None:
                return False
            coordinates = await _point_coordinates(
                session,
                select(
                    func.ST_X(GeocodeResultRow.point),
                    func.ST_Y(GeocodeResultRow.point),
                ).where(GeocodeResultRow.id == latest.geocode_result_id),
            )
            if coordinates is None:
                return False
            longitude, latitude = coordinates
            await _append_selection(
                session,
                _LineageDecision(
                    location_id=location_id,
                    geocode_result_id=latest.geocode_result_id,
                    from_state=row.review_status,
                    to_state="accepted",
                    reason_code=SelectionReason.MANUAL_ACCEPT.value,
                    selection_version=latest.selection_version + 1,
                ),
                actor_id=actor_id,
                decided_at=decided_at,
            )
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == location_id)
                .values(
                    point=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
                    precision=result.precision,
                    confidence=result.confidence,
                    review_status="accepted",
                    selected_geocode_result_id=latest.geocode_result_id,
                    out_of_scope=False,
                    updated_at=decided_at,
                ),
            )
            return True

    async def apply_reject(
        self,
        *,
        location_id: UUID,
        actor_id: str,
        decided_at: datetime,
    ) -> bool:
        """Mark the location rejected; False when not applicable."""
        async with self._session_factory.begin() as session:
            row = await session.get(LocationRow, location_id)
            if row is None or row.review_status == "rejected":
                return False
            latest = await _latest_selection_row(session, location_id)
            await _append_selection(
                session,
                _LineageDecision(
                    location_id=location_id,
                    geocode_result_id=None if latest is None else latest.geocode_result_id,
                    from_state=row.review_status,
                    to_state="rejected",
                    reason_code=SelectionReason.MANUAL_REJECT.value,
                    selection_version=1 if latest is None else latest.selection_version + 1,
                ),
                actor_id=actor_id,
                decided_at=decided_at,
            )
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == location_id)
                .values(review_status="rejected", updated_at=decided_at),
            )
            return True

    async def apply_unresolve(
        self,
        *,
        location_id: UUID,
        actor_id: str,
        decided_at: datetime,
    ) -> bool:
        """Return a decided location to needs_review; False when not applicable."""
        async with self._session_factory.begin() as session:
            row = await session.get(LocationRow, location_id)
            if row is None or row.review_status not in ("accepted", "rejected"):
                return False
            latest = await _latest_selection_row(session, location_id)
            await _append_selection(
                session,
                _LineageDecision(
                    location_id=location_id,
                    geocode_result_id=None if latest is None else latest.geocode_result_id,
                    from_state=row.review_status,
                    to_state="needs_review",
                    reason_code=SelectionReason.MANUAL_UNRESOLVE.value,
                    selection_version=1 if latest is None else latest.selection_version + 1,
                ),
                actor_id=actor_id,
                decided_at=decided_at,
            )
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == location_id)
                .values(review_status="needs_review", updated_at=decided_at),
            )
            return True

    async def apply_set_point(
        self,
        *,
        location_id: UUID,
        longitude: Decimal,
        latitude: Decimal,
        actor_id: str,
        decided_at: datetime,
    ) -> bool:
        """Place an operator-verified point; False when the location is unknown."""
        async with self._session_factory.begin() as session:
            row = await session.get(LocationRow, location_id)
            if row is None:
                return False
            latest = await _latest_selection_row(session, location_id)
            await _append_selection(
                session,
                _LineageDecision(
                    location_id=location_id,
                    geocode_result_id=None,
                    from_state=row.review_status,
                    to_state="accepted",
                    reason_code=SelectionReason.MANUAL_ACCEPT.value,
                    selection_version=1 if latest is None else latest.selection_version + 1,
                ),
                actor_id=actor_id,
                decided_at=decided_at,
            )
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == location_id)
                .values(
                    point=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
                    precision=_MANUAL_PRECISION,
                    confidence=_MANUAL_CONFIDENCE,
                    review_status="accepted",
                    selected_geocode_result_id=None,
                    out_of_scope=False,
                    updated_at=decided_at,
                ),
            )
            return True


class _UsableCandidate:
    """Provider metadata of a geocode result usable as an in-scope candidate."""

    __slots__ = ("confidence", "precision")

    def __init__(self, *, precision: str, confidence: Decimal) -> None:
        """Initialize the collaborator."""
        self.precision = precision
        self.confidence = confidence


def _latest_selection_subquery() -> Subquery:
    """Return the per-location latest selection row-number subquery."""
    return (
        select(
            LocationGeocodeSelectionRow.location_id.label("location_id"),
            LocationGeocodeSelectionRow.reason_code.label("reason_code"),
            func.row_number()
            .over(
                partition_by=LocationGeocodeSelectionRow.location_id,
                order_by=LocationGeocodeSelectionRow.selection_version.desc(),
            )
            .label("rn"),
        )
    ).subquery()


def _apply_status_filter(
    stmt: Select[Any],
    status: LocationStatusFilter,
) -> Select[Any]:
    """Constrain the listing to one bounded review-status slice."""
    if status is LocationStatusFilter.PENDING:
        return stmt.where(LocationRow.review_status.in_(_PENDING_STATUSES))
    if status is LocationStatusFilter.ALL:
        return stmt
    return stmt.where(LocationRow.review_status == status.value)


def _escaped_search(term: str) -> str:
    """Escape SQL LIKE wildcards in an owner search term."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _offer_summary(offer: OfferRow) -> OfferContextSummary:
    """Project one offer row into owner-facing verification evidence."""
    return OfferContextSummary(
        id=offer.id,
        content_type=offer.content_type,
        market_type=offer.market_type,
        visibility=offer.visibility,
        published_at=offer.published_at,
        currency=offer.currency,
        price_min_minor=offer.price_min_minor,
        price_max_minor=offer.price_max_minor,
        area_min_sqm=offer.area_min_sqm,
        area_max_sqm=offer.area_max_sqm,
        rooms_min=offer.rooms_min,
        rooms_max=offer.rooms_max,
        source_text_excerpt=offer.source_text_excerpt,
    )


async def _latest_reason(session: AsyncSession, location_id: UUID) -> str | None:
    """Return the newest selection reason for one location."""
    row = (
        await session.execute(
            select(LocationGeocodeSelectionRow.reason_code)
            .where(LocationGeocodeSelectionRow.location_id == location_id)
            .order_by(LocationGeocodeSelectionRow.selection_version.desc())
            .limit(1),
        )
    ).first()
    return None if row is None else str(row.reason_code)


async def _latest_selection_row(
    session: AsyncSession,
    location_id: UUID,
) -> LocationGeocodeSelectionRow | None:
    """Return the newest lineage row for one location."""
    return (
        await session.scalars(
            select(LocationGeocodeSelectionRow)
            .where(LocationGeocodeSelectionRow.location_id == location_id)
            .order_by(LocationGeocodeSelectionRow.selection_version.desc())
            .limit(1),
        )
    ).first()


async def _latest_candidate(
    session: AsyncSession,
    latest: LocationGeocodeSelectionRow | None,
) -> GeocodeCandidateSummary | None:
    """Return the in-scope provider point behind the latest selection."""
    if latest is None or latest.geocode_result_id is None:
        return None
    row = (
        await session.execute(
            select(
                GeocodeResultRow.provider,
                GeocodeResultRow.display_name,
                GeocodeResultRow.precision,
                GeocodeResultRow.confidence,
                GeocodeResultRow.point,
                GeocodeResultRow.within_scope,
                GeocodeResultRow.error_code,
            ).where(GeocodeResultRow.id == latest.geocode_result_id),
        )
    ).one_or_none()
    if row is None or row.point is None or row.within_scope is not True:
        return None
    if row.error_code is not None:
        return None
    coordinates = await _point_coordinates(
        session,
        select(
            func.ST_X(GeocodeResultRow.point),
            func.ST_Y(GeocodeResultRow.point),
        ).where(GeocodeResultRow.id == latest.geocode_result_id),
    )
    if coordinates is None:
        return None
    return GeocodeCandidateSummary(
        longitude=coordinates[0],
        latitude=coordinates[1],
        precision=row.precision,
        confidence=row.confidence,
        provider=row.provider,
        display_name=row.display_name,
    )


async def _usable_candidate_result(
    session: AsyncSession,
    geocode_result_id: UUID,
) -> _UsableCandidate | None:
    """Return precision/confidence when the result carries an in-scope point."""
    row = (
        await session.execute(
            select(
                GeocodeResultRow.precision,
                GeocodeResultRow.confidence,
                GeocodeResultRow.point,
                GeocodeResultRow.within_scope,
                GeocodeResultRow.error_code,
            ).where(GeocodeResultRow.id == geocode_result_id),
        )
    ).one_or_none()
    if row is None or row.point is None or row.within_scope is not True:
        return None
    if row.error_code is not None:
        return None
    return _UsableCandidate(precision=row.precision, confidence=row.confidence)


async def _point_coordinates(
    session: AsyncSession,
    stmt: Select[Any],
) -> tuple[Decimal, Decimal] | None:
    """Return exact stored coordinates from an ST_X/ST_Y projection."""
    row = (await session.execute(stmt)).one_or_none()
    if row is None or row[0] is None or row[1] is None:
        return None
    longitude, latitude = row[0], row[1]
    return (
        longitude if isinstance(longitude, Decimal) else Decimal(str(longitude)),
        latitude if isinstance(latitude, Decimal) else Decimal(str(latitude)),
    )


@dataclass(frozen=True, slots=True)
class _LineageDecision:
    """One operator decision to append to the lineage."""

    location_id: UUID
    geocode_result_id: UUID | None
    from_state: str
    to_state: str
    reason_code: str
    selection_version: int


async def _append_selection(
    session: AsyncSession,
    decision: _LineageDecision,
    *,
    actor_id: str,
    decided_at: datetime,
) -> None:
    """Append one operator decision to the lineage."""
    session.add(
        LocationGeocodeSelectionRow(
            id=uuid4(),
            location_id=decision.location_id,
            geocode_result_id=decision.geocode_result_id,
            from_state=decision.from_state,
            to_state=decision.to_state,
            reason_code=decision.reason_code,
            actor_type="operator",
            actor_id=actor_id,
            review_policy_version=REVIEW_POLICY_VERSION,
            selection_version=decision.selection_version,
            decided_at=decided_at,
        ),
    )
