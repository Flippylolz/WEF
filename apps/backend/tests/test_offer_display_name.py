"""Unit tests for public offer display names."""

from wef_backend.features.catalog.application.offer_display_name import (
    offer_display_name,
)
from wef_backend.features.catalog.domain import ContentType, MarketType


def test_display_name_combines_content_and_market_labels() -> None:
    """Classified offers combine friendly content and market labels."""
    assert (
        offer_display_name(ContentType.UNIT, MarketType.SECONDARY)
        == "Unit offer · Secondary market"
    )
    assert (
        offer_display_name(ContentType.DEVELOPMENT, MarketType.PRIMARY)
        == "Development post · Primary market"
    )


def test_display_name_omits_unclassified_market() -> None:
    """Unclassified market is omitted instead of surfacing the raw value."""
    assert offer_display_name(ContentType.UNIT, MarketType.UNKNOWN) == "Unit offer"
    assert offer_display_name(ContentType.DEVELOPMENT, MarketType.UNKNOWN) == "Development post"
