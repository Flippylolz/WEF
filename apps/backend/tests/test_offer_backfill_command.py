"""The operator must not connect or mutate without valid explicit bounds."""

import pytest

from wef_backend.offer_backfill_command import run


@pytest.mark.parametrize(
    ("after", "through", "limit"), [(-1, 10, 1), (10, 10, 1), (20, 10, 1), (0, 10, 0), (0, 10, 501)]
)
async def test_invalid_bounds_reject_before_settings_or_database(
    after: int, through: int, limit: int
) -> None:
    with pytest.raises(ValueError, match="after-id"):
        await run(channel="synthetic", after_id=after, through_id=through, limit=limit, apply=True)
