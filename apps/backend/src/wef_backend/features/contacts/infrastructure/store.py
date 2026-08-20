"""SQLAlchemy contact store adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import delete, select

from wef_backend.features.catalog.infrastructure.models import OfferRow
from wef_backend.features.contacts.application.reveal import CONTACT_SET_VERSION
from wef_backend.features.contacts.domain.model import (
    ContactKind,
    ContactPointRecord,
    RevealOutcome,
)
from wef_backend.features.contacts.infrastructure.models import (
    ContactPointRow,
    ContactRevealRow,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SQLAlchemyContactStore:
    """Persist encrypted contacts and minimized reveal audits."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the lazy session factory."""
        self._session_factory = session_factory

    async def replace_offer_contacts(
        self,
        *,
        offer_id: UUID,
        source_message_id: UUID | None,
        contacts: tuple[ContactPointRecord, ...],
    ) -> None:
        """Replace all contact points for one offer in one transaction."""
        del source_message_id  # carried on each ContactPointRecord
        async with self._session_factory.begin() as session:
            await session.execute(
                delete(ContactPointRow).where(ContactPointRow.offer_id == offer_id),
            )
            for item in contacts:
                session.add(
                    ContactPointRow(
                        id=item.id,
                        offer_id=item.offer_id,
                        source_message_id=item.source_message_id,
                        kind=item.kind.value,
                        value_ciphertext=item.value_ciphertext,
                        masked_value=item.masked_value,
                        fingerprint_hmac=item.fingerprint_hmac,
                        is_revealable=item.is_revealable,
                    ),
                )

    async def list_revealable_for_offer(
        self,
        offer_id: UUID,
    ) -> tuple[ContactPointRecord, ...]:
        """Return revealable contacts for one offer."""
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(ContactPointRow)
                    .where(
                        ContactPointRow.offer_id == offer_id,
                        ContactPointRow.is_revealable.is_(True),
                    )
                    .order_by(ContactPointRow.kind, ContactPointRow.created_at),
                )
            ).all()
        return tuple(_to_record(row) for row in rows)

    async def offer_is_publicly_visible(self, offer_id: UUID) -> bool:
        """Report whether the offer is anonymously visible."""
        async with self._session_factory() as session:
            visibility = await session.scalar(
                select(OfferRow.visibility).where(OfferRow.id == offer_id),
            )
        return visibility == "visible"

    async def record_reveal(
        self,
        *,
        user_id: UUID,
        offer_id: UUID,
        source_message_id: UUID | None,
        request_id: UUID,
        outcome: RevealOutcome,
    ) -> None:
        """Persist one minimized reveal audit row when the offer exists."""
        async with self._session_factory.begin() as session:
            exists = await session.scalar(select(OfferRow.id).where(OfferRow.id == offer_id))
            if exists is None:
                # Missing offers must fail closed as not-found without FK errors.
                return
            session.add(
                ContactRevealRow(
                    id=uuid4(),
                    user_id=user_id,
                    offer_id=offer_id,
                    source_message_id=source_message_id,
                    contact_set_version=CONTACT_SET_VERSION,
                    request_id=request_id,
                    outcome=outcome.value,
                ),
            )


def _to_record(row: ContactPointRow) -> ContactPointRecord:
    """Map one ORM row to the application record."""
    return ContactPointRecord(
        id=row.id,
        offer_id=row.offer_id,
        source_message_id=row.source_message_id,
        kind=ContactKind(row.kind),
        value_ciphertext=row.value_ciphertext,
        masked_value=row.masked_value,
        fingerprint_hmac=row.fingerprint_hmac,
        is_revealable=row.is_revealable,
    )
