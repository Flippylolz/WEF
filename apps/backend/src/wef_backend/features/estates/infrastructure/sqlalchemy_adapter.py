"""SQLAlchemy/PostGIS implementation of the estate query port."""

from collections.abc import Sequence

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import CheckConstraint, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from wef_backend.features.estates.application import EstateQueryPort, EstateRecord
from wef_backend.features.estates.domain import Availability, GeoPoint


class Base(DeclarativeBase):
    """Declarative base for the disposable proof mapping."""


class EstateRow(Base):
    """Synthetic PostGIS-backed estate row."""

    __tablename__ = "e0_proof_estates"
    __table_args__ = (
        CheckConstraint(
            "availability IN ('available', 'reserved')",
            name="ck_e0_proof_estates_availability",
        ),
    )

    estate_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    availability: Mapped[str] = mapped_column(String(16))
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
    )


class SQLAlchemyEstateQueryAdapter(EstateQueryPort):
    """Map SQLAlchemy/PostGIS rows into application-owned records."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store a session factory without opening a database connection."""
        self._session_factory = session_factory

    async def list_estate_records(self) -> Sequence[EstateRecord]:
        """Read point ordinates in SQL and return deterministic records."""
        statement = (
            select(
                EstateRow.estate_id,
                EstateRow.title,
                EstateRow.availability,
                func.ST_X(EstateRow.location).label("longitude"),
                func.ST_Y(EstateRow.location).label("latitude"),
            )
            .select_from(EstateRow)
            .order_by(EstateRow.estate_id)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()

        return tuple(
            EstateRecord(
                estate_id=estate_id,
                title=title,
                availability=Availability(availability),
                location=GeoPoint(longitude=float(longitude), latitude=float(latitude)),
            )
            for estate_id, title, availability, longitude, latitude in rows
        )
