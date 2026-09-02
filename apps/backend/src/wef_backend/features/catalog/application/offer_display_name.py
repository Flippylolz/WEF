"""Human-readable public display names for offer summaries and details."""

from wef_backend.features.catalog.domain.model import ContentType, MarketType

_CONTENT_LABELS: dict[ContentType, str] = {
    ContentType.DEVELOPMENT: "Development post",
    ContentType.UNIT: "Unit offer",
}

_MARKET_LABELS: dict[MarketType, str] = {
    MarketType.PRIMARY: "Primary market",
    MarketType.SECONDARY: "Secondary market",
}


def offer_display_name(content_type: ContentType, market_type: MarketType) -> str:
    """Return a public offer title from parsed content and market types.

    Unclassified market is omitted instead of surfacing the raw enum value,
    so unclassified unit offers read "Unit offer" rather than
    "unit · unknown".
    """
    label = _CONTENT_LABELS[content_type]
    market = _MARKET_LABELS.get(market_type)
    return f"{label} · {market}" if market else label
