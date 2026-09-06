"""Negative warning probes and regression for retained integration sessions."""

from __future__ import annotations

import os
import warnings

import pytest
from sqlalchemy import text

from wef_backend.database import create_database_resources


@pytest.mark.parametrize("category", [RuntimeWarning, DeprecationWarning, ResourceWarning])
def test_unexpected_warning_is_an_error(category: type[Warning]) -> None:
    with pytest.raises(category, match="synthetic warning probe"):
        warnings.warn("synthetic warning probe", category, stacklevel=1)


@pytest.mark.integration
async def test_disposal_closes_retained_test_session_before_pool() -> None:
    url = os.getenv("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
    resources = create_database_resources(url)
    session = resources.session_factory()
    await session.execute(text("SELECT 1"))
    assert session.in_transaction()
    await resources.engine.dispose()
    assert not session.in_transaction()
