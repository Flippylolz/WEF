"""PostgreSQL allocation shared by all AI entry points and worker processes."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text

from wef_backend.features.admin.application.ai_review import (
    ProviderOutcome,
    ProviderRequestError,
    StructuredCompletion,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_LOCK = 25032026
_MAX_SAFE_ATTEMPTS = 2


def next_day(now: datetime) -> datetime:
    """Return the next UTC budget boundary."""
    utc = now.astimezone(UTC)
    return utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)


class SQLAlchemyProviderBudget:
    """Serialize short reservation transactions; never hold locks over HTTP."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Bind the application database."""
        self._sessions = sessions

    async def reserve(
        self, owner: UUID, key: str, now: datetime, limit: int, *, operation_id: UUID | None = None
    ) -> UUID:
        """Count legacy usage once on first use, and reserve before sending."""
        failure = None
        attempt = uuid4()
        async with self._sessions.begin() as session:
            await session.execute(text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": _LOCK})
            account = (
                (
                    await session.execute(
                        text("SELECT * FROM ai_provider_accounts WHERE owner_id=:owner FOR UPDATE"),
                        {"owner": owner},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if account is None:
                used = await session.scalar(
                    text("""
                    SELECT count(*) FROM (
                        SELECT created_at FROM place_ai_review_runs WHERE owner_user_id=:owner
                        UNION ALL SELECT created_at FROM ingestion_ai_parse_runs
                            WHERE owner_user_id=:owner
                        UNION ALL SELECT i.provider_called_at FROM offer_ai_enrichment_items i
                            JOIN offer_ai_enrichment_batches b ON b.id=i.batch_id
                            WHERE b.owner_user_id=:owner AND i.provider_called_at IS NOT NULL
                    ) calls WHERE created_at >= :start
                """),
                    {"owner": owner, "start": next_day(now) - timedelta(days=1)},
                )
                await session.execute(
                    text("""
                    INSERT INTO ai_provider_accounts(owner_id,budget_day,used,next_eligible_at)
                    VALUES (:owner,:day,:used,:now)
                """),
                    {"owner": owner, "day": now.date(), "used": used or 0, "now": now},
                )
                used_count, eligible = int(used or 0), now
            else:
                used_count = account["used"] if account["budget_day"] == now.date() else 0
                eligible = account["next_eligible_at"]
                if account["attempt_id"] is not None:
                    if account["lease_until"] > now:
                        eligible = max(eligible, account["lease_until"])
                    else:
                        await session.execute(
                            text("""
                            UPDATE ai_provider_attempts SET state='uncertain',
                                reason='uncertain_submission',finished_at=:now
                            WHERE id=:id AND state='submitting'
                        """),
                            {"id": account["attempt_id"], "now": now},
                        )
            previous = (
                (
                    await session.execute(
                        text("""
                SELECT * FROM ai_provider_attempts WHERE owner_id=:owner AND work_key=:key
                ORDER BY ordinal DESC LIMIT 1
            """),
                        {"owner": owner, "key": key},
                    )
                )
                .mappings()
                .one_or_none()
            )
            ordinal = 1 if previous is None else previous["ordinal"] + 1
            if previous is not None and previous["state"] not in {"retry", "rate_limited"}:
                failure = ProviderRequestError(ProviderOutcome.DISABLED, uncertain=True)
            elif previous is not None and previous["next_eligible_at"] > now:
                failure = ProviderRequestError(
                    ProviderOutcome.RATE_LIMITED, retry_at=previous["next_eligible_at"]
                )
            elif used_count >= min(20, limit):
                eligible = max(eligible, next_day(now))
                await session.execute(
                    text(
                        "UPDATE ai_provider_accounts SET next_eligible_at=:next "
                        "WHERE owner_id=:owner"
                    ),
                    {"next": eligible, "owner": owner},
                )
                failure = ProviderRequestError(ProviderOutcome.RATE_LIMITED, retry_at=eligible)
            elif eligible > now:
                failure = ProviderRequestError(ProviderOutcome.RATE_LIMITED, retry_at=eligible)
            else:
                await session.execute(
                    text("""
                    INSERT INTO ai_provider_attempts
                        (id,owner_id,operation_id,work_key,ordinal,state,created_at)
                    VALUES (:id,:owner,:operation,:key,:ordinal,'submitting',:now)
                """),
                    {
                        "id": attempt,
                        "owner": owner,
                        "operation": operation_id,
                        "key": key,
                        "ordinal": ordinal,
                        "now": now,
                    },
                )
                await session.execute(
                    text("""
                    UPDATE ai_provider_accounts SET budget_day=:day,used=:used,
                        next_eligible_at=:eligible,attempt_id=:id,lease_until=:lease
                    WHERE owner_id=:owner
                """),
                    {
                        "day": now.date(),
                        "used": used_count + 1,
                        "eligible": now + timedelta(seconds=60),
                        "id": attempt,
                        "lease": now + timedelta(seconds=120),
                        "owner": owner,
                    },
                )
        if failure is not None:
            raise failure
        return attempt

    async def finish(
        self,
        attempt: UUID,
        now: datetime,
        error: ProviderRequestError | None,
        completion: StructuredCompletion | None,
    ) -> None:
        """Release lease and preserve quota even when a request failed."""
        async with self._sessions.begin() as session:
            await session.execute(text("SELECT pg_advisory_xact_lock(:lock)"), {"lock": _LOCK})
            row = (
                (
                    await session.execute(
                        text("SELECT * FROM ai_provider_attempts WHERE id=:id FOR UPDATE"),
                        {"id": attempt},
                    )
                )
                .mappings()
                .one()
            )
            if row["state"] != "submitting":
                return
            state, reason, eligible = "succeeded", None, now
            if error is not None:
                reason = error.outcome.value
                state = "terminal"
                if error.outcome is ProviderOutcome.RATE_LIMITED:
                    state, eligible = "rate_limited", max(next_day(now), error.retry_at or now)
                elif error.safe_retry and row["ordinal"] < _MAX_SAFE_ATTEMPTS:
                    state, eligible = "retry", now + timedelta(seconds=60)
                elif not error.safe_retry and (
                    error.uncertain
                    or error.outcome
                    in {
                        ProviderOutcome.TIMEOUT,
                        ProviderOutcome.NETWORK,
                    }
                ):
                    state, reason = "uncertain", "uncertain_submission"
                if state in {"retry", "rate_limited"}:
                    error.retry_at = eligible
            await session.execute(
                text("""
                UPDATE ai_provider_attempts SET state=:state,reason=:reason,finished_at=:now,
                    next_eligible_at=:eligible,token_input=:ti,token_output=:to,
                    provider_request_id=:request WHERE id=:id
            """),
                {
                    "state": state,
                    "reason": reason,
                    "now": now,
                    "eligible": eligible,
                    "ti": completion.token_input if completion else None,
                    "to": completion.token_output if completion else None,
                    "request": (
                        completion.request_id
                        if completion
                        and completion.request_id
                        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", completion.request_id)
                        else None
                    ),
                    "id": attempt,
                },
            )
            await session.execute(
                text("""
                UPDATE ai_provider_accounts SET attempt_id=NULL,lease_until=NULL,
                    next_eligible_at=GREATEST(next_eligible_at,:eligible)
                WHERE owner_id=:owner AND attempt_id=:id
            """),
                {"eligible": eligible, "owner": row["owner_id"], "id": attempt},
            )
