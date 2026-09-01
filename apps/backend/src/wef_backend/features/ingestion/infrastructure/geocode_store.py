"""SQLAlchemy durable geocode cache, fencing, and selection adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.catalog.infrastructure.models import LocationRow
from wef_backend.features.ingestion.application.geocoding import (
    CachedGeocode,
    ClaimDisposition,
    GeocodeStorePort,
    MissClaim,
)
from wef_backend.features.ingestion.domain.geocoding import (
    REVIEW_POLICY_VERSION,
    GeocodeCacheKey,
    GeocodeErrorCode,
    GeocodePrecision,
    GeocodeProvider,
    GeocodeResult,
    NormalizedGeocodeQuery,
    ReviewDecision,
)
from wef_backend.features.ingestion.infrastructure.models import (
    GeocodeMissClaimRow,
    GeocodeResultRow,
    LocationGeocodeSelectionRow,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class StaleGeocodeClaimError(RuntimeError):
    """A fenced owner tried to complete after a newer takeover."""


class SQLAlchemyGeocodeStore(GeocodeStorePort):
    """PostgreSQL implementation with short transactions around provider I/O."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def get_cached(self, key: GeocodeCacheKey) -> CachedGeocode | None:
        """Read the unique cache row and neutral point coordinates."""
        async with self._session_factory() as session:
            record = (
                await session.execute(
                    select(
                        GeocodeResultRow,
                        func.ST_X(GeocodeResultRow.point),
                        func.ST_Y(GeocodeResultRow.point),
                    )
                    .where(GeocodeResultRow.query_hash == key.query_hash)
                    .limit(1),
                )
            ).one_or_none()
        return (
            _cached_from_record((record[0], record[1], record[2])) if record is not None else None
        )

    async def claim_miss(
        self,
        key: GeocodeCacheKey,
        *,
        owner_id: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> MissClaim:
        """Atomically insert or take over only an expired incomplete claim."""
        statement = insert(GeocodeMissClaimRow).values(
            query_hash=key.query_hash,
            owner_id=owner_id,
            fencing_token=1,
            claimed_at=now,
            lease_expires_at=lease_expires_at,
            completed_geocode_result_id=None,
        )
        takeover = statement.on_conflict_do_update(
            index_elements=[GeocodeMissClaimRow.query_hash],
            set_={
                "owner_id": owner_id,
                "fencing_token": GeocodeMissClaimRow.fencing_token + 1,
                "claimed_at": now,
                "lease_expires_at": lease_expires_at,
                "completed_geocode_result_id": None,
            },
            where=(
                (GeocodeMissClaimRow.lease_expires_at <= now)
                & (GeocodeMissClaimRow.completed_geocode_result_id.is_(None))
            ),
        ).returning(GeocodeMissClaimRow)
        async with self._session_factory() as session, session.begin():
            claimed = (await session.execute(takeover)).scalar_one_or_none()
            if claimed is None:
                claimed = await session.scalar(
                    select(GeocodeMissClaimRow)
                    .where(GeocodeMissClaimRow.query_hash == key.query_hash)
                    .with_for_update(),
                )
            if claimed is None:
                message = "geocode miss claim disappeared during acquisition"
                raise RuntimeError(message)
            disposition = (
                ClaimDisposition.OWNER if claimed.owner_id == owner_id else ClaimDisposition.WAIT
            )
            return MissClaim(
                disposition=disposition,
                owner_id=claimed.owner_id,
                fencing_token=claimed.fencing_token,
                lease_expires_at=claimed.lease_expires_at,
            )

    async def complete_miss(  # noqa: PLR0913
        self,
        key: GeocodeCacheKey,
        *,
        claim: MissClaim,
        query: NormalizedGeocodeQuery,
        result: GeocodeResult,
        attempted_at: datetime,
        expires_at: datetime | None,
    ) -> CachedGeocode:
        """Fence completion and reconcile ambiguous retries to one cache row."""
        point = None
        if result.longitude is not None and result.latitude is not None:
            point = WKTElement(f"POINT({result.longitude} {result.latitude})", srid=4326)
        result_id = uuid4()
        values = {
            "id": result_id,
            "query_hash": key.query_hash,
            "query_original": query.original[:240],
            "query_normalized": query.normalized[:240],
            "normalizer_version": key.normalizer_version,
            "scope_version": key.scope_version,
            "request_version": key.request_version,
            "provider": result.provider.value,
            "provider_result_id": result.provider_result_id,
            "point": point,
            "display_name": result.display_name,
            "precision": result.precision.value,
            "confidence": result.confidence,
            "within_scope": result.within_scope,
            "response_json": dict(result.diagnostic),
            "attribution_text": result.attribution_text,
            "attempted_at": attempted_at,
            "expires_at": expires_at,
            "error_code": result.error_code.value if result.error_code is not None else None,
        }
        async with self._session_factory() as session, session.begin():
            current = await session.scalar(
                select(GeocodeMissClaimRow)
                .where(GeocodeMissClaimRow.query_hash == key.query_hash)
                .with_for_update(),
            )
            if current is None or (
                current.owner_id != claim.owner_id or current.fencing_token != claim.fencing_token
            ):
                existing = await self._get_cached_in_session(session, key)
                if existing is not None:
                    return existing
                message = "geocode miss completion rejected by fencing token"
                raise StaleGeocodeClaimError(message)
            inserted_id = await session.scalar(
                insert(GeocodeResultRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=[GeocodeResultRow.query_hash])
                .returning(GeocodeResultRow.id),
            )
            durable_id = inserted_id
            if durable_id is None:
                durable_id = await session.scalar(
                    select(GeocodeResultRow.id).where(
                        GeocodeResultRow.query_hash == key.query_hash,
                    ),
                )
            if durable_id is None:
                message = "geocode cache reconciliation produced no durable result"
                raise RuntimeError(message)
            current.completed_geocode_result_id = durable_id
            durable = await self._get_cached_in_session(session, key)
            if durable is None:
                message = "geocode cache row missing after completion"
                raise RuntimeError(message)
            await session.delete(current)
            return durable

    async def abandon_miss(
        self,
        key: GeocodeCacheKey,
        *,
        claim: MissClaim,
        now: datetime,
    ) -> None:
        """Expire only the caller's still-incomplete fenced miss claim."""
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(GeocodeMissClaimRow)
                .where(
                    GeocodeMissClaimRow.query_hash == key.query_hash,
                    GeocodeMissClaimRow.owner_id == claim.owner_id,
                    GeocodeMissClaimRow.fencing_token == claim.fencing_token,
                    GeocodeMissClaimRow.completed_geocode_result_id.is_(None),
                )
                .values(lease_expires_at=now),
            )

    async def _get_cached_in_session(
        self,
        session: AsyncSession,
        key: GeocodeCacheKey,
    ) -> CachedGeocode | None:
        record = (
            await session.execute(
                select(
                    GeocodeResultRow,
                    func.ST_X(GeocodeResultRow.point),
                    func.ST_Y(GeocodeResultRow.point),
                ).where(GeocodeResultRow.query_hash == key.query_hash),
            )
        ).one_or_none()
        return (
            _cached_from_record((record[0], record[1], record[2])) if record is not None else None
        )

    async def select_for_location(
        self,
        *,
        location_id: UUID,
        cached: CachedGeocode,
        decision: ReviewDecision,
        actor_type: str,
        actor_id: str | None,
    ) -> None:
        """Append review lineage and update every current field atomically."""
        async with self._session_factory() as session, session.begin():
            location = await session.scalar(
                select(LocationRow).where(LocationRow.id == location_id).with_for_update(),
            )
            if location is None:
                message = "location does not exist"
                raise ValueError(message)
            latest = await session.scalar(
                select(func.max(LocationGeocodeSelectionRow.selection_version)).where(
                    LocationGeocodeSelectionRow.location_id == location_id,
                ),
            )
            selection_version = (latest or 0) + 1
            result = cached.result
            selected_id = cached.result_id if decision.select_result else None
            point = None
            if decision.select_result:
                if result.longitude is None or result.latitude is None:
                    message = "selected result must have coordinates"
                    raise ValueError(message)
                point = WKTElement(f"POINT({result.longitude} {result.latitude})", srid=4326)
            session.add(
                LocationGeocodeSelectionRow(
                    id=uuid4(),
                    location_id=location_id,
                    geocode_result_id=cached.result_id,
                    from_state=location.review_status,
                    to_state=decision.status.value,
                    reason_code=decision.reason.value,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    review_policy_version=REVIEW_POLICY_VERSION,
                    selection_version=selection_version,
                    decided_at=datetime.now(UTC),
                ),
            )
            await session.execute(
                update(LocationRow)
                .where(LocationRow.id == location_id)
                .values(
                    selected_geocode_result_id=selected_id,
                    point=point,
                    precision=result.precision.value,
                    confidence=result.confidence,
                    review_status=decision.status.value,
                    out_of_scope=decision.out_of_scope,
                    updated_at=datetime.now(UTC),
                ),
            )


def _cached_from_record(
    record: tuple[GeocodeResultRow, float | None, float | None],
) -> CachedGeocode:
    row, longitude, latitude = record
    diagnostic = row.response_json if isinstance(row.response_json, dict) else {}
    result = GeocodeResult(
        provider=GeocodeProvider(row.provider),
        provider_result_id=row.provider_result_id,
        longitude=Decimal(str(longitude)) if longitude is not None else None,
        latitude=Decimal(str(latitude)) if latitude is not None else None,
        display_name=row.display_name,
        precision=GeocodePrecision(row.precision),
        confidence=Decimal(row.confidence),
        within_scope=row.within_scope,
        attribution_text=row.attribution_text,
        error_code=GeocodeErrorCode(row.error_code) if row.error_code is not None else None,
        diagnostic=tuple(sorted((str(key), str(value)) for key, value in diagnostic.items())),
    )
    return CachedGeocode(result_id=row.id, result=result, expires_at=row.expires_at)
