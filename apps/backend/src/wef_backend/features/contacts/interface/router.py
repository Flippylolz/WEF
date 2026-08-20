"""HTTP adapter for authenticated contact reveal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict

from wef_backend.errors import AuthProblemError, ResourceNotFoundError
from wef_backend.features.contacts.domain.model import RevealOutcome
from wef_backend.features.identity.interface.router import (
    _require_account,
    enforce_trusted_origin,
)

if TYPE_CHECKING:
    from wef_backend.features.contacts.application.reveal import ContactService

router = APIRouter(
    prefix="/api/v1/offers",
    tags=["contacts"],
    dependencies=[Depends(enforce_trusted_origin)],
)


class RevealedContactResponse(BaseModel):
    """One plaintext contact returned only after authorization."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["phone", "telegram"]
    value: str
    masked_value: str


class RevealContactsResponse(BaseModel):
    """Authorized reveal body without source text."""

    model_config = ConfigDict(extra="forbid")

    contacts: list[RevealedContactResponse]


def _contacts(request: Request) -> ContactService:
    """Return the composed contact service or refuse safely."""
    service: ContactService | None = getattr(request.app.state, "contacts", None)
    if service is None:
        raise AuthProblemError(
            status_code=503,
            code="contacts_unavailable",
            detail="Contact reveal is currently unavailable.",
        )
    return service


@router.post(
    "/{offer_id}/contacts/reveal",
    operation_id="revealOfferContacts",
    summary="Reveal contacts for one visible offer",
    responses={
        401: {"description": "Authentication is required."},
        403: {"description": "The account cannot reveal contacts."},
        404: {"description": "The offer is absent or not publicly visible."},
        415: {"description": "Mutations require a JSON content type."},
        429: {"description": "Too many reveal attempts from this account."},
        503: {"description": "Contact reveal is temporarily unavailable."},
    },
)
async def reveal_offer_contacts(
    offer_id: UUID,
    request: Request,
    response: Response,
) -> RevealContactsResponse:
    """Decrypt contacts after session, visibility, and rate-limit checks."""
    account = await _require_account(request)
    service = _contacts(request)
    request_id = request.state.request_id
    result = await service.reveal(
        user_id=account.id,
        offer_id=offer_id,
        request_id=request_id,
        must_change_password=account.must_change_password,
    )
    response.headers["Cache-Control"] = "no-store, private"
    if result.outcome is RevealOutcome.RATE_LIMITED:
        raise AuthProblemError(
            status_code=429,
            code="reveal_rate_limited",
            detail="Too many contact reveal attempts. Try again later.",
        )
    if result.outcome is RevealOutcome.UNAVAILABLE:
        raise AuthProblemError(
            status_code=503,
            code="contacts_unavailable",
            detail="Contact reveal is currently unavailable.",
        )
    if result.outcome is RevealOutcome.FORBIDDEN:
        if result.not_found:
            raise ResourceNotFoundError
        raise AuthProblemError(
            status_code=403,
            code="reveal_forbidden",
            detail="Contact reveal is not allowed for this account.",
        )
    return RevealContactsResponse(
        contacts=[
            RevealedContactResponse(
                kind="phone" if item.kind.value == "phone" else "telegram",
                value=item.value,
                masked_value=item.masked_value,
            )
            for item in result.contacts
        ],
    )
