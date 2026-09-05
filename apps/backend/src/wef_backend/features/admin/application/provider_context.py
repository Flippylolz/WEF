"""Request-local attribution for the shared provider reservation boundary."""

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar
from uuid import UUID

P = ParamSpec("P")
R = TypeVar("R")
provider_actor: ContextVar[tuple[UUID, UUID] | None] = ContextVar("provider_actor", default=None)


def provider_operation[**P, R](function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Attribute nested provider calls to the authorized owner and operation."""

    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        owner, request = kwargs.get("owner_id"), kwargs.get("batch_id", kwargs.get("request_id"))
        if not isinstance(owner, UUID) or not isinstance(request, UUID):
            msg = "provider operation requires owner and request identities"
            raise TypeError(msg)
        token = provider_actor.set((owner, request))
        try:
            return await function(*args, **kwargs)
        finally:
            provider_actor.reset(token)

    return wrapped
