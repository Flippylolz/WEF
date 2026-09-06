"""Shared daily quota reservation and provider-attempt completion transactions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from wef_backend.features.ingestion.application.complete_import import ProviderReservation
from wef_backend.features.ingestion.infrastructure.models import (
    ProviderAttemptRow,
    ProviderDailyBudgetRow,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from wef_backend.features.ingestion.domain.geocoding import GeocodeProvider


class SQLAlchemyProviderBudget:
    """Own atomic daily-budget rows and redacted attempt ledger writes."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Retain the same session factory without opening a transaction."""
        self._session_factory = session_factory

    async def reserve_provider_attempt(  # noqa: PLR0913
        self,
        *,
        run_id: UUID,
        provider: GeocodeProvider,
        account_identity: str,
        query_hash: str,
        daily_limit: int,
        minimum_interval: timedelta,
        now: datetime,
    ) -> ProviderReservation | None:
        """Reserve quota and allocate one globally spaced not-before slot."""
        budget_date = now.astimezone(UTC).date()
        async with self._session_factory() as session, session.begin():
            await session.execute(
                insert(ProviderDailyBudgetRow)
                .values(
                    provider=provider.value,
                    budget_date=budget_date,
                    account_identity=account_identity,
                    used_attempts=0,
                    last_not_before=None,
                    updated_at=now,
                )
                .on_conflict_do_nothing(),
            )
            budget = await session.scalar(
                select(ProviderDailyBudgetRow)
                .where(
                    ProviderDailyBudgetRow.provider == provider.value,
                    ProviderDailyBudgetRow.budget_date == budget_date,
                    ProviderDailyBudgetRow.account_identity == account_identity,
                )
                .with_for_update(),
            )
            if budget is None:
                message = "provider budget disappeared during reservation"
                raise RuntimeError(message)
            if budget.used_attempts >= daily_limit:
                return None
            not_before = now
            if budget.last_not_before is not None:
                not_before = max(now, budget.last_not_before + minimum_interval)
            budget.used_attempts += 1
            budget.last_not_before = not_before
            budget.updated_at = now
            attempt_id = uuid4()
            session.add(
                ProviderAttemptRow(
                    id=attempt_id,
                    complete_import_run_id=run_id,
                    provider=provider.value,
                    budget_date=budget_date,
                    account_identity=account_identity,
                    query_hash=query_hash,
                    not_before=not_before,
                    status="reserved",
                    error_code=None,
                    reserved_at=now,
                    completed_at=None,
                ),
            )
            return ProviderReservation(attempt_id=attempt_id, not_before=not_before)

    async def complete_provider_attempt(
        self,
        attempt_id: UUID,
        *,
        status: str,
        error_code: str | None,
        completed_at: datetime,
    ) -> None:
        """Complete only a still-reserved non-sensitive attempt ledger row."""
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(ProviderAttemptRow)
                .where(
                    ProviderAttemptRow.id == attempt_id,
                    ProviderAttemptRow.status == "reserved",
                )
                .values(status=status, error_code=error_code, completed_at=completed_at),
            )
