"""Private operator entrypoint routes controls without provider calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from wef_backend import location_validation_command as command
from wef_backend.features.ingestion.application.location_revalidation import VALIDATION_TARGET


@pytest.mark.parametrize(
    "action", ["status", "off", "observe", "apply", "verify-canary", "rollback"]
)
async def test_operator_control_routes_and_disposes(
    action: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = SimpleNamespace(
        control=AsyncMock(),
        rollback=AsyncMock(),
        verify_canary=AsyncMock(),
        status=AsyncMock(return_value={"states": []}),
    )
    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(command, "load_settings", lambda: SimpleNamespace(database_url="synthetic"))
    monkeypatch.setattr(
        command,
        "create_database_resources",
        lambda _url: SimpleNamespace(engine=engine, session_factory=object()),
    )
    monkeypatch.setattr(command, "SQLAlchemyLocationValidationStore", lambda _factory: store)
    canaries = (uuid4(),)
    assert await command.run(action, canary_ids=canaries, discovery_ready=True) == {"states": []}
    if action == "rollback":
        store.rollback.assert_awaited_once_with(target=VALIDATION_TARGET)
    elif action == "verify-canary":
        store.verify_canary.assert_awaited_once_with(target=VALIDATION_TARGET)
    elif action != "status":
        store.control.assert_awaited_once_with(
            target=VALIDATION_TARGET, mode=action, canary_ids=canaries, discovery_ready=True
        )
    else:
        store.control.assert_not_called()
    engine.dispose.assert_awaited_once()
